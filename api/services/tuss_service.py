import json
import re
import os
import unicodedata

class TussService:
    def __init__(self, json_path: str = None):
        if json_path is None:
            # Caminho relativo ao diretório da API
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.json_path = os.path.join(base_dir, "temp_tuss/TUSS/tabela 22/tabela_22.json")
        else:
            self.json_path = json_path
            
        self.procedures = {} # map code -> full data
        self.synonyms = {}   # map alias -> official name
        self._load_data()

    def _normalize(self, text: str) -> str:
        """Remove accents and lowercase for robust matching"""
        if not text: return ""
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        return text.lower().strip()

    def _load_data(self):
        try:
            if not os.path.exists(self.json_path):
                print(f"⚠️ TUSS JSON not found at {self.json_path}")
                return

            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for row in data.get('rows', []):
                proc_name = row.get('procedimento', '')
                code = row.get('codigo')
                
                # Check for parenthesis synonyms
                # Ex: "Pesquisa de elementos anormais  do sedimento (EAS)" -> Extract "EAS"
                match = re.search(r'\((.*?)\)', proc_name)
                if match:
                    alias = match.group(1)
                    # Adiciona aos sinônimos normalizados
                    norm_alias = self._normalize(alias)
                    if len(norm_alias) > 2: # Ignorar (a) (b) etc
                        self.synonyms[norm_alias] = proc_name
                
                # Adiciona o nome oficial também como chave para lookup direto
                self.synonyms[self._normalize(proc_name)] = proc_name
                
                count += 1
            
            # --- SINÔNIMOS MANUAIS (CURADORIA) ---
            # Alias comum -> Nome TUSS exato encontrado no arquivo (ou adaptado para BQ)
            # Obs: Adaptado para bater com a chave do BigQuery (agora limpa de dashes)
            bq_eas_key = "urina rotina eas"
            self.synonyms["eas"] = bq_eas_key
            self.synonyms["urina tipo 1"] = bq_eas_key
            self.synonyms["urina tipo i"] = bq_eas_key
            self.synonyms["sumario de urina"] = bq_eas_key
            
            self.synonyms["tsh"] = "hormonio tireoestimulante (tsh) -" # Chute educado, mas vamos verificar depois se falhar
            self.synonyms["hemograma"] = "hemograma completo -" # Exemplo comum
            
            # Coprologico
            self.synonyms["coprologico"] = "coprologico funcional"
            self.synonyms["coprologico funcional"] = "coprologico funcional"
            
            # H.Pylori - Nome exato do BigQuery
            self.synonyms["h.pylori"] = "antigeno helicobacter pylori"
            self.synonyms["h pylori"] = "antigeno helicobacter pylori"
            self.synonyms["pylori"] = "antigeno helicobacter pylori"
            self.synonyms["helicobacter pylori"] = "antigeno helicobacter pylori"
            self.synonyms["antigeno fecal"] = "antigeno helicobacter pylori"
            self.synonyms["pesquisa antigeno fecal para h.pylori"] = "antigeno helicobacter pylori"
            
            # Perfil Lipídico
            self.synonyms["perfil lipidico"] = "lipidograma"
            self.synonyms["lipidograma"] = "lipidograma"

            # FSH
            self.synonyms["fsh"] = "hormonio foliculo estimulante (fsh)"
            self.synonyms["hormonio foliculo estimulante"] = "hormonio foliculo estimulante (fsh)"

            # TGO / AST
            self.synonyms["tgo"] = "aspartato aminotransferase (ast)"
            self.synonyms["ast"] = "aspartato aminotransferase (ast)"
            self.synonyms["aspartato aminotransferase"] = "aspartato aminotransferase (ast)"
            
            # TGP / ALT
            self.synonyms["tgp"] = "alanina aminotransferase (alt)"
            self.synonyms["alt"] = "alanina aminotransferase (alt)"
            self.synonyms["alanina aminotransferase"] = "alanina aminotransferase (alt)"

            # Hemoglobina Glicada
            self.synonyms["hemoglobina glicada"] = "hemoglobina glicada (a1c), dosagem"
            self.synonyms["glicada"] = "hemoglobina glicada (a1c), dosagem"
            self.synonyms["hba1c"] = "hemoglobina glicada (a1c), dosagem"

            # Vitamina B12
            self.synonyms["vitamina b12"] = "vitamina b12 - pesquisa e/ou dosagem"
            self.synonyms["vit b12"] = "vitamina b12 - pesquisa e/ou dosagem"
            self.synonyms["b12"] = "vitamina b12 - pesquisa e/ou dosagem"
            
            # TODO: Idealmente, carregar chaves do BQ na inicialização para validar cruzamento
            
            print(f"✅ TUSS Service Loaded: {count} procedures. Synonyms ready.")
            
        except Exception as e:
            print(f"❌ Error loading TUSS data: {e}")

    def search(self, term: str):
        """Returns standard name if found, else None"""
        norm_term = self._normalize(term)
        # 1. Tenta match exato
        if norm_term in self.synonyms:
            return self.synonyms[norm_term]
        return None

if __name__ == "__main__":
    # Teste
    pass

# Singleton instance global
tuss_service = TussService()
