import re
from typing import List, Dict, Any

class OCRResoluteAuditor:
    """
    Vitta Resolute OCR Auditor: Verifies extraction completeness and filters noise.
    Goal: 100% Extraction Fidelity & No Noise Leakage.
    """
    
    def __init__(self):
        # Medical Prefixes that indicate a high probability of an exam
        self.medical_prefixes = [
            "ANTI", "TSH", "T4", "HEMO", "GLICO", "URIA", "CREAT", "LIPID", 
            "PROTEINA", "VHS", "PCR", "DOSAGEM", "PESQUISA", "SOROLOGIA",
            "FAN", "PSA", "CEA", "AFP", "ACTH", "FSH", "LH", "T3"
        ]
        
        # Heavy Blacklist for Noise (Dr, Address, Metadata)
        self.noise_blacklist = [
            r"DR\.", r"DRA\.", r"CRM", r"RUA", r"AV\.", r"CEP:", r"TEL:",
            r"LOTE", r"QUADRA", r"SETOR", r"BAIRRO", r"CIDADE", r"ASSINATURA",
            r"CARIMBO", r"PACIENTE:", r"CONVENIO:", r"DATA:", r"PAGINA"
        ]

    def audit(self, raw_lines: List[str], extracted_exams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audits the OCR result against the raw data.
        """
        extracted_originals = [e["original"].upper() for e in extracted_exams]
        
        missed_candidates = []
        noise_leaked = []
        
        # 1. Detect Missed Exams
        for line in raw_lines:
            line_upper = line.upper()
            
            # If line is NOT in extracted but looks like an exam
            if not any(orig in line_upper for orig in extracted_originals):
                if self._is_likely_exam(line_upper):
                    missed_candidates.append(line)
        
        # 2. Check for Noise Leakage in Extracted
        for exam in extracted_exams:
            term = exam["corrected"].upper()
            if self._is_noise(term):
                noise_leaked.append(exam["corrected"])
                
        # 3. Calculate Scores
        total_extracted = len(extracted_exams)
        noise_count = len(noise_leaked)
        valid_identified = total_extracted - noise_count
        possible_missed = len(missed_candidates)
        
        # Coverage: Ratio of identified valid items vs (identified + missed)
        coverage = valid_identified / max(1, (valid_identified + possible_missed))
        
        # Accuracy: Average confidence penalized by noise leakage percentage
        avg_confidence = sum(e.get("confidence", 0) for e in extracted_exams) / max(1, total_extracted)
        noise_penalty = (noise_count / max(1, total_extracted))
        accuracy_score = avg_confidence * (1 - noise_penalty)

        return {
            "audit_status": "PASS" if not missed_candidates and not noise_leaked else "WARNING",
            "accuracy_score": round(accuracy_score, 2),
            "coverage_score": round(coverage, 2),
            "missed_candidates": missed_candidates,
            "noise_leaked": noise_leaked,
            "recommendations": self._get_recommendations(missed_candidates, noise_leaked)
        }

    def _is_likely_exam(self, text: str) -> bool:
        # Whitelist for short valid tokens
        whitelist_short = ["TSH", "T3", "T4", "CK", "K+", "NA+", "FE", "VHS", "PCR", "PSA"]
        
        # 1. Check exact short whitelist
        if text.strip() in whitelist_short:
             return True

        # 2. Check if line starts with or contains strong medical prefixes
        for prefix in self.medical_prefixes:
            if prefix in text:
                # Basic check to avoid small noise (like "TEL: ...")
                if len(text) >= 3 and not self._is_noise(text):
                    return True
        return False

    def _is_noise(self, text: str) -> bool:
        for pattern in self.noise_blacklist:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _get_recommendations(self, missed: list, noise: list) -> List[str]:
        recs = []
        if missed:
            recs.append(f"Verificar se os termos {missed[:2]} são exames válidos.")
        if noise:
            recs.append(f"Remover termos de ruído detectados: {noise[:2]}.")
        if not recs:
            recs.append("Extração perfeita detectada. Nenhuma ação necessária.")
        return recs

ocr_resolute_auditor = OCRResoluteAuditor()
