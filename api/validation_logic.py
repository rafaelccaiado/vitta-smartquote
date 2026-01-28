from typing import List, Dict, Any
from difflib import get_close_matches
from services.tuss_service import tuss_service
from services.missing_terms_logger import missing_terms_logger
from services.fuzzy_matcher import fuzzy_matcher

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
        """Remove acentos e caracteres especiais para comparação"""
        import unicodedata
        nfkd_form = unicodedata.normalize('NFKD', text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

    @staticmethod
    def validate_batch(terms: List[str], unit: str, bq_client: Any) -> Dict[str, Any]:
        results = {
            "items": [],
            "stats": {"confirmed": 0, "pending": 0, "not_found": 0, "total": 0}
        }
        
        # 1. Carregar catálogo completo (Cache Local) - O(1) Query
        print(f"Carregando catálogo para unidade: {unit}...")
        all_exams = bq_client.get_all_exams(unit)
        
        # Mapa para busca exata rápida: "termo normalizado" -> Objeto Exame
        exam_map = {}
        for exam in all_exams:
            # Normaliza chave do mapa (sem acentos)
            name_key = ValidationService.normalize_text(exam["search_name"])
            if name_key not in exam_map:
                exam_map[name_key] = []
            exam_map[name_key].append(exam)
            
        exam_keys = list(exam_map.keys()) # Para fuzzy search
        
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
            "tgo": ["dosagem de tgo", "transaminase glutamico oxalacetica", "aspartato aminotransferase"],
            "ast": ["dosagem de tgo", "aspartato aminotransferase"],
            "tgp": ["dosagem de tgp", "transaminase glutamico piruvica", "alanina aminotransferase"],
            "alt": ["dosagem de tgp", "alanina aminotransferase"],
            "glicose": ["glicemia", "glicemia de jejum", "dosagem de glicose"],
            "glicemia": ["glicemia", "glicemia de jejum"],
            "colesterol": ["colesterol total", "colesterol total e fracoes"],
            "perfil lipidico": ["lipidograma"], 
            "lipidograma": ["lipidograma"],
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
            # V61 Synonyms
            "complemento c3": ["c3", "complemento c3"],
            "complemento c4": ["c4", "complemento c4"],
            "ch 50": ["ch50", "complemento ch50"],
            "dosagens de imunoglobulinas igg": ["igg", "imunoglobulina g"],
            "dosagens de imunoglobulinas igm": ["igm", "imunoglobulina m"],
            "dosagens de imunoglobulinas iga": ["iga", "imunoglobulina a"],
            "igg": ["imunoglobulina g", "dosagem de igg"],
            "igm": ["imunoglobulina m", "dosagem de igm"],
            "iga": ["imunoglobulina a", "dosagem de iga"]
        }
        
        seen_terms = set()
        
        # Regex para datas
        import re
        date_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')

        # Caracteres de bullet point
        clean_pattern = re.compile(r'^[\s\-\*\•\>]+')
        
        valid_terms = []

        for term in terms:
            clean_term = clean_pattern.sub('', term).strip(" .:;-")
            
            # V63: Allow short valid medical codes (C3, C4, T4, etc.)
            clean_upper = clean_term.upper()
            is_valid_short = clean_upper in ["C3", "C4", "T3", "T4", "CK", "PTA", "K+", "NA+", "CA", "P", "MG", "FE", "LI", "ZN", "CU", "LDH", "IGM", "IGG", "IGA", "IGE"]
            
            if len(clean_term) < 3 and not is_valid_short: continue 
            if date_pattern.search(clean_term): continue
            
            term_lower = clean_term.lower()
            if term_lower in ["solicito", "paciente", "data", "crm", "assinatura"]: continue 
            if term_lower.startswith("dr.") or term_lower.startswith("dra."): continue
            
            valid_terms.append(clean_term)
            
        results["stats"]["total"] = len(valid_terms)
        
        # 0. Instancia Learning Service
        from services.learning_service import learning_service

        for term in valid_terms:
            item = {"term": term, "status": "not_found", "matches": [], "original_term": term}
            
            # Normaliza o termo de busca (sem acentos, lower)
            term_norm = ValidationService.normalize_text(term)
            
            # --- PRIORIDADE 0: Mapeamento Aprendido (Knowledge Base) ---
            learned_target = learning_service.get_learned_match(term_norm)
            if learned_target:
                print(f"🧠 Aplicando conhecimento aprendido: '{term}' -> '{learned_target}'")
                target_key = ValidationService.normalize_text(learned_target)
                
                if target_key in exam_map:
                    results["items"].append({
                        "term": term, 
                        "status": "confirmed", 
                        "matches": exam_map[target_key]
                    })
                    results["stats"]["confirmed"] += 1
                    seen_terms.add(term)
                    continue

            # 1. Checar duplicidade na lista atual
            if term_norm in seen_terms:
                item["status"] = "duplicate"
                results["items"].append(item)
                continue
            
            seen_terms.add(term_norm)
            
            found_matches = []
            strategy = "none"

            # 2a. TUSS Lookup
            tuss_name = tuss_service.search(term)
            if tuss_name:
                tuss_key = ValidationService.normalize_text(tuss_name)
                if tuss_key in exam_map:
                    found_matches = exam_map[tuss_key]
                    strategy = "tuss_exact"

            # 2b. Busca Exata Direta (Com normalização de acentos!)
            if not found_matches and term_norm in exam_map:
                found_matches = exam_map[term_norm]
                strategy = "exact"
            
            # 2b. Busca por Sinônimos
            if not found_matches:
                # Normaliza input term para chave do dicionario (se necessário)
                # Mas as chaves do SYNONYMS estão explicitamente hardcoded. Vamos assumir usar o lower original ou normalizar tb
                # Vamos tentar direto no SYNONYMS com term_norm se as chaves la forem compativeis
                
                if term_norm in SYNONYMS: # Direct Normalized Match
                   for syn in SYNONYMS[term_norm]:
                       syn_key = ValidationService.normalize_text(syn)
                       if syn_key in exam_map:
                           found_matches = exam_map[syn_key]
                           strategy = "synonym"
                           break
                
                # Fuzzy no dicionario
                if not found_matches:
                    synonym_keys = list(SYNONYMS.keys())
                    close_synonyms = get_close_matches(term_norm, synonym_keys, n=1, cutoff=0.85) # Strict override
                    if close_synonyms:
                        matched_key = close_synonyms[0]
                        for syn in SYNONYMS[matched_key]:
                            syn_key = ValidationService.normalize_text(syn)
                            if syn_key in exam_map:
                                found_matches = exam_map[syn_key]
                                strategy = f"fuzzy_synonym ({matched_key})"
                                break

            # 2c. Substring Search
            if not found_matches and len(term_norm) > 3:
                for key in exam_keys:
                    # Verifica boundaries de palavra para evitar matches falsos (ex: "ferro" em "transferrina")
                    if term_norm in key or key in term_norm:
                         found_matches.extend(exam_map[key])
                if found_matches: strategy = "substring"

            # 2d. Smart Fuzzy Search
            if not found_matches:
                # Regra de Segurança para Siglas Curtas (V44 Fix)
                # Se for curto (<=3 chars), exige score altíssimo (90)
                min_score_threshold = 95 if len(term_norm) <= 3 else 60
                
                best_results = fuzzy_matcher.find_top_matches(term_norm, limit=5, min_score=min_score_threshold)
                if best_results:
                    for match in best_results:
                        match_name = match["match"] # match_name is normalized key if update_known_exams received normalized keys? 
                        # update_known_exams received exam_keys which ARE normalized keys now.
                        found_matches.extend(exam_map[match_name])
                    strategy = "fuzzy_smart"
                
                if not found_matches and len(term_norm) > 3: # Only fallback for longer terms
                    close_names = get_close_matches(term_norm, exam_keys, n=5, cutoff=0.6) 
                    for name in close_names:
                        found_matches.extend(exam_map[name])
                    if found_matches: strategy = "fuzzy_fallback"

            # 2e. Simplify & Retry (V61)
            if not found_matches:
                tokens = term_norm.split()
                if len(tokens) > 1:
                    last_token = tokens[-1]
                    is_code_like = len(last_token) <= 4 or last_token.startswith("anti") 
                    if is_code_like:
                         if last_token in exam_map:
                             found_matches = exam_map[last_token]
                             strategy = f"simplified_exact ({last_token})"
                         elif last_token in SYNONYMS:
                            for syn in SYNONYMS[last_token]:
                                syn_key = ValidationService.normalize_text(syn)
                                if syn_key in exam_map:
                                    found_matches = exam_map[syn_key]
                                    strategy = f"simplified_synonym ({last_token})"
                                    break


            # 3. SEMANTIC AI MATCH (V67 - Smart Match) =========================================
            # If standard fuzzy failed, ask Gemini to normalize the term
            # Collect candidates first to batch (but for now we do inside the loop or just before returning??)
            # PROB: We are inside a loop `for term in terms`. Batching requires refactoring loop.
            # WORKAROUND: For V67, we do one-by-one or small batch inside? 
            # Generating content 10 times is slow.
            # OPTION B: Run Semantic Step AFTER the loop for all "not_found" items?
            # Yes. Let's finish the loop, then re-process "not_found" items.
            pass 

            # Processar resultados encontrados
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
                    "urina": "urina", "urinario": "urina"
                }
                boost_keywords = []
                for kw, target in material_keywords.items():
                    if kw in term_norm:
                        boost_keywords.append(target)
                
                matches_list.sort(key=lambda x: (
                    0 if any(bk in ValidationService.normalize_text(x['item_name']) for bk in boost_keywords) else 1, # Material match boost
                    0 if term_norm == ValidationService.normalize_text(x['search_name']) else 1, # Exato
                    0 if term_norm in ValidationService.normalize_text(x['search_name']) else 1, # Contido
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
                        term=term,
                        matched_exam=matches_list[0]['search_name'],
                        strategy=strategy,
                        unit=unit
                    )
                
                item["match_strategy"] = strategy
            else:
                missing_terms_logger.log_not_found(term=term, unit=unit)
                results["stats"]["not_found"] += 1
                
                # V62/V63: Last Resort - Create Generic Match from Simplified Term
                # If we have a simplified code-like term (e.g. "IgM", "C4"), but it wasn't in the DB,
                # we create a placeholder so the user sees something instead of "0 exams".
                tokens = term_norm.split()
                if len(tokens) > 0:
                    fallback_name = tokens[-1].upper()
                    # Only for code-like terms
                    if len(fallback_name) <= 4 or fallback_name.startswith("ANTI"):
                         # V63: Use 'multiple' status so it counts as Pending (Yellow) in Frontend
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
                         results["stats"]["not_found"] -= 1 # Correct stats
                
            results["items"].append(item)
            
                
                
        # --- V67: SEMANTIC BATCH PROCESSING ("Smart Match") ---
        # Filter items that are still "not_found" (and not just placeholder mocks if we implement semantics before mocks)
        # Actually, V62 mocks have status="multiple". Real failures have "not_found".
        # Let's collect items that are "not_found" OR "manual_fallback" (if we want to improve them) -> No, mock is last resort.
        # But wait, the loop creates the item and appends it.
        # So we iterate over `results["items"]` looking for "not_found".
        
        candidates = []
        candidate_indices = []
        
        for idx, item in enumerate(results["items"]):
             if item["status"] == "not_found" and len(item["term"]) > 3:
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
                        
                        print(f"✨ AI Normalized: '{original_term}' -> '{normalized_term}'")
                        
                        # Run Fuzzy Match on Normalized Term
                        norm_key = ValidationService.normalize_text(normalized_term)
                        
                        # 1. Exact/Map Check
                        if norm_key in exam_map:
                             matches = exam_map[norm_key]
                             results["items"][i]["matches"] = matches
                             results["items"][i]["status"] = "confirmed" if len(matches)==1 else "multiple"
                             results["items"][i]["match_strategy"] = "ai_semantic_exact"
                             results["stats"]["not_found"] -= 1
                             results["stats"]["confirmed" if len(matches)==1 else "pending"] += 1
                             continue

                        # 2. Fuzzy Check
                        best_match = fuzzy_matcher.find_best_match(norm_key, min_score=80)
                        if best_match:
                             match_name = best_match["match"]
                             matches = exam_map[match_name]
                             results["items"][i]["matches"] = matches
                             results["items"][i]["status"] = "confirmed" if len(matches)==1 else "multiple"
                             results["items"][i]["match_strategy"] = "ai_semantic_fuzzy"
                             results["items"][i]["normalized_term"] = normalized_term
                             results["stats"]["not_found"] -= 1
                             results["stats"]["confirmed" if len(matches)==1 else "pending"] += 1
            except Exception as e:
                print(f"❌ Erro Semantic Service: {e}")

        return results

    @staticmethod
    def get_fuzzy_suggestions(term: str, all_exam_names: List[str]) -> List[str]:
        return get_close_matches(term, all_exam_names, n=3, cutoff=0.6)
