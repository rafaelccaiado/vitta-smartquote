from typing import Dict, Any, List, Tuple, Optional
import requests
from google.auth.transport.requests import Request
import io
import traceback
from PIL import Image
import re
from auth_utils import get_gcp_credentials

# Novo pipeline de OCR
from services.image_preprocessor import image_preprocessor
from services.llm_interpreter import llm_interpreter
import json
import unicodedata

import os

class OCRProcessor:
    def __init__(self):
        print("Inicializando OCRProcessor com Google Cloud Vision API ☁️")
        try:
            self.creds = get_gcp_credentials()
            if self.creds:
                 print("🔑 Credenciais carregadas com sucesso via auth_utils!")
            else:
                 print("⚠️ Credenciais retornaram None. OCP irá falhar.")
                 
            print("OCR Processor (REST Mode) inicializado!")
            self.init_error = None
            
            # Novos componentes do pipeline
            self.use_preprocessing = True
            
            # Carregar Dicionário de Exames (V80.0)
            self.exams_dict = self._load_exams_dictionary()
            
            # Prepara estruturas de busca otimizadas
            self.exams_flat_list = self._flatten_dictionary() # Para Fuzzy
            self.exact_set = {self._normalizar_texto(name) for name, _ in self.exams_flat_list} # Para Phase A
            
            print(f"📖 Dicionário Médico Carregado: {len(self.exams_flat_list)} termos indexados.")
            
        except Exception as e:
            print(f"Erro ao inicializar Google Vision Client: {e}")
            self.init_error = str(e)
            self.client = None

    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Processa imagem com Pipeline 2-Phase Matching & Alta Cobertura.
        """
        if not self.creds:
            return {"error": f"CONFIG ERROR: GCP Credentials Missing. {self.init_error}", "status": "config_error"}

        try:
            # === CAMADA 1: ROI DETECTION & PRE-PROCESSAMENTO ===
            processed_image_bytes = image_bytes
            
            if self.use_preprocessing:
                try:
                    # Tenta melhorar contraste e remover sombras
                    processed_image_bytes = image_preprocessor.preprocess(image_bytes)
                except Exception as e:
                    print(f"⚠️ Warning: Preprocessing failed, using original: {e}")

            # === CAMADA 2: GOOGLE VISION OCR ===
            # === CAMADA 2: GOOGLE VISION OCR (VIA REST API) ===
            # Codificar imagem em base64
            import base64
            b64_image = base64.b64encode(processed_image_bytes).decode("utf-8")
            
            # Refresh token se necessário
            try:
                if not self.creds.valid:
                    auth_req = Request()
                    self.creds.refresh(auth_req)
                token = self.creds.token
            except Exception as e:
                return {"error": f"AUTH ERROR: Failed to refresh token. {e}", "status": "auth_error"}

            # Montar payload JSON
            url = "https://vision.googleapis.com/v1/images:annotate"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "requests": [
                    {
                        "image": {"content": b64_image},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                        "imageContext": {"languageHints": ["pt", "pt-BR"]}
                    }
                ]
            }

            response_obj = requests.post(url, headers=headers, json=payload)
            
            if response_obj.status_code != 200:
                return {"error": f"API ERROR {response_obj.status_code}: {response_obj.text}", "status": "error"}
            
            response_json = response_obj.json()
            # O JSON de resposta tem estrutura {"responses": [...]}
            # Pegamos o primeiro item da lista responses
            api_resp = response_json.get("responses", [{}])[0]

            if "error" in api_resp:
                return {"error": api_resp["error"].get("message"), "status": "error"}

            # Extração Bruta das Linhas (Adaptado para Dict)
            raw_lines = self._extrair_linhas(api_resp)
            
            # === CAMADA 3: FILTRAGEM & CLASSIFICAÇÃO (CANDIDATES) ===
            candidates = []
            
            # Thresholds Reais (Hardcoded para consistência com _match_term)
            THRESH_PHASE_A = 92
            THRESH_PHASE_B = 85
            
            # Metadados de execução
            stats = {
                "total_ocr_lines": len(raw_lines),
                "candidates_count": 0,
                "matched_count": 0,
                "unverified_count": 0, # Fallback items
                "fuzzy_used": False,
                "thresholds": {"phase_a": THRESH_PHASE_A, "phase_b": THRESH_PHASE_B, "short_token": 95}
            }
            
            for line in raw_lines:
                if self._is_valid_candidate(line):
                    candidates.append(line)

            stats["candidates_count"] = len(candidates)
            
            # === CAMADA 4: 2-PHASE MATCHING ===
            matched_exams = []
            
            for cand in candidates:
                # Fase A & B encapsuladas no matcher
                match_result = self._match_term(cand)
                
                if match_result:
                    corrected, score, method = match_result
                    
                    if "fuzzy" in method:
                        stats["fuzzy_used"] = True
                        
                    matched_exams.append({
                        "original": cand,
                        "corrected": corrected,
                        "confidence": score / 100.0,
                        "method": method
                    })
            
            # Deduplicação básica (nomes exatos iguais)
            unique_matches = {}
            for m in matched_exams:
                key = m["corrected"]
                if key not in unique_matches or m["confidence"] > unique_matches[key]["confidence"]:
                     unique_matches[key] = m
            matched_exams = list(unique_matches.values())
            
            stats["matched_count"] = len(matched_exams)

            # === CAMADA 5: FALLBACK INTELIGENTE ===
            fallback_used = False
            
            # Se temos candidatos (texto legível) mas ZERO matches (dicionário falhou)
            if not matched_exams and candidates:
                fallback_used = True
                print("⚠️ Fallback ativado: Texto detectado mas sem correspondência médica.")
                for cand in candidates[:10]: # Limita a 10 para não poluir
                     matched_exams.append({
                        "original": cand,
                        "corrected": f"{cand} [⚠️ Não Verificado]",
                        "confidence": 0.1,
                        "method": "fallback_raw"
                    })
            
            # Cálculo de Métricas QA
            verified_count = sum(1 for x in matched_exams if "fallback" not in x["method"])
            unverified_count = len(matched_exams) - verified_count
            total_returned = len(matched_exams)
            
            stats["unverified_count"] = unverified_count
            
            metrics = {
                "coverage": (len(raw_lines) > 0 and total_returned > 0),
                "verified_ratio": round(verified_count / max(1, total_returned), 2),
                "fallback_rate_flag": (unverified_count > 0)
            }

            # Montagem da Resposta
            clean_text = "\n".join([x["corrected"] for x in matched_exams])
            avg_conf = sum(x["confidence"] for x in matched_exams)/len(matched_exams) if matched_exams else 0.0

            return {
                "text": clean_text,
                "lines": matched_exams,
                "confidence": round(avg_conf, 2),
                "stats": {
                    "total_ocr_lines": len(raw_lines),
                    "classified_exams": len(candidates),
                    "valid_matches": len(matched_exams)
                },
                "backend_version": "V81.2-HighRecall-QA", # Version bump
                "model_used": "Vision -> 2-Phase Matcher -> QA Metrics",
                "debug_raw": candidates, 
                "debug_meta": {
                    "raw_ocr_lines_count": len(raw_lines),
                    "candidates_count": len(candidates),
                    "matched_count": verified_count, # Use verified only for clear stats
                    "unverified_count": unverified_count,
                    "total_returned": total_returned,
                    "fuzzy_used": stats["fuzzy_used"],
                    "thresholds": stats["thresholds"],
                    "dictionary_loaded": bool(self.exams_flat_list),
                    "dictionary_size": len(self.exams_flat_list),
                    "fallback_used": fallback_used,
                    "qa_metrics": metrics # New QA Section
                }
            }

        except Exception as e:
            print(f"Exceção no processamento OCR: {e}")
            traceback.print_exc()
            return {
                "text": "",
                "lines": [],
                "error": f"SERVER ERROR: {str(e)}",
                "debug_meta": {"error_trace": str(e)}
            }

    def _match_term(self, text: str) -> Optional[Tuple[str, float, str]]:
        """
        Implementa Matching em 2 Fases:
        Fase A: Alta Precisão (Normalização + Exact/Contains)
        Fase B: Alta Cobertura (Fuzzy Difflib - Pure Python)
        """
        text_norm = self._normalizar_texto(text)
        if not text_norm: return None

        # --- FASE B: Fuzzy Matching (Difflib) ---
        best_ratio = 0.0
        best_official = None
        best_norm_term = ""

        # Otimização: Se houver match exato, retorna imediatamente
        for norm_term, official_name in self.exams_flat_list:
            if text_norm == norm_term:
                return official_name, 100.0, "exact_match"
            
        from difflib import SequenceMatcher
        
        for norm_term, official_name in self.exams_flat_list:
            # SequenceMatcher.ratio() returns [0.0, 1.0] -> *100
            sm = SequenceMatcher(None, text_norm, norm_term)
            ratio = sm.ratio() * 100.0
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_official = official_name
                best_norm_term = norm_term

        score = best_ratio
        
        if not best_official:
            return None
            
        # === REGRAS DE CALIBRAÇÃO ===
        
        # Regra CRÍTICA para Siglas Curtas (2-4 chars)
        if len(text_norm) <= 4:
            if score >= 95:
                return best_official, score, "short_token_high_precision"
            return None

        # 1. Phase A: Match Alta Precisão
        if score >= 92:
            return best_official, score, "phase_a_high_precision"
        
        # 2. Phase B: Match Alta Cobertura
        if score >= 85:
            return best_official, score, "phase_b_high_coverage"

        # Se o termo matched está contido totalmente no input
        if len(best_norm_term) > 4 and best_norm_term in text_norm:
             return best_official, 80.0, "contains_fallback"

        return None

    def _is_valid_candidate(self, text: str) -> bool:
        """
        Filtra ruído (Blacklist) e Tokens Curtos e valida candidatos.
        """
        text = text.strip()
        if not text: return False
        
        text_upper = text.upper()
        
        # 1. Tokens muito curtos (< 3 chars)
        # Lista expandida de siglas médicas válidas
        whitelist_short = {
            "T3", "T4", "T4L", "TSH", "CK", "K", "NA", "P", "MG", "ZN", "FE", "LI", "V", "DHL", 
            "C3", "C4", "VHS", "PCR", "PSA", "CEA", "AFP", "CA", "PTH", "ACTH", "GH", "LH", "FSH",
            "EAS", "HIV", "VDRL", "HBSAG", "FAN", "IGA", "IGE", "IGG", "IGM", "CROSS"
        }
        
        # Remove caracteres não alfanuméricos para checar tamanho real
        clean_len = len(re.sub(r'[^A-Z0-9]', '', text_upper))
        
        if clean_len < 3:
            # Se for curto, SÓ passa se estiver na whitelist exata
            # Check normal e com sufixos comuns (+, -)
            if text_upper not in whitelist_short and text_upper.rstrip("+-") not in whitelist_short:
                return False

        # 2. Blacklist (Palavras de cabeçalho/rodapé/médico)
        blacklist_terms = [
             "DRA.", "DR.", "CRM", "DATA", "ASSINATURA", "PACIENTE", "CONVENIO",
             "RUA", "AV.", "TEL:", "CEP:", "BAIRRO", "CIDADE", "ESTADO",
             "SOLICITO", "PEDIDO", "REQUISICAO", "CNPJ", "CPF", "RG",
             "LABORATORIO", "CLINICA", "HOSPITAL", "UNIMED", "BRADESCON",
             "RESULTADO", "IMPRESSO", "PAGINA", "FOLHA", "OBS:", "OBSERVACAO",
             "ATENCIOSAMENTE", "GRATO", "VISTO", "REMESSA", "PROTOCOLO",
             "SENHA", "HORA", "COLETA", "IDADE", "SEXO", "NASCIMENTO"
        ]
        
        # Verifica início da linha ou palavra solta
        for term in blacklist_terms:
            if text_upper.startswith(term):
                return False
            # Verifica delimitadores comuns para evitar falsos positivos em substrings
            # Ex: "DATA" não deve dar match em "CANDIDATA" (mas startswith protege)
            # Mas "Data:" no meio da linha deve ser pego
            if f" {term}" in text_upper:
                 return False

        # 3. Formato de Data (dd/mm/aaaa) ou Hora (hh:mm)
        if re.search(r'\d{2}/\d{2}/\d{2,4}', text):
            return False
        if re.search(r'\d{2}:\d{2}', text):
            return False

        return True

    def _normalizar_texto(self, texto: str) -> str:
        """Normalização agressiva para matching: UPPER, Sem Acentos, Sem Pontuação"""
        if not texto: return ""
        texto = texto.upper()
        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto)
        texto = "".join([c for c in texto if not unicodedata.combining(c)])
        # Mantém apenas letras e números (remove traços, barras, etc)
        texto = re.sub(r'[^A-Z0-9\s]', ' ', texto) 
        # Colapsa espaços
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def _load_exams_dictionary(self) -> dict:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, "data", "exams_dictionary.json")
            if not os.path.exists(json_path):
                 return {"exames": []}
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"exames": []}

    def _flatten_dictionary(self) -> list:
        flat_list = []
        if not self.exams_dict: return []
        for item in self.exams_dict.get("exames", []):
            official = item["nome_oficial"]
            # Normaliza as chaves do dicionário também!
            flat_list.append((self._normalizar_texto(official), official))
            for syn in item.get("sinonimos", []):
                flat_list.append((self._normalizar_texto(syn), official))
            for var in item.get("variacoes", []):
                flat_list.append((self._normalizar_texto(var), official))
            for err in item.get("erros_ocr_comuns", []):
                flat_list.append((self._normalizar_texto(err), official))
        return flat_list

    def _extrair_linhas(self, api_resp: dict) -> List[str]:
        linhas = []
        # No formato REST, acessamos como dict: api_resp.get("fullTextAnnotation")
        full_text = api_resp.get("fullTextAnnotation")
        
        if not full_text:
            return []
            
        for page in full_text.get("pages", []):
            for block in page.get("blocks", []):
                for paragraph in block.get("paragraphs", []):
                    linha = ""
                    for word in paragraph.get("words", []):
                        # Symbols também é lista de dicts
                        palavra = "".join([s.get("text", "") for s in word.get("symbols", [])])
                        linha += palavra + " "
                    if linha.strip():
                        linhas.append(linha.strip())
        return linhas
