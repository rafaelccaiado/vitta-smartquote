from typing import Dict, Any, List, Tuple
from google.cloud import vision
import io
import traceback
from PIL import Image
import re
from auth_utils import get_gcp_credentials

# Novo pipeline de OCR
from services.image_preprocessor import image_preprocessor
from services.llm_ocr_corrector import llm_ocr_corrector
from services.fuzzy_matcher import fuzzy_matcher

class OCRProcessor:
    def __init__(self):
        print("Inicializando OCRProcessor com Google Cloud Vision API ☁️")
        try:
            creds = get_gcp_credentials()
            if creds:
                 print("🔑 Credenciais carregadas com sucesso via auth_utils!")
                 self.client = vision.ImageAnnotatorClient(credentials=creds)
            else:
                 print("⚠️ Credenciais retornaram None, tentando ADC padrão...")
                 self.client = vision.ImageAnnotatorClient()
                 
            print("Client Google Vision inicializado!")
            self.init_error = None
            
            # Novos componentes do pipeline
            self.use_preprocessing = True  # Flag para ativar/desativar pré-processamento
            self.use_llm_correction = True  # Flag para ativar/desativar correção LLM
            
        except Exception as e:
            print(f"Erro ao inicializar Google Vision Client: {e}")
            self.init_error = str(e)
            self.client = None

    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Processa imagem usando pipeline completo de OCR:
        1. Pré-processamento (OpenCV)
        2. Google Cloud Vision OCR
        3. Correção com LLM (Gemini)
        4. Smart parsing
        """
        if not self.client:
            # Diagnóstico detalhado para o frontend
            import os
            key_preview = "NOT_SET"
            env_val = os.getenv("GCP_SA_KEY_BASE64")
            if env_val:
                key_preview = f"{env_val[:5]}...{env_val[-5:]} (len={len(env_val)})"
            
            error_details = self.init_error if hasattr(self, 'init_error') and self.init_error else "Unknown Init Error"
            
            return {
                "error": f"CONFIG ERROR: GCP Creds Failed. Key: {key_preview}. Detail: {error_details}",
                "confidence": 0.0,
                "status": "config_error"
            }

        try:
            # === CAMADA 0: CONVERSÃO PDF -> IMAGEM ===
            # Verificação relaxada: procura assinatura PDF nos primeiros 1024 bytes
            if b'%PDF' in image_bytes[:1024]:
                print("📄 Detectado arquivo PDF. Convertendo para imagem...")
                try:
# import fitz  # PyMuPDF
#                    doc = fitz.open(stream=image_bytes, filetype="pdf")
#                    images = []
#                    
#                    print(f"📄 PDF tem {len(doc)} páginas.")
#                    
#                    for i, page in enumerate(doc):
#                        # Renderiza com zoom 2x para melhor qualidade OCR
#                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
#                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#                        images.append(img)
#                        print(f"   - Página {i+1} renderizada ({pix.width}x{pix.height})")

#                    if not images:
#                        raise ValueError("PDF vazio ou ilegível")
#
#                    # Stitch images vertically
#                    total_width = max(img.width for img in images)
#                    total_height = sum(img.height for img in images)
#                    
#                    # Limit total height to avoid Vision API limits (max 20000 pixels usually ok, but be safe)
#                    MAX_HEIGHT = 15000
#                    scale = 1.0
#                    if total_height > MAX_HEIGHT:
#                        scale = MAX_HEIGHT / total_height
#                        total_width = int(total_width * scale)
#                        total_height = MAX_HEIGHT
#                        print(f"⚠️ Imagem muito longa! Redimensionando para {total_height}px de altura.")
#                        # Resize all images
#                        images = [img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS) for img in images]
#
#                    stitched = Image.new('RGB', (total_width, total_height), (255, 255, 255))
#                    current_y = 0
#                    for img in images:
#                        stitched.paste(img, (0, current_y))
#                        current_y += img.height
#                    
#                    # Convert back to bytes
#                    img_byte_arr = io.BytesIO()
#                    stitched.save(img_byte_arr, format='JPEG', quality=95)
#                    image_bytes = img_byte_arr.getvalue()
#                    print(f"✅ Conversão PDF -> Imagem Job completa (Nova size: {len(image_bytes)} bytes)")
                    pass
                except Exception as e:
                    print(f"❌ Erro ao converter PDF: {e}")
                    return {"error": f"SERVER: PDF Conversion Failed: {str(e)}", "status": "error"}

            # === CAMADA 1: PRÉ-PROCESSAMENTO ===
            processed_image_bytes = image_bytes
            preprocessing_applied = False
            
            if self.use_preprocessing:
                try:
                    print("🔧 Aplicando pré-processamento de imagem...")
                    processed_image_bytes = image_preprocessor.preprocess(image_bytes)
                    preprocessing_applied = True
                    print("✅ Pré-processamento concluído")
                except Exception as e:
                    print(f"⚠️ Erro no pré-processamento: {e}")
                    print("Continuando com imagem original...")
                    processed_image_bytes = image_bytes

            # === CAMADA 2: GOOGLE VISION OCR ===
            image = vision.Image(content=processed_image_bytes)
            print("Enviando imagem para Google Cloud... 🚀")
            
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                error_msg = f"Erro da API Vision: {response.error.message}"
                print(error_msg)
                return {
                    "text": "", 
                    "confidence": 0.0, 
                    "error": error_msg,
                    "model_used": "Google Cloud Vision (Error)"
                }

            # Extração do texto completo
            raw_ocr_text = response.full_text_annotation.text
            print(f"📄 OCR extraiu: {len(raw_ocr_text)} caracteres")
            
            # === CAMADA 2.1: SMART PARSE (LIMPEZA INICIAL) ===
            clean_text = self._smart_parse(raw_ocr_text)
            print(f"🧹 Smart Parse limpou para {len(clean_text)} caracteres")

            # Estrutura de dados detalhada
            detailed_lines = []
            
            # Divide em linhas e aplica correções linha a linha
            raw_lines = clean_text.split('\n')
            deterministic_count = 0
            
            # === CAMADA 3.1: REGRAS DETERMINÍSTICAS (SIGLAS) ===
            for line in raw_lines:
                original_line = line
                corrected_line = self._apply_deterministic_rules(line)
                
                method = "ocr"
                confidence = 0.90 # Base confidence
                
                if corrected_line != original_line:
                    deterministic_count += 1
                    method = "deterministic_rule"
                    confidence = 1.0
                else:
                    # Tenta Fuzzy Match se a regra determinística falhou
                    fuzzy_corrected, fuzzy_conf = self._apply_fuzzy_correction(line)
                    if fuzzy_corrected != line:
                        corrected_line = fuzzy_corrected
                        method = "fuzzy_match"
                        confidence = fuzzy_conf

                if len(line) < 4 and line.isupper() and method == "ocr": # Siglas curtas mantidas
                    confidence = 0.95
                
                detailed_lines.append({
                    "original": original_line,
                    "corrected": corrected_line,
                    "confidence": confidence,
                    "method": method
                })

            # Reconstrói texto limpo para LLM (se necessário)
            current_text_lines = [item["corrected"] for item in detailed_lines]
            clean_text = "\n".join(current_text_lines)
            
            print(f"🧩 Siglas corrigidas: {deterministic_count}")

            # === CAMADA 3.2: CORREÇÃO COM LLM (SOMENTE SE NECESSÁRIO) ===
            llm_correction_data = None
            # Trigger LLM if: 
            # 1. Contains numbers (codes/results mixing)
            # 2. Contains comma (potential multi-exam line like "C3, C4")
            # 3. Contains "IgG", "IgM", "IgA" (antibody lists)
            # 4. Very short list (might be noise)
            # 4. Very short list (might be noise)
            # V70 Update: ALWAYS VALIDATE WITH LLM to ensure filtering of noise (Dr, Address, Date) works.
            # Use heuristic only if you wanted to save cost, but for accuracy we need it always.
            needs_llm = True
            
            if self.use_llm_correction and clean_text and needs_llm:
                try:
                    print("🤖 Corrigindo erros complexos com LLM...")
                    llm_result = llm_ocr_corrector.correct_ocr_text(clean_text)
                    llm_correction_data = llm_result
                    
                    if llm_result.get("corrected_terms"):
                        # V50: FULL REPLACEMENT STRATEGY
                        # Instead of trying to map 1-to-1 (which breaks on splits),
                        # we rebuild the detailed_lines entirely from the LLM output.
                        # This enables true splitting (1 line -> 3 items) and filtering (removing noise).
                        
                        new_detailed_lines = []
                        for term_data in llm_result["corrected_terms"]:
                            new_detailed_lines.append({
                                "original": term_data.get("ocr", "LLM Generated"),
                                "corrected": term_data.get("corrected", ""),
                                "confidence": term_data.get("confidence", 0.95),
                                "method": "llm_split" if "," in term_data.get("ocr", "") else "llm_correction"
                            })
                        
                        detailed_lines = new_detailed_lines
                        print(f"✅ V50: Reconstruído {len(detailed_lines)} linhas via LLM (Split/Filter Ativo)")
                except Exception as e:
                    print(f"⚠️ Erro na correção LLM: {e}")

            # === CAMADA 3.3: DICIONÁRIO CONTEXTUAL ===
            # Extrai apenas os textos para contexto
            final_terms_list = [item["corrected"] for item in detailed_lines]
            final_terms, context_stats = self._apply_context_rules(final_terms_list)
            
            # Atualiza detailed_lines com contexto (se houve mudanca)
            # A funcao _apply_context_rules retorna a lista modificada, entao comparamos indices
            for i, term in enumerate(final_terms):
                if i < len(detailed_lines):
                    if detailed_lines[i]["corrected"] != term:
                        detailed_lines[i]["corrected"] = term
                        detailed_lines[i]["method"] = "context_rule"
                        detailed_lines[i]["confidence"] = 0.98

            clean_text = "\n".join(final_terms)

            # Calcular confiança media
            avg_confidence = sum(item["confidence"] for item in detailed_lines) / len(detailed_lines) if detailed_lines else 0.0

            # Calcular estatísticas reais para a UI
            stats = {
                "auto_confirmed": deterministic_count,
                "context_corrected": context_stats.get("corrections", 0),
                "llm_applied": llm_correction_data is not None
            }

            return {
                "text": clean_text,
                "lines": detailed_lines, # NOVO: Retorna estrutura detalhada
                "confidence": round(avg_confidence, 2),
                "stats": stats,
                "backend_version": "V70.1-StrictFilter",
                "model_used": "Google Cloud Vision API (Enhanced Pipeline)",
                "pipeline_info": {
                    "preprocessing_applied": preprocessing_applied,
                    "llm_correction_applied": llm_correction_data is not None,
                    "raw_ocr_text": raw_ocr_text,
                    "llm_corrections": llm_correction_data
                },
                "debug_raw": [{
                    "model": "google-vision-enhanced", 
                    "text_preview": clean_text[:100]
                }]
            }

        except Exception as e:
            print(f"Exceção no processamento OCR: {e}")
            traceback.print_exc()
            return {
                "text": "",
                "confidence": 0.0, 
                "error": f"CRITICAL SERVER ERROR: {str(e)}",
                "backend_version": "V70.1-VercelFix",
                "model_used": "Error Handler"
            }

    def _smart_parse(self, text: str) -> str:
        """Filtra cabeçalhos, rodapés e ruídos comuns de receitas médicas"""
        lines = text.split('\n')
        
        # Padrões para remover (Blacklist)
        patterns = [
            r"cpf[:\s].*", r"cnpj[:\s].*", r"rg[:\s].*", r"tel[:\s].*",
            r"rua\s.*", r"av\.?\s.*", r"avenida\s.*", r"alameda\s.*", r"bairro\s.*",
            r"cep[:\s].*", r"crm[:\s].*", r"crm-?go.*", r"crv[:\s].*", r"crv-?go.*", r"dra?\.?\s.*", 
            r"paciente[:\s].*", r"convênio[:\s].*", r"unimed.*", r"data[:\s].*",
            r"ass\..*", r"assinatura.*", r"carimbo.*", r"receitu[áa]rio.*", r"médic[oa].*",
            r"goi[âa]nia.*", r"aparecida.*", r"bras[íi]lia.*", # Cidades comuns
            r"^cid.*", r"cid[:\-\s].*", r"cid-?10.*", r"h\.?d\.?.*", r"hds[:\s].*", # Diagnósticos (CID START)
            r"hosp.*", r"denmar.*", r"instituto.*", r"laborat[óo]rio.*", # Logos
            r"^\d{2}/\d{2}/\d{2,4}.*", r"página\s\d.*", r"folha\s\d.*",
            r"^id[:\s]\d+", r"^unidade:.*", r"^exames$", r"^solicito$", 
            r"^pedido de exame$", r"^indicação clínica.*", r"^código.*", 
            r"^documento gerado.*", r"^assinado digitalmente.*", r"^amorsaúde.*",
            r"^impresso em.*", r"^data da impressão.*", r"^usuário.*",
            r"ricardo eletro.*", r"gastroenter.*", r"^\s*we\.\s*$", r"^\s*dar é\s*$", 
            r"^especialidade:.*", r"^unidade:.*", r"^médico:.*", r"^paciente:.*",
            r"taguatinga.*", r"valparaiso.*", r"ocidental.*", r"gleba.*", r"lote\s?\d+.*", 
            r"quadra\s?\d+.*", r"etapa\s?.*", r"br-040.*", r"trecho.*",
            r"^\d{5,}.*", r"^[\d\.\-\/\s]+$", r"^[a-zA-Z]{1,2}$",
            r"^sust.*", r"^sus$" # Noise specific
        ]
        
        regexes = [re.compile(p, re.IGNORECASE) for p in patterns]
        start_anchors = ["solicito", "prescrição", "prescrevo", "exames abaixo"]
        
        # Verifica se TEM alguma âncora no texto inteiro
        global_has_anchor = any(a in text.lower() for a in start_anchors)
        
        extracted = []
        found_anchor = False
        
        latest_context = None # V57: Track parent exam context
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # --- FASE 0: Context Reconnection (V58 Improved) ---
            # Broaden orphan check: matches "IgM", "- IgM", "IgM.", "IgM "
            # Must strictly match the Ig pattern with optional non-word chars around
            is_orphan = re.search(r'^\W*(Ig[GAM]|IG[GAM])\W*$', line, re.IGNORECASE)
            
            if is_orphan and latest_context:
                # Extract the actual Ig part
                ig_part = is_orphan.group(0).strip(" -.,")
                print(f"🔗 Reconnecting Orphan: '{line}' -> '{latest_context} {ig_part}'")
                line = f"{latest_context} {ig_part}"
            
            # Update Context if this line is a valid "Parent"
            # Must start with medical term AND be long enough
            line_upper = line.upper()
            # V59: Added COMPLEMENTO to context triggers (For "Complemento C3, C4")
            if line_upper.startswith(("ANTI", "FAN", "SOROLOGIA", "PESQUISA", "DOSAGEM", "DOSAGENS", "IMUNO", "COMPLEMENTO")):
                 # Remove the specific Ig from the context so we get a clean base
                 # Ex: "Dosagens.. IgA" -> "Dosagens.."
                 clean_context = re.sub(r'\b(Ig[GAM]|IG[GAM])\b', '', line, flags=re.IGNORECASE).strip()
                 # Remove trailing punctuation like " e", ","
                 clean_context = re.sub(r'[\s,e.-]+$', '', clean_context, flags=re.IGNORECASE)
                 if len(clean_context) > 5:
                     latest_context = clean_context
            
            # --- FASE 1: Detecção de Âncora ---
            line_lower = line.lower()
            is_anchor_line = False
            for anchor in start_anchors:
                if anchor in line_lower:
                    is_anchor_line = True
                    found_anchor = True
                    # Remove a palavra âncora da linha, mas mantém o resto (ex: "Solicito: Hemograma")
                    line = re.sub(anchor, "", line, flags=re.IGNORECASE).strip(" :")
                    break
            
            # Se tem âncora no texto global, DESCARTA tudo antes dela
            if global_has_anchor and not found_anchor:
                continue

            if not line: continue

            # --- FASE 2: Filtros Universais (Blacklist) ---
            if any(r.search(line) for r in regexes): continue
            
            # V52: Allow short lines if they are known exam parts (C3, C4, T3, T4, CK, Pta)
            # Normal < 3 rule kills "C4".
            # V57 Fix: Use strip() to ensure " C4 " matches "C4"
            is_valid_short = line.strip().upper() in ["C3", "C4", "T3", "T4", "CK", "PTA", "K+", "NA+", "CA", "P", "MG", "FE", "LI", "ZN", "CU"]
            if len(line) < 3 and not is_valid_short: continue
            
            # --- FASE 3: Heurística de Nomes (Assinaturas/Médicos) ---
            # Remove linhas que parecem nomes de pessoas (ex: "Aniele N. de Siqueira")
            
            # V54 SAFEGUARD: Don't treat exams starting with these as names
            line_upper = line.upper()
            # V55: Added DOSAGENS (Plural), IMUNO, ANTICORPO
            is_medical_term = line_upper.startswith(("ANTI", "FAN", "SOROLOGIA", "PESQUISA", "DOSAGEM", "DOSAGENS", "VDRL", "HIV", "HTLV", "IG", "HEMO", "CULTURA", "ELETRO", "IMUNO", "ANTICORPO"))
            
            words = line.split()
            if not is_medical_term and len(words) > 1 and not any(char.isdigit() for char in line):
                 capitalized_count = sum(1 for w in words if w[0].isupper())
                 connectors = ['de', 'da', 'do', 'dos', 'das', 'e']
                 has_connector = any(w.lower() in connectors for w in words)
                 
                 # Se > 70% das palavras são Capitalized, é provavelmente um nome/assinatura
                 # OU se tem conectores de nome e pelo menos uma maiúscula
                 is_name_structure = (capitalized_count / len(words) > 0.6) or (has_connector and capitalized_count >= 1)
                 
                 if is_name_structure:
                     print(f"👻 Linha removida por parecer nome: {line}")
                     continue

            # --- FASE 4: Limpeza Fina (Bullets e Enumeração) ---
            # Remove hífens, bolinhas, números de lista (1., 2.) do início da linha
            # Ex: "- Hemograma" -> "Hemograma", "1. Glicose" -> "Glicose"
            line = re.sub(r'^[\s\-\*\•\>]+', '', line) # Bullets simples
            line = re.sub(r'^\s*\d+[\.\)\-]\s*', '', line) # Enumeração (1. 1) 01-)
            
            line = line.strip()
            if not line: continue

            # --- FASE 5: Detecção de Exames Combinados (Split) ---
            # Separa linhas como "TGO/TGP", "Ureia / Creatinina", "Hemograma + Glicose"
            # Separadores comuns: /  \  +  e  - (com cuidado para não quebrar hífens de nomes)
            
            # Padroniza separadores para um token único <SPLIT>
            # 1. Barra (/) ou Backslash (\)
            line_processed = re.sub(r'\s*[\/\\]\s*', '<SPLIT>', line)
            # 2. Mais (+)
            line_processed = re.sub(r'\s*\+\s*', '<SPLIT>', line_processed)
            # 3. " e " (isolado)
            line_processed = re.sub(r'\s+e\s+', '<SPLIT>', line_processed, flags=re.IGNORECASE)
            # 4. Vígula (,) - V51 Fix
            line_processed = re.sub(r'\s*,\s*', '<SPLIT>', line_processed)
            
            if '<SPLIT>' in line_processed:
                parts = line_processed.split('<SPLIT>')
                
                # V60: Intelligent Context Propagation in Splitter
                # Determine context from the first part (Local) or use Global `latest_context`
                first_part = parts[0].strip()
                first_part_upper = first_part.upper()
                
                local_context = None
                parent_triggers = ("ANTI", "FAN", "SOROLOGIA", "PESQUISA", "DOSAGEM", "DOSAGENS", "IMUNO", "COMPLEMENTO")
                
                # Check if first part defines a new context (e.g., "Complemento C3...")
                if first_part_upper.startswith(parent_triggers):
                    clean = re.sub(r'\b(Ig[GAM]|IG[GAM])\b', '', first_part, flags=re.IGNORECASE).strip()
                    clean = re.sub(r'[\s,e.-]+$', '', clean, flags=re.IGNORECASE)
                    clean = re.sub(r'\b[A-Z0-9]{1,3}\b$', '', clean).strip() # Remove short trailing codes like "C3"
                    if len(clean) > 3:
                        local_context = clean
                
                # Decide which context to use for siblings
                active_context = local_context if local_context else latest_context
                
                for i, part in enumerate(parts):
                    part = part.strip()
                    if not part: continue
                    
                    # V59 Clean whitelist check
                    is_valid_short = part.strip().upper() in ["C3", "C4", "T3", "T4", "CK", "PTA", "K+", "NA+", "CA", "P", "MG", "FE", "LI", "ZN", "CU", "LDH"]
                    
                    # Logic: 
                    # If i==0: It works as is context is normally embedded. 
                    # If i>0 (Siblings): We MUST prepend context if it's missing.
                    
                    final_part = part
                    if i > 0 and active_context:
                        # Don't double paste if somehow already present (rare in split parts)
                        if not part.upper().startswith(active_context.upper()[:5]): 
                            final_part = f"{active_context} {part}"
                    
                    # Also handle the edge case where Part 0 needs global context (e.g. Line 1: Header, Line 2: "C3, C4")
                    if i == 0 and not local_context and latest_context:
                         if not part.upper().startswith(latest_context.upper()[:5]):
                             final_part = f"{latest_context} {part}"

                    if len(part) > 2 or is_valid_short: 
                        final_part = self._clean_suffix_noise(final_part)
                        if final_part:
                            extracted.append(final_part)
                        
                print(f"✂️ Linha dividida context: '{line}' -> {[active_context] + parts}")
                continue # Já adicionou as partes

            line = self._clean_suffix_noise(line)
            if not line: continue
            extracted.append(line)
                
        # V55: Python-side Antibody Expansion (Force Split)
        # Post-process extracted lines to split merged antibodies (IgG IgM)
        final_extracted = []
        for item in extracted:
            expanded = self._expand_antibody_line(item)
            final_extracted.extend(expanded)
        
        return "\n".join(final_extracted)

    def _expand_antibody_line(self, text: str) -> List[str]:
        """
        V55: Deterministically splits lines with multiple antibodies.
        Ex: "Dengue IgG IgM" -> ["Dengue IgG", "Dengue IgM"]
        """
        # Encontra todas as ocorrências de IgA, IgG, IgM
        igs = re.findall(r'\b(Ig[GAM]|IG[GAM])\b', text, re.IGNORECASE)
        
        # Se tiver mais de uma imunoglobulina DIFERENTE na mesma linha
        if len(set(x.upper() for x in igs)) >= 2:
            base_text = re.sub(r'\b(Ig[GAM]|IG[GAM])\b', '', text, flags=re.IGNORECASE).strip()
            # Remove conectores soltos no final (ex: "Dengue e")
            base_text = re.sub(r'\s+e\s*$', '', base_text, flags=re.IGNORECASE)
            
            expanded = []
            for ig in igs:
                # Reconstrói: "Nome Base + IgG"
                expanded.append(f"{base_text} {ig.upper()}")
            print(f"🧬 Antibody Split: '{text}' -> {expanded}")
            return expanded
            
        return [text]

    def _clean_suffix_noise(self, text: str) -> str:
        """
        Removes known clinic locations or address fragments from the end of a line.
        Ex: "ANTI GLIADINA Valparaiso" -> "ANTI GLIADINA"
        """
        # Patterns that are usually suffixes in clinic addresses
        noise_suffixes = [
            r"taguatinga.*", r"valparaiso.*", r"ocidental.*", r"gleba.*", 
            r"lote\s?\d+.*", r"quadra\s?\d+.*", r"etapa\s?.*", r"br-040.*", r"trecho.*",
            r"unidade.*", r"goi[âa]nia.*", r"aparecida.*", r"bras[íi]lia.*",
            r"exames\slaboratoriais.*", r"gastroenter.*"
        ]
        
        cleaned = text
        for noise in noise_suffixes:
            # Match the noise pattern preceded by a space, hyphen or slash
            cleaned = re.sub(r'[\s\-\/\•\·]+\b' + noise, '', cleaned, flags=re.IGNORECASE).strip()
            
        return cleaned

    def _apply_deterministic_rules(self, text: str) -> str:
        """Aplica regras fixas para siglas médicas comuns que o OCR costuma errar"""
        rules = [
            (r'(?i)[4T][S5][H47]', 'TSH'),
            (r'(?i)[F|P][S5][H4]', 'FSH'),
            (r'(?i)T4\s?Li[o|v]re', 'T4 Livre'),
            (r'(?i)H[o|e|a]m[o|a|e]?gr[o|a]ma', 'Hemograma'), # Homgrama (missing vowel)
            (r'(?i)L[i|1]p[i|1]d[o|a][\-\s]?gr[a|o]ma', 'Lipidograma'), # Lipido-gama
            (r'(?i)G[l|1][i|1]c[e|i]m[i|e]a', 'Glicemia'),
            (r'(?i)Ur+e+i+a+', 'Ureia'),
            (r'(?i)Jr[e|a]l[a|o]', 'Ureia'), 
            (r'(?i)Cr[e|i]at[i|e]n[i|e]na', 'Creatinina'),
            (r'(?i)T[G|6]O', 'TGO'),
            (r'(?i)T[G|6]P', 'TGP'),
            (r'^\s*4\s*754\s*$', 'TSH'),
        ]
        
        for pattern, replacement in rules:
            if re.search(pattern, text):
                return replacement
        return text

    def _apply_fuzzy_correction(self, text: str) -> Tuple[str, float]:
        """
        Aplica correção fuzzy agressiva baseada na lista de exames comuns.
        Retorna (texto_corrigido, confiança)
        """
        COMMON_EXAMS = [
            "HEMOGRAMA", "LIPIDOGRAMA", "COLESTEROL", "TSH", "FSH", 
            "T4 LIVRE", "T3", "GLICEMIA", "UREIA", "CREATININA",
            "TGO", "TGP", "EAS", "PARASITOLOGICO"
        ]
        
        from rapidfuzz import fuzz
        
        best_match = None
        best_score = 0
        
        text_upper = text.upper()
        
        for exam in COMMON_EXAMS:
            # Ratio simples costuma ser melhor para erros de OCR (substituição/falta de chars)
            score = fuzz.ratio(text_upper, exam)
            
            if score > best_score:
                best_score = score
                best_match = exam
        
        # Threshold de 60% conforme solicitado
        if best_score >= 60:
            # Se for muito alto (>90), confiança alta, senão média
            confidence = 0.95 if best_score > 90 else 0.80
            return best_match, confidence
            
        return text, 0.0

    def _apply_context_rules(self, terms: List[str]) -> Tuple[List[str], Dict[str, Any]]:
        """Aplica lógica de contexto: se tiver X, prioriza Y no mesmo grupo"""
        context_groups = {
            'tireoide': ['TSH', 'T4 Livre', 'T3', 'T4', 'Anticorpo Anti-TPO'],
            'lipidico': ['Colesterol Total', 'HDL', 'LDL', 'VLDL', 'Triglicerídeos', 'Lipidograma'],
            'glicemia': ['Glicemia de Jejum', 'Hemoglobina Glicada', 'Insulina']
        }
        
        detected_contexts = set()
        stats = {"corrections": 0}
        
        for term in terms:
            term_upper = term.upper()
            if any(k in term_upper for k in ['TSH', 'T4', 'T3']): detected_contexts.add('tireoide')
            if any(k in term_upper for k in ['COLESTEROL', 'LIPID', 'TRIGLI']): detected_contexts.add('lipidico')
            if any(k in term_upper for k in ['GLICEMA', 'GLICADA']): detected_contexts.add('glicemia')
        
        # Otimização: se o contexto for detectado, podemos expandir termos curtos
        # ou ambíguos baseados no grupo. Por enquanto, apenas logamos.
        if detected_contexts:
            print(f"🧠 Contextos médicos detectados: {detected_contexts}")
            
        return terms, stats
