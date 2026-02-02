from typing import List, Dict, Any
from difflib import get_close_matches
from services.tuss_service import tuss_service
from services.missing_terms_logger import missing_terms_logger
from services.pdca_service import pdca_service
from services.resolute_orchestrator import resolute_orchestrator
from services.fuzzy_matcher import fuzzy_matcher
from services.learning_service import learning_service

print("🛡️ Validation Logic: Module Loaded Successfully")

class ValidationService:
    @staticmethod
    def calculate_similarity(term1: str, term2: str) -> float:
        # Usa o fuzzy_matcher se possível, senão difflib
        try:
            match = fuzzy_matcher.find_best_match(term1, min_score=0)
            if match:
                return match["score"] / 100.0
        except:
            pass
        s = get_close_matches(term1, [term2], n=1, cutoff=0.0)
        return 1.0 if s else 0.0

    @staticmethod
    def normalize_text(text: str) -> str:
        """Remove acentos, pontuação e normaliza espaços para comparação robusta"""
        import unicodedata
        import re
        if not text: return ""
        # Remove acentos
        nfkd_form = unicodedata.normalize('NFKD', str(text))
        text = "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()
        # Remove pontuação e caracteres especiais, mantendo apenas letras, números e espaços
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Remove sufixos comuns que poluem o match
        text = text.replace(' exames laboratoriais', '').replace(' exames', '')
        # Normaliza espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def validate_batch(terms: List[str], unit: str, bq_client: Any) -> Dict[str, Any]:
        results = {
            "items": [],
            "stats": {
                "confirmed": 0,
                "pending": 0,
                "not_found": 0,
                "total": 0,
                "catalog_count": 0,
                "bq_error": None,
                "backend_version": "V101.0-RESOLUTE-ULTRA"
            }
        }
        
        # 1. Carregar catálogo completo (Cache Local) - O(1) Query
        print(f"Carregando catálogo para unidade: {unit}...")
        try:
            all_exams = bq_client.get_all_exams(unit)
            results["stats"]["catalog_count"] = len(all_exams)
        except Exception as e:
            print(f"❌ Critical BQ Error: {e}")
            all_exams = []
            results["stats"]["bq_error"] = str(e)
        
        # Mapa para busca exata rápida: "termo_normalizado" -> Objeto Exame
        exam_map = {}
        # Dynamic versioning to help debug
        auth_status = getattr(bq_client, 'auth_info', 'INIT')
        results["stats"]["backend_version"] = f"V102.2-Expert (Catalog: {len(all_exams)}, Auth: {auth_status})"
        
        for exam in all_exams:
            # Normaliza chave do mapa (sem acentos)
            name_key = ValidationService.normalize_text(exam["search_name"])
            if name_key not in exam_map:
                exam_map[name_key] = []
            exam_map[name_key].append(exam)
        
        exam_keys = list(exam_map.keys()) # Para fuzzy search
        print(f"📊 Catálogo Carregado: {len(all_exams)} itens, {len(exam_keys)} chaves únicas.")
        if exam_keys:
            print(f"🔬 Amostra de Chaves: {exam_keys[:10]}")
        
        # Atualizar FuzzyMatcher
        fuzzy_matcher.update_known_exams(exam_keys)
        
        # Dicionário de Sinônimos Médicos (Normalizados)
        SYNONYMS = {
            "eas": ["urina rotina eas", "urina tipo i", "urina tipo 1", "sumario de urina", "elementos anormais do sedimento"],
            "elementos anormais do sedimento": ["urina tipo i", "urina rotina eas"],
            "urina tipo i": ["urina tipo i", "eas", "urina rotina eas"],
            "hemograma": ["hemograma completo", "hemograma com contagem de plaquetas"],
            "hemograma completo": ["hemograma"],
            "epf": ["parasitologico de fezes", "protoparasitologico"],
            "parasitologico": ["parasitologico de fezes"],
            "glicose": ["glicemia", "glicemia de jejum", "dosagem de glicose"],
            "glicemia": ["glicemia", "glicemia de jejum"],
            "glicada": ["hemoglobina glicada", "hemoglobina glicada a1c", "hba1c"],
            "hemoglobina glicada": ["hemoglobina glicada", "hemoglobina glicada a1c", "hba1c"],
            "colesterol": ["colesterol total", "colesterol total e fracoes"],
            "perfil lipidico": ["lipidogramas"],
            "lipidogramas": ["lipidogramas"],
            "coprologico funcional": ["coprologico funcional"],
            "coprologico": ["coprologico funcional"],
            "h.pylori": ["antigeno helicobacter pylori", "pesquisa de helicobacter pylori", "helicobacter pylori fezes"],
            "h pylori": ["antigeno helicobacter pylori"],
            "pylori": ["antigeno helicobacter pylori"],
            "helicobacter pylori": ["antigeno helicobacter pylori"],
            "tsh": ["hormonio tireoestimulante", "tsh ultra sensivel"],
            "fsh": ["hormonio foliculo estimulante", "dosagem de hormonio foliculo estimulante", "fsh"],
            "hormonio foliculo estimulante": ["hormonio foliculo estimulante", "fsh"],
            "t4 livre": ["tiroxina livre", "t4"],
            "ureia": ["dosagem de ureia", "ureia"],
            "creatinina": ["dosagem de creatinina", "creatinina"],
            "acido urico": ["dosagem de acido urico", "acido urico"],
            "beta hcg": ["beta hcg qualitativo", "beta hcg quantitativo"],
            "grupo sanguineo": ["tipagem sanguinea", "grupo sanguineo fator rh"],
            "tgo": ["dosagem de tgo", "tgo transaminase oxalacetica", "transaminase glutamico oxalacetica", "aspartato aminotransferase", "ast"],
            "ast": ["dosagem de tgo", "aspartato aminotransferase", "tgo"],
            "tgp": ["dosagem de tgp", "tgp transaminase piruvica", "transaminase glutamico piruvica", "alanina aminotransferase", "alt"],
            "alt": ["dosagem de tgp", "alanina aminotransferase", "tgp"],
            "vitamina d": ["25 hidroxivitamina d", "dosagem de vitamina d", "vitamina d 25 oh", "vit d", "25 oh vitamina d"],
            "25 hidroxivitamina d": ["vitamina d", "vitamina d 25 oh", "25 oh vitamina d"],
            "vitamina d 25-oh": ["25 hidroxivitamina d", "vitamina d"],
            "vit d": ["25 hidroxivitamina d", "vitamina d"],
            "ferritina": ["ferritina serica", "dosagem de ferritina"],
            "vitamina b12": ["vitamina b12 serica", "dosagem de vitamina b12", "cobalamina"],
            "vhs": ["vhs hemossedimentacao", "vhs hemossedimentacao exames laboratoriais", "velocidade de hemossedimentacao"],
            "tsh ultra": ["hormonio tireoestimulante", "tsh"],
            "urocultura": ["cultura de urina (urocultura)", "pesquisa de bacterias na urina"],
            "antibiogram": ["teste de sensibilidade a antibioticos (antibiograma)"],
            # V83 Synonyms
            "complemento c3": ["c3", "complemento c3"],
            "complemento c4": ["c4", "complemento c4"],
            "ch 50": ["ch50", "complemento ch50"],
            "dosagens de imunoglobulinas igg": ["igg", "imunoglobulina g"],
            "dosagens de imunoglobulinas igm": ["igm", "imunoglobulina m"],
            "dosagens de imunoglobulinas iga": ["iga", "imunoglobulina a"],
            "igg": ["imunoglobulina g", "dosagem de igg"],
            "igm": ["imunoglobulina m", "dosagem de igm"],
            "iga": ["imunoglobulina a", "dosagem de iga"],
            "colesterol total": ["colesterol total e fracoes"],
            "gama gt": ["gama glutamil transferase", "gama - gt", "ggt"],
            "gama-gt": ["gama glutamil transferase", "gama gt", "ggt"],
            "pcr": ["proteina c reativa", "pcr ultra sensivel"],
        }
        
        seen_terms = set()
        
        # Regex para datas
        import re
        date_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')

        # Caracteres de bullet point (NÃO remove espaços \s para não quebrar Vitamina D)
        clean_pattern = re.compile(r'[\*•-]')
        
        valid_terms = []
        for term in terms:
            clean_term = clean_pattern.sub('', term).strip(". :-")
            
            # V63: Allow short valid medical codes (C3, C4, T3, etc.)
            clean_upper = clean_term.upper()
            is_valid_short = clean_upper in ["C3", "C4", "T3", "T4", "CK", "PTA", "K+", "NA+", "CA", "P", "MG", "FE", "LI", "CL", "ZN", "LDH", "IMG", "IGG", "IGA", "IGE"]
            
            if len(clean_term) < 3 and not is_valid_short: continue
            if date_pattern.search(clean_term): continue
            
            term_lower = clean_term.lower()
            if term_lower in ["solicito", "paciente", "data", "crm", "assinatura"]: continue
            if term_lower.startswith("dr.") or term_lower.startswith("dra."): continue
            
            valid_terms.append(clean_term)
            
        results["stats"]["total"] = len(valid_terms)
        
        # V85: Vitta Resolute AI Pipeline - Standardize BEFORE search
        try:
            resolute_items = resolute_orchestrator.standardize_batch(valid_terms)
        except Exception as e:
            print(f"⚠️ Resolute Pipeline Error: {e}")
            resolute_items = [{"original": t, "resolved": t, "source": "fallback"} for t in valid_terms]

        for res_item in resolute_items:
            original_term = res_item["original"]
            resolved_term = res_item["resolved"]
            
            # Diagnostic for expert
            # print(f"🔍 Cruzando: '{original_term}' (AI: '{resolved_term}')")
            
            item = {"term": original_term, "resolved_term": resolved_term, "status": "not_found", "matches": [], "original_term": original_term}
            
            # Normaliza o termo de busca (sem acentos, lower)
            term_norm = ValidationService.normalize_text(resolved_term)
            
            # --- PRIORIDADE 0: Mapeamento Aprendido (Knowledge Base) ---
            learned_target = learning_service.get_learned_match(term_norm)
            if learned_target:
                print(f"🎯 Aplicando conhecimento aprendido: '{original_term}' -> '{learned_target}'")
                target_key = ValidationService.normalize_text(learned_target)
                
                if target_key in exam_map:
                    results["items"].append({
                        "term": original_term,
                        "status": "confirmed",
                        "matches": exam_map[target_key]
                    })
                    results["stats"]["confirmed"] += 1
                    seen_terms.add(original_term)
                    continue

            # 1. Checar duplicidade na lista atual
            if term_norm in seen_terms:
                item["status"] = "duplicate"
                results["items"].append(item)
                continue
            
            seen_terms.add(term_norm)
            
            # --- V100.0 MULTI-STAGE MATCHING PIPELINE ---
            found_matches = []
            strategy = "none"
            
            # Sub-etapas de normalização
            term_norm = ValidationService.normalize_text(resolved_term)
            orig_norm = ValidationService.normalize_text(original_term)
            
            # Lista de variantes para tentar buscar
            search_variants = [
                {"text": term_norm, "tag": "resolved"},
                {"text": orig_norm, "tag": "original"}
            ]
            
            # Se forem muito diferentes, adiciona sinônimos de ambos
            for var in list(search_variants):
                if var["text"] in SYNONYMS:
                    for syn in SYNONYMS[var["text"]]:
                        search_variants.append({"text": ValidationService.normalize_text(syn), "tag": f"synonym_of_{var['tag']}"})

            # STAGE 1: Exact Match on any variant
            for var in search_variants:
                if var["text"] in exam_map:
                    found_matches = exam_map[var["text"]]
                    strategy = f"exact_{var['tag']}"
                    break
            
            # STAGE 2: TUSS Lookup
            if not found_matches:
                tuss_name = tuss_service.search(original_term) or tuss_service.search(resolved_term)
                if tuss_name:
                    tuss_key = ValidationService.normalize_text(tuss_name)
                    if tuss_key in exam_map:
                        found_matches = exam_map[tuss_key]
                        strategy = "tuss_match"

            # STAGE 3: Substring Search (More conservative)
            if not found_matches:
                for var in search_variants:
                    v_text = var["text"]
                    if len(v_text) < 4: continue
                    for key in exam_keys:
                        if v_text == key or (len(v_text) > 5 and (v_text in key or key in v_text)):
                            found_matches.extend(exam_map[key])
                    if found_matches:
                        strategy = f"substring_{var['tag']}"
                        break

            # STAGE 4: Token Overlap Discovery (V100.0 Power Feature)
            # Find exams that contain all essential tokens of the search term
            if not found_matches:
                for var in search_variants:
                    v_tokens = set(var["text"].split())
                    if not v_tokens: continue
                    # Essential tokens: > 2 chars OR specific medical codes/letters
                    essential_v = {t for t in v_tokens if len(t) > 2 or t in ["d", "k", "p", "ca", "fe", "zn", "c3", "c4"]}
                    if not essential_v: continue
                    
                    for key in exam_keys:
                        k_tokens = set(key.split())
                        if essential_v.issubset(k_tokens):
                            found_matches.extend(exam_map[key])
                    
                    if found_matches:
                        strategy = f"token_overlap_{var['tag']}"
                        break

            # STAGE 5: Smart Fuzzy Search
            if not found_matches:
                for var in search_variants:
                    v_text = var["text"]
                    min_score_threshold = 95 if len(v_text) <= 3 else 75
                    best_results = fuzzy_matcher.find_top_matches(v_text, limit=3, min_score=min_score_threshold)
                    if best_results:
                        for match in best_results:
                            found_matches.extend(exam_map[match["match"]])
                        strategy = f"fuzzy_{var['tag']}"
                        break


            # 3. SEMANTIC AI MATCH (V67 - Smart Match) =====================
            # If standard fuzzy failed, ask Gemini to normalize the term
            # Collect candidates first to batch (but for now we do inside the loop or just before returning?)
            # PROB: We are inside a loop `for term in terms`. Batching requires refactoring loop.
            # WORKAROUND: For V67, we do one-by-one or small batch inside?
            # Generating content 10 times is slow.
            # OPTION B: Run Semantic Step AFTER the loop for all "not_found" items?
            # Yes. Let's finish the loop, then re-process "not_found" items.
            pass

            # Processar resultado encontrado
            if found_matches:

                unique_matches = {}
                for m in found_matches:
                    unique_matches[m['item_id']] = m
                
                matches_list = list(unique_matches.values())
                
                # --- HEURÍSTICA DE MATERIAL BIOLÓGICO (V44 Fix) ---
                # Se o termo original mencionar material, prioriza matches que contenham esse material
                material_keywords = {
                    "fecal": "fezes", "fezes": "fezes",
                    "sangue": "sangue", "sanguineo": "sangue", "serico": "serico",
                    "urina": "urina", "urinario": "urina",
                }
                boost_keywords = []
                for kw, target in material_keywords.items():
                    if kw in term_norm:
                        boost_keywords.append(target)
                
                # V86: Improved sorting with token-overlap boost
                def get_overlap(candidate_name):
                    c_norm = ValidationService.normalize_text(candidate_name)
                    t_tokens = set(term_norm.split())
                    c_tokens = set(c_norm.split())
                    return len(t_tokens.intersection(c_tokens))

                matches_list.sort(key=lambda x: (
                    -get_overlap(x['item_name']), # High overlap is better
                    0 if any(bk in ValidationService.normalize_text(x['item_name']) for bk in boost_keywords) else 1, # Material match boost
                    0 if term_norm == ValidationService.normalize_text(x['search_name']) else 1, # Exact
                    0 if term_norm in ValidationService.normalize_text(x['search_name']) else 1, # Contained
                    abs(len(x['search_name']) - len(term_norm)),
                    len(x['search_name']),
                    x['search_name']
                ))

                item["matches"] = matches_list
                item["selectedMatch"] = 0
                
                is_perfect_match = (strategy in ["exact", "synonym", "tuss_exact"]) or (ValidationService.normalize_text(matches_list[0]['search_name']) == term_norm)
                
                if len(matches_list) == 1 or is_perfect_match:
                    item["status"] = "confirmed"
                    results["stats"]["confirmed"] += 1
                else:
                    item["status"] = "multiple"
                    results["stats"]["pending"] += 1
                
                if strategy in ["fuzzy", "substring", "fuzzy_synonym"]:
                    missing_terms_logger.log_fuzzy_match(
                        term=original_term,
                        matched_exam=matches_list[0]['search_name'],
                        strategy=strategy,
                        unit=unit
                    )
                
                item["match_strategy"] = strategy
            else:
                pdca_service.log_fca(original_term, unit, "not_found", matches=[])
                missing_terms_logger.log_not_found(term=original_term, unit=unit)
                results["stats"]["not_found"] += 1
                
                # V62/V63: Last Resort - Create Generic Match from Simplified Term
                # If we have a simplified code-like term (e.g. "IgG", "C4"), but it wasn't in the DB,
                # we create a placeholder so the user sees something instead of "0 exams".
                tokens = term_norm.split()
                if len(tokens) > 0:
                    fallback_name = tokens[-1].upper()
                    # Only for code-like terms
                    if len(fallback_name) <= 4 or fallback_name.startswith("ANTI"):
                        # V63: Use 'multiple' status so it counts as Pending (Yellow) in frontend
                        item["status"] = "multiple" 
                        item["matches"] = [{
                            "item_id": 99999, # Safe Mock ID
                            "item_name": f"{fallback_name} (Verificar Cadastro)",
                            "search_name": fallback_name,
                            "price": 0.0,
                            "unit_name": unit
                        }]
                        item["selectedMatch"] = None # Force user to look (or default select?) None is safer for "Pending"
                        item["match_strategy"] = "manual_fallback"
                        results["stats"]["pending"] += 1
                        results["stats"]["not_found"] -= 1 # Correct stat
                
            results["items"].append(item)
            
        
        # --- V67: SEMANTIC BATCH PROCESSING ("Smart Match") ---
        # Filter items that are still "not_found" (and not just placeholder mocks if we implement semantics before mocks)
        # Actually, V62 mocks have status="multiple". Real failures have "not_found".
        # Let's collect items that are "not_found" OR "manual_fallback" (if we want to improve them) -> No, mock is last resort.
        
        candidates = []
        candidate_indices = []
        
        for idx, item in enumerate(results["items"]):
            # V69: Include "manual_fallback" items (which are status="multiple") so AI can try to fix them too.
            # V67 only checked "not_found".
            is_candidate = (
                item["status"] == "not_found" and len(item["term"]) > 3 or
                item.get("match_strategy") == "manual_fallback"
            )
            
            if is_candidate:
                candidates.append(item["term"])
                candidate_indices.append(idx)
        
        if candidates:
            # Import locally to avoid circular deps
            try:
                from services.semantic_service import semantic_service
                print(f"🧠 Semantic Service: Normalizando {len(candidates)} termos...")
                
                normalized_map = semantic_service.normalize_batch(candidates)
                
                for i, original_term in zip(candidate_indices, candidates):
                    if original_term in normalized_map:
                        normalized_term = normalized_map[original_term]
                        if not normalized_term: continue
                        
                        print(f"🧠 AI Normalized: '{original_term}' -> '{normalized_term}'")
                        
                        # Run Fuzzy Match on Normalized Term
                        norm_key = ValidationService.normalize_text(normalized_term)
                        
                        # 1. Exact/Map Check
                        if norm_key in exam_map:
                            matches = exam_map[norm_key]
                            results["items"][i]["matches"] = matches
                            results["items"][i]["status"] = "confirmed" if len(matches) == 1 else "multiple"
                            results["items"][i]["match_strategy"] = "ai_semantic_exact"
                            results["stats"]["not_found"] -= 1
                            results["stats"]["confirmed" if len(matches) == 1 else "pending"] += 1
                            # V86 Fix: Use direct 'unit' variable
                            pdca_service.log_fca(original_term, unit, "ai_semantic_exact", "ai_semantic_exact", matches)
                            continue

                        # 2. Fuzzy Check
                        best_match = fuzzy_matcher.find_best_match(norm_key, min_score=70)
                        if best_match:
                            match_name = best_match["match"]
                            matches = exam_map[match_name]
                            results["items"][i]["matches"] = matches
                            results["items"][i]["status"] = "confirmed" if len(matches) == 1 else "multiple"
                            results["items"][i]["match_strategy"] = "ai_semantic_fuzzy"
                            results["items"][i]["normalized_term"] = normalized_term
                            results["stats"]["not_found"] -= 1
                            results["stats"]["confirmed" if len(matches) == 1 else "pending"] += 1
                            # V86 Fix: Use direct 'unit' variable
                            pdca_service.log_fca(original_term, unit, "ai_semantic_fuzzy", "ai_semantic_fuzzy", matches)
            except Exception as e:
                print(f"❌ Erro Semantic Service: {e}")
        
        # Add Semantic Status to Stats
        try:
            from services.semantic_service import semantic_service
            results["stats"]["semantic_active"] = semantic_service.model is not None
        except:
            results["stats"]["semantic_active"] = False

        return results

    @staticmethod
    def get_fuzzy_suggestions(term: str, all_exam_names: List[str]) -> List[str]:
        return get_close_matches(term, all_exam_names, n=3, cutoff=0.6)

# Singleton global instance
validation_service = ValidationService()
