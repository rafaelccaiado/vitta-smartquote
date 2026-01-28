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
    def validate_batch(terms: List[str], unit: str, bq_client: Any) -> Dict[str, Any]:
        results = {
            "items": [],
            "stats": {"confirmed": 0, "pending": 0, "not_found": 0, "total": 0}
        }
        
        # 1. Carregar catálogo completo (Cache Local) - O(1) Query
        print(f"Carregando catálogo para unidade: {unit}...")
        all_exams = bq_client.get_all_exams(unit)
        
        # Mapa para busca exata rápida: "termo lower" -> Objeto Exame
        # Se houver duplicatas no banco, armazena lista
        exam_map = {}
        for exam in all_exams:
            name_key = exam["search_name"]
            if name_key not in exam_map:
                exam_map[name_key] = []
            exam_map[name_key].append(exam)
            
        exam_keys = list(exam_map.keys()) # Para fuzzy search
        
        # Atualizar FuzzyMatcher com os exames reais da unidade
        fuzzy_matcher.update_known_exams(exam_keys)
        
        # Dicionário de Sinônimos Médicos (Alias -> [Possíveis Nomes no Banco])
        # ... (rest of SYNONYMS remains the same)
        SYNONYMS = {
            "eas": ["urina tipo i", "urina tipo 1", "sumario de urina", "elementos anormais do sedimento"],
            "elementos anormais do sedimento": ["urina tipo i"],
            "urina tipo i": ["urina tipo i", "eas"],
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
            "h.pylori": ["antigeno helicobacter pylori"],
            "h pylori": ["antigeno helicobacter pylori"],
            "pylori": ["antigeno helicobacter pylori"],
            "helicobacter pylori": ["antigeno helicobacter pylori"],
            "antigeno fecal": ["antigeno helicobacter pylori"],
            "pesquisa antigeno fecal para h.pylori": ["antigeno helicobacter pylori"],
            "tsh": ["hormonio tireoestimulante", "tsh ultra sensivel"],
            "fsh": ["hormonio foliculo estimulante", "dosagem de hormonio foliculo estimulante", "fsh"],
            "hormonio foliculo estimulante": ["hormonio foliculo estimulante", "fsh"],
            "t4 livre": ["tiroxina livre", "t4"],
            "ureia": ["dosagem de ureia", "ureia"],
            "creatinina": ["dosagem de creatinina", "creatinina"],
            "acido urico": ["dosagem de acido urico", "acido urico"],
            "beta hcg": ["beta hcg qualitativo", "beta hcg quantitativo"],
            "grupo sanguineo": ["tipagem sanguinea", "grupo sanguineo fator rh"]
        }
        
        seen_terms = set()
        
        # Regex para datas (dd/mm/aa ou dd/mm/aaaa)
        import re
        date_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')

        # Caracteres de bullet point comuns para remover
        clean_pattern = re.compile(r'^[\s\-\*\•\>]+')
        
        valid_terms = []

        for term in terms:
            # 1. Limpeza básica (remove bullets no inicio e pontuação no final)
            clean_term = clean_pattern.sub('', term).strip(" .:;-")
            
            # 2. Filtros de exclusão (Ruído)
            if len(clean_term) < 3: continue # Muito curto
            if date_pattern.search(clean_term): continue # É data
            
            # Palavras banidas (exatas ou contidas)
            term_lower = clean_term.lower()
            if term_lower in ["solicito", "paciente", "data", "crm", "assinatura"]: continue 
            if term_lower.startswith("dr.") or term_lower.startswith("dra."): continue
            
            valid_terms.append(clean_term)
            
        results["stats"]["total"] = len(valid_terms)
        
        # 0. Instancia Learning Service
        from services.learning_service import learning_service

        for term in valid_terms:
            item = {"term": term, "status": "not_found", "matches": [], "original_term": term}
            term_lower = term.lower()
            
            # --- PRIORIDADE 0: Mapeamento Aprendido (Knowledge Base) ---
            learned_target = learning_service.get_learned_match(term_lower)
            if learned_target:
                print(f"🧠 Aplicando conhecimento aprendido: '{term}' -> '{learned_target}'")
                
                # Tenta match exato no target aprendido no MAPA
                # O target aprendido DEVE ser chave do exam_map (search_name)
                # target_lower = learned_target.lower() 
                # Mas exam_map keys já são lower
                target_key = learned_target.lower().strip()
                
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
            if term_lower in seen_terms:
                item["status"] = "duplicate"
                results["items"].append(item)
                continue
            
            seen_terms.add(term_lower)
            
            found_matches = []
            strategy = "none"

            # 2a. TUSS Lookup (Prioridade Máxima vs ANS)
            tuss_name = tuss_service.search(term)
            if tuss_name:
                tuss_key = tuss_name.lower()
                if tuss_key in exam_map:
                    found_matches = exam_map[tuss_key]
                    strategy = "tuss_exact"

            # 2b. Busca Exata Direta
            if not found_matches and term_lower in exam_map:
                found_matches = exam_map[term_lower]
                strategy = "exact"
            
            # 2b. Busca por Sinônimos (se falhar exata)
            if not found_matches:
                # 1. Tenta direto no dicionario (Alias exato)
                if term_lower in SYNONYMS:
                    for syn in SYNONYMS[term_lower]:
                        if syn in exam_map:
                            found_matches = exam_map[syn]
                            strategy = "synonym"
                            break
                
                # 2. Tenta Fuzzy no dicionario (Alias com erro de digitacao)
                if not found_matches:
                    synonym_keys = list(SYNONYMS.keys())
                    close_synonyms = get_close_matches(term_lower, synonym_keys, n=1, cutoff=0.7)
                    if close_synonyms:
                        matched_key = close_synonyms[0]
                        for syn in SYNONYMS[matched_key]:
                            if syn in exam_map:
                                found_matches = exam_map[syn]
                                strategy = f"fuzzy_synonym ({matched_key})"
                                break

            # 2c. Substring Search (Se o termo digitado é parte do nome do exame)
            if not found_matches and len(term_lower) > 3:
                for key in exam_keys:
                    if term_lower in key: 
                        found_matches.extend(exam_map[key])
                    elif key in term_lower:
                        found_matches.extend(exam_map[key])
                if found_matches: strategy = "substring"

            # 2d. Smart Fuzzy Search usando o novo FuzzyMatcher
            if not found_matches:
                # Usa o algoritmos de similaridade do RapidFuzz via FuzzyMatcher
                best_results = fuzzy_matcher.find_top_matches(term_lower, limit=5, min_score=60)
                if best_results:
                    for match in best_results:
                        match_name = match["match"]
                        found_matches.extend(exam_map[match_name])
                    strategy = "fuzzy_smart"
                
                # Fallback para difflib se falhar o smart (raro)
                if not found_matches:
                    close_names = get_close_matches(term_lower, exam_keys, n=5, cutoff=0.5) 
                    for name in close_names:
                        found_matches.extend(exam_map[name])
                    if found_matches: strategy = "fuzzy_fallback"

            # Processar resultados encontrados
            if found_matches:
                # Remove duplicatas de ID na lista de matches
                unique_matches = {}
                for m in found_matches:
                    unique_matches[m['item_id']] = m
                
                # LISTA FINAL
                matches_list = list(unique_matches.values())
                
                # --- ALGORITMO DE RANKING DE SUGESTÕES ---
                # Ordena por relevância para o termo original
                # Critério 1: Contém o termo exato (Prioridade Máxima)
                # Critério 2: Menor diferença de tamanho (Prefere exames "puros" vs compostos)
                # Critério 3: Match alfabético
                
                matches_list.sort(key=lambda x: (
                    0 if term_lower == x['search_name'] else 1, # Exato primeiro
                    0 if term_lower in x['search_name'] else 1, # Contido segundo
                    len(x['search_name']), # Menor tamanho terceiro ("Ureia" antes de "Ureia 24h")
                    x['search_name']
                ))

                item["matches"] = matches_list
                item["selectedMatch"] = 0 # Auto-seleciona o primeiro (Melhor Rank)
                
                # Define status
                # Se validou algo com muita certeza (Exato ou Synonym), marca Confirmed
                # Se foi Fuzzy ou Substring genérica e tem muitos, marca Multiple
                
                is_perfect_match = (strategy in ["exact", "synonym", "tuss_exact"]) or (matches_list[0]['search_name'] == term_lower)
                
                if len(matches_list) == 1 or is_perfect_match:
                    item["status"] = "confirmed"
                    results["stats"]["confirmed"] += 1
                else:
                    # Se tiver matches mas não perfeitos, deixa para o usuário confirmar
                    item["status"] = "multiple"
                    results["stats"]["pending"] += 1
                
                # Log para curadoria: termos que só matcharam via fuzzy/substring
                if strategy in ["fuzzy", "substring", "fuzzy_synonym"]:
                    missing_terms_logger.log_fuzzy_match(
                        term=term,
                        matched_exam=matches_list[0]['search_name'],
                        strategy=strategy,
                        unit=unit
                    )
                
                item["match_strategy"] = strategy
            else:
                # Log para curadoria: termos não encontrados
                missing_terms_logger.log_not_found(term=term, unit=unit)
                results["stats"]["not_found"] += 1
                
            results["items"].append(item)
            
        return results

    @staticmethod
    def get_fuzzy_suggestions(term: str, all_exam_names: List[str]) -> List[str]:
        return get_close_matches(term, all_exam_names, n=3, cutoff=0.6)
