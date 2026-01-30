import json
import os
from datetime import datetime
from typing import Dict, Any

class MissingTermsLogger:
    """
    Logger para rastrear termos não encontrados e sugerir melhorias.
    Gera relatórios para curadoria de sinônimos e exames faltantes.
    """
    
    def __init__(self, log_dir: str = None):
        if log_dir is None:
            # Vercel bypass: Only /tmp is writable
            if os.getenv("VERCEL") or os.getenv("ENVIRONMENT") == "production":
                log_dir = "/tmp"
            else:
                log_dir = "logs"
        
        self.log_dir = log_dir
        
        # Só cria diretório se não for /tmp (Vercel já tem /tmp)
        if log_dir != "/tmp":
            os.makedirs(log_dir, exist_ok=True)
        
        self.not_found_file = os.path.join(log_dir, "exames_nao_encontrados.json")
        self.fuzzy_matches_file = os.path.join(log_dir, "sugestoes_sinonimos.json")
        
        # Carrega logs existentes
        self.not_found_terms = self._load_json(self.not_found_file)
        self.fuzzy_matches = self._load_json(self.fuzzy_matches_file)
    
    def _load_json(self, filepath: str) -> Dict:
        """Carrega arquivo JSON ou retorna dict vazio"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_json(self, filepath: str, data: Dict):
        """Salva dados em JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def log_not_found(self, term: str, unit: str, user_context: str = None):
        """
        Registra termo que não foi encontrado de forma alguma.
        
        Args:
            term: Termo original digitado
            unit: Unidade onde foi buscado
            user_context: Contexto adicional (ex: nome do médico, especialidade)
        """
        key = term.lower().strip()
        
        if key not in self.not_found_terms:
            self.not_found_terms[key] = {
                "original_term": term,
                "occurrences": [],
                "status": "pending",  # pending, added, ignored
                "notes": ""
            }
        
        # Adiciona ocorrência
        self.not_found_terms[key]["occurrences"].append({
            "timestamp": datetime.now().isoformat(),
            "unit": unit,
            "context": user_context
        })
        
        self._save_json(self.not_found_file, self.not_found_terms)
    
    def log_fuzzy_match(self, term: str, matched_exam: str, strategy: str, unit: str):
        """
        Registra termo que só foi encontrado via fuzzy/substring.
        Sugere criação de sinônimo.
        
        Args:
            term: Termo original digitado
            matched_exam: Exame que foi matched
            strategy: Estratégia usada (fuzzy, substring, etc)
            unit: Unidade
        """
        key = f"{term.lower().strip()} -> {matched_exam.lower().strip()}"
        
        if key not in self.fuzzy_matches:
            self.fuzzy_matches[key] = {
                "input_term": term,
                "matched_exam": matched_exam,
                "strategy": strategy,
                "occurrences": [],
                "status": "pending",  # pending, added, ignored
                "suggested_action": f"Adicionar sinônimo: '{term}' -> '{matched_exam}'"
            }
        
        # Adiciona ocorrência
        self.fuzzy_matches[key]["occurrences"].append({
            "timestamp": datetime.now().isoformat(),
            "unit": unit
        })
        
        self._save_json(self.fuzzy_matches_file, self.fuzzy_matches)
    
    def generate_report(self) -> str:
        """Gera relatório em markdown para revisão"""
        report = []
        report.append("# Relatório de Curadoria - Vittá SmartQuote\n")
        report.append(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        report.append("---\n")
        
        # Seção 1: Exames Não Encontrados
        report.append("## 🔴 Exames Não Encontrados (Adicionar na Tabela de Preços)\n")
        
        pending_not_found = {k: v for k, v in self.not_found_terms.items() 
                            if v["status"] == "pending"}
        
        if pending_not_found:
            report.append(f"**Total:** {len(pending_not_found)} termos\n")
            
            # Ordena por frequência
            sorted_terms = sorted(pending_not_found.items(), 
                                 key=lambda x: len(x[1]["occurrences"]), 
                                 reverse=True)
            
            for term_key, data in sorted_terms:
                count = len(data["occurrences"])
                units = set(occ["unit"] for occ in data["occurrences"])
                
                report.append(f"\n### `{data['original_term']}`")
                report.append(f"- **Frequência:** {count}x")
                report.append(f"- **Unidades:** {', '.join(units)}")
                report.append(f"- **Ação:** Verificar se exame existe e adicionar na tabela de preços")
        else:
            report.append("*Nenhum termo pendente.*\n")
        
        # Seção 2: Sugestões de Sinônimos
        report.append("\n---\n")
        report.append("## 🟡 Sugestões de Sinônimos (Melhorar Matching)\n")
        
        pending_synonyms = {k: v for k, v in self.fuzzy_matches.items() 
                           if v["status"] == "pending"}
        
        if pending_synonyms:
            report.append(f"**Total:** {len(pending_synonyms)} sugestões\n")
            
            # Ordena por frequência
            sorted_syns = sorted(pending_synonyms.items(), 
                                key=lambda x: len(x[1]["occurrences"]), 
                                reverse=True)
            
            for syn_key, data in sorted_syns:
                count = len(data["occurrences"])
                
                report.append(f"\n### `{data['input_term']}` → `{data['matched_exam']}`")
                report.append(f"- **Frequência:** {count}x")
                report.append(f"- **Estratégia atual:** {data['strategy']}")
                report.append(f"- **Ação sugerida:** {data['suggested_action']}")
        else:
            report.append("*Nenhuma sugestão pendente.*\n")
        
        return "\n".join(report)
    
    def export_report(self, filename: str = None):
        """Exporta relatório para arquivo markdown"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.log_dir, f"relatorio_curadoria_{timestamp}.md")
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filename

# Singleton global
missing_terms_logger = MissingTermsLogger()
