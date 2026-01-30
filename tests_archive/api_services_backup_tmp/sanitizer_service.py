import re

class SanitizerService:
    """
    Serviço especializado em limpeza final e 'Firewall' de ruído.
    Garante que endereços, nomes de médicos e metadados não passem.
    """

    # Salvaguardas Médicas (Whitelist)
    # Termos que, se presentes no início, garantem que a linha é um exame.
    IMMUNITY_PREFIXES = (
        "ANTI", "FAN", "SOROLOGIA", "PESQUISA", "DOSAGEM", "HEMO", "GLICO", "UREIA", "CREAT", "LIPID", "PROTEIN", 
        "TSH", "VHS", "PCR", "IGE", "IGG", "IGM", "VITAMINA", "T3", "T4", "GAMA", "FOSFATASE", "TRANSAMINASE",
        "EAS", "UROCULTURA", "CULTURA", "TESTE", "PERFIL"
    )

    # Padrões de Ruído (Blacklist)
    # Regex compilados para performance e precisão.
    NOISE_PATTERNS = [
        # Endereços e Logradouros (Word Boundaries \b para evitar falsos positivos)
        r"\bRUA\b", r"\bAV\b", r"\bAVENIDA\b", r"\bALAMEDA\b", r"\bTRAVESSA\b",
        r"\bQD\.?\b", r"\bQUADRA\b", r"\bLT\.?\b", r"\bLOTE\b", r"\bBL\.?\b", r"\bBLOCO\b",
        r"\bST\.?\b", r"\bSETOR\b", r"\bBAIRRO\b", r"\bCOND\.?\b", r"\bCONDOMINIO\b",
        r"\bRES\.?\b", r"\bRESIDENCIAL\b", r"\bED\.?\b", r"\bEDIFICIO\b", r"\bSALA\b",
        # Cidades Comuns (Goiás/DF)
        r"GOI[ÂA]NIA", r"BRAS[ÍI]LIA", r"APARECIDA", r"VALPARA[ÍI]SO", r"TAGUATINGA", 
        r"OCIDENTAL", r"LUZI[ÂA]NIA", r"ÁGUAS LINDAS", r"SENADOR CANEDO", r"TRINDADE",
        # Identificação Profissional/Pessoal
        r"\bDR\.?\b", r"\bDRA\.?\b", r"\bDOUTOR(A)?\b", r"\bCRM\b", r"\bCNPJ\b", r"\bCPF\b", r"\bRG\b",
        # Contato e Metadados
        r"\bTEL\b", r"\bTEL\:", r"\bFONE\b", r"\bCEL\b", r"\bWHATSAPP\b", 
        r"\bPÁGINA\b", r"\bFOLHA\b", r"\bIMPRESSO EM\b", r"\bDATA\:\b"
    ]

    @classmethod
    def is_valid_exam(cls, text: str) -> bool:
        """
        Verifica se um texto é um exame válido ou ruído.
        Retorna True se for válido (passou no firewall).
        """
        if not text:
            return False
            
        normalized = text.upper().strip()
        
        # 1. Checa Imunidade (Se for exame garantido, passa direto)
        if normalized.startswith(cls.IMMUNITY_PREFIXES):
            return True
            
        # 2. Checa Blacklist (Se bater em qualquer padrão, é ruído)
        for pattern in cls.NOISE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                # print(f"🔥 Firewall Killed: {text} (Pattern: {pattern})")
                return False
                
        # 3. Regras Extras de Tamanho
        if len(normalized) < 3: # Exames muito curtos sem imunidade (ex: "A", "B")
            return False
            
        return True
