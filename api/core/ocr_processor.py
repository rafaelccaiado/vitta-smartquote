from typing import Dict, Any, List, Tuple, Optional
import requests
from google.auth.transport.requests import Request
import io
import traceback
from PIL import Image
import re
from core.auth_utils import get_gcp_credentials
import json
import unicodedata
import os

# New OCR Pipeline V87.0
from services.image_preprocessor import ImagePreprocessor
from services.llm_interpreter import LLMInterpreter
from services.ocr_resolute_auditor import OCRResoluteAuditor

class OCRProcessor:
    def __init__(self):
        print("Initializing OCRProcessor with Google Cloud Vision API V87.0...")
        try:
            self.creds = get_gcp_credentials()
            if self.creds and self.creds.requires_scopes:
                self.creds = self.creds.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])
            
            if self.creds:
                print("✅ Credentials loaded and scoped (Cloud Platform)!")
            else:
                print("❌ Credentials returned None. GCP will fail.")
                
            print("OCR Processor (REST Mode) initialized!")
            self.init_error = None
            
            # Components
            self.use_preprocessing = True
            
            # Load Dictionary
            self.exams_dict = self._load_exams_dictionary()
            
            # Flat list for matching
            self.exams_flat_list = self._flatten_dictionary()
            self.exact_set = {self._normalizar_texto(name) for name, _ in self.exams_flat_list}
            
            print(f"✅ Medical Dictionary Loaded: {len(self.exams_flat_list)} terms indexed.")
            
        except Exception as e:
            print(f"Error initializing Google Vision Client: {e}")
            self.init_error = str(e)

    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Processa a imagem com Pipeline 3-Phase Matching & Alta Cobertura.
        """
        if not self.creds:
            return {"error": f"CONFIG ERROR: GCP Credentials Missing. {self.init_error}", "status": "config_error"}

        try:
            # Phase 1: ROI Detection & Pre-processing
            processed_image_bytes = image_bytes
            
            if self.use_preprocessing:
                try:
                    # Attempt to enhance contrast and remove shadows
                    from services.image_preprocessor import image_preprocessor
                    processed_image_bytes = image_preprocessor.preprocess(image_bytes)
                except Exception as e:
                    print(f"⚠️ Preprocessing failed, using original: {e}")

            # Phase 2: Google Vision OCR (via REST API)
            import base64
            b64_image = base64.b64encode(processed_image_bytes).decode("utf-8")
            
            # Refresh token if needed
            try:
                if not self.creds.valid:
                    auth_req = Request()
                    self.creds.refresh(auth_req)
                token = self.creds.token
            except Exception as e:
                return {"error": f"AUTH ERROR: Failed to refresh token. {e}", "status": "auth_error"}

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
            api_resp = response_json.get("responses", [{}])[0]

            if "error" in api_resp:
                return {"error": api_resp["error"].get("message"), "status": "error"}

            # Extraction
            raw_lines = self._extrair_linhas(api_resp)

            # Phase 3: Filtering & Classification (CANDIDATES)
            candidates = []
            
            # Thresholds
            THRESH_PHASE_A = 92
            THRESH_PHASE_B = 85

            stats = {
                "total_ocr_lines": len(raw_lines),
                "candidates_count": 0,
                "matched_count": 0,
                "unverified_count": 0,
                "fuzzy_used": False,
                "thresholds": {"phase_a": THRESH_PHASE_A, "phase_b": THRESH_PHASE_B, "short_token": 95}
            }

            for line in raw_lines:
                if self._is_valid_candidate(line):
                    candidates.append(line)

            stats["candidates_count"] = len(candidates)

            # Phase 4: 2-Phase Matching
            matched_exams = []

            for can in candidates:
                match_result = self._match_term(can)

                if match_result:
                    corrected, score, method = match_result
                    
                    if "fuzzy" in method:
                        stats["fuzzy_used"] = True

                    matched_exams.append({
                        "original": can,
                        "corrected": corrected,
                        "confidence": score / 100.0,
                        "method": method
                    })

            # Dedup
            unique_matches = {}
            for m in matched_exams:
                key = m["corrected"]
                if key not in unique_matches or m["confidence"] > unique_matches[key]["confidence"]:
                    unique_matches[key] = m
            matched_exams = list(unique_matches.values())
            
            stats["matched_count"] = len(matched_exams)

            # Phase 5: Fallback Intelligence
            fallback_used = False
            
            if not matched_exams and candidates:
                fallback_used = True
                for can in candidates[:10]:
                    matched_exams.append({
                        "original": can,
                        "corrected": f"{can} [⚠️ Não Verificado]",
                        "confidence": 0.1,
                        "method": "fallback_raw"
                    })
            
            # Metrics
            verified_count = sum(1 for x in matched_exams if "fallback" not in x["method"])
            unverified_count = len(matched_exams) - verified_count
            total_returned = len(matched_exams)
            
            stats["unverified_count"] = unverified_count
            
            metrics = {
                "coverage": (len(raw_lines) > 0 and total_returned > 0),
                "verified_ratio": round(verified_count / max(1, total_returned), 2),
                "fallback_rate_flag": (unverified_count > 0)
            }

            audit_result = {}
            try:
                from services.ocr_resolute_auditor import ocr_resolute_auditor
                audit_result = ocr_resolute_auditor.audit(raw_lines, matched_exams)
            except Exception as e:
                print(f"⚠️ Resolute Audit fail: {e}")

            clean_text = "\n".join([x["corrected"] for x in matched_exams])
            avg_conf = sum(x["confidence"] for x in matched_exams) / len(matched_exams) if matched_exams else 0.0

            return {
                "text": clean_text,
                "lines": matched_exams,
                "confidence": round(avg_conf, 2),
                "stats": {
                    "total_ocr_lines": len(raw_lines),
                    "classified_exams": len(candidates),
                    "valid_matches": len(matched_exams)
                },
                "backend_version": "V87.0-Split-Fixed",
                "mode_used": "Vision -> 2-Phase Matcher -> QA Metrics",
                "debug_raw": candidates,
                "debug_meta": {
                    "raw_ocr_lines_count": len(raw_lines),
                    "candidates_count": len(candidates),
                    "matched_count": verified_count,
                    "unverified_count": unverified_count,
                    "total_returned": total_returned,
                    "fuzzy_used": stats["fuzzy_used"],
                    "thresholds": stats["thresholds"],
                    "dictionary_loaded": bool(self.exams_flat_list),
                    "dictionary_size": len(self.exams_flat_list),
                    "fallback_used": fallback_used,
                    "raw_metrics": metrics,
                    "resolute_audit": audit_result
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
        text_norm = self._normalizar_texto(text)
        if not text_norm: return None

        # Phase A: Exact Match
        best_ratio = 0.0
        best_official = None
        best_norm_term = ""

        for norm_term, official_name in self.exams_flat_list:
            if text_norm == norm_term:
                return official_name, 100.0, "exact_match"
        
        from difflib import SequenceMatcher
        
        for norm_term, official_name in self.exams_flat_list:
            sm = SequenceMatcher(None, text_norm, norm_term)
            ratio = sm.ratio() * 100.0
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_official = official_name
                best_norm_term = norm_term

        score = best_ratio
        
        if not best_official:
            return None
            
        # Calibration Rules
        if len(text_norm) <= 4:
            if score >= 95:
                return best_official, score, "short_token_high_precision"
            return None

        if score >= 92:
            return best_official, score, "phase_a_high_precision"
        
        if score >= 85:
            return best_official, score, "phase_b_high_coverage"

        if len(best_norm_term) > 4 and best_norm_term in text_norm:
            return best_official, 80.0, "contains_fallback"

        return None

    def _is_valid_candidate(self, text: str) -> bool:
        text = text.strip()
        if not text: return False
        
        text_upper = text.upper()
        
        whitelist_short = {
            "T3", "T4", "TSH", "CK", "K", "NA", "P", "MG", "CL", "FE", "LI", "CR", "DHL",
            "C3", "C4", "VHS", "PCR", "PSA", "CEA", "AFP", "CA", "PTH", "ACTH", "GH", "LH", "FSH",
            "EAS", "HIV", "VDRL", "HBSAG", "FAN", "IGA", "IGE", "IGG", "IGM", "ROSS"
        }
        
        clean_len = len(re.sub(r'[^A-Z0-9]', '', text_upper))
        
        if clean_len < 3:
            if text_upper not in whitelist_short and text_upper.rstrip("+-") not in whitelist_short:
                return False

        blacklist_terms = [
            "DRA.", "DR.", "CRM", "DATA", "ASSINATURA", "PACIENTE", "CONVENIO",
            "RUA", "AV.", "TEL:", "CEP:", "BAIRRO", "CIDADE", "ESTADO",
            "SOLICITO", "PEDIDO", "REQUISICAO", "CNPJ", "CPF", "RG",
            "LABORATORIO", "CLINICA", "HOSPITAL", "UNIMED", "BRADESCO",
            "RESULTADO", "IMPRESSAO", "PAGINA", "FOLHA", "OBS:", "OBSERVACAO",
            "ATENCIOSAMENTE", "GRATO", "VISTO", "REMESSA", "PROTOCOLO",
            "SENHA", "HORA", "COLETA", "IDADE", "SERV.", "NASCIMENTO"
        ]
        
        for term in blacklist_terms:
            if text_upper.startswith(term):
                return False
            if f" {term} " in text_upper:
                return False
        
        if re.search(r'\d{2}/\d{2}/\d{2,4}', text):
            return False
        if re.search(r'\d{2}:\d{2}', text):
            return False

        return True

    def _normalizar_texto(self, texto: str) -> str:
        if not texto: return ""
        texto = texto.upper()
        
        noise = [
            "EXAMES LABORATORIAIS", 
            "EXAME LABORATORIAL",
            "SOLICITACAO DE EXAMES",
            " E EXAMES",
            "LABORATORIAIS",
            "LABORATORIAL"
        ]
        for n in noise:
            texto = texto.replace(n, "")

        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto)
        texto = "".join([c for c in texto if not unicodedata.combining(c)])
        
        # Vitamin D special
        texto = texto.replace("2,5", "25").replace("2.5", "25")

        # Keep only letters and numbers
        texto = re.sub(r'[^A-Z0-9\s]', ' ', texto)
        
        # Collapse whitespace
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def _load_exams_dictionary(self) -> Dict:
        try:
            core_dir = os.path.dirname(os.path.abspath(__file__))
            api_dir = os.path.dirname(core_dir)
            json_path = os.path.join(api_dir, "data", "exams_dictionary.json")
            if not os.path.exists(json_path):
                return {"exames": []}
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"exames": []}

    def _flatten_dictionary(self) -> List:
        flat_list = []
        if not self.exams_dict: return []
        for item in self.exams_dict.get("exames", []):
            official = item["nome_oficial"]
            flat_list.append((self._normalizar_texto(official), official))
            for syn in item.get("sinonimos", []):
                flat_list.append((self._normalizar_texto(syn), official))
            for var in item.get("variacoes", []):
                flat_list.append((self._normalizar_texto(var), official))
            for err in item.get("erros_ocr_comuns", []):
                flat_list.append((self._normalizar_texto(err), official))
        return flat_list

    def _extrair_linhas(self, api_resp: Dict) -> List[str]:
        linhas = []
        full_text = api_resp.get("fullTextAnnotation")
        
        if not full_text:
            return []
            
        for page in full_text.get("pages", []):
            for block in page.get("blocks", []):
                for paragraph in block.get("paragraphs", []):
                    linha = ""
                    for word in paragraph.get("words", []):
                        palavra = "".join([s.get("text", "") for s in word.get("symbols", [])])
                        linha += palavra + " "
                    if linha.strip():
                        linhas.append(linha.strip())
        return linhas
