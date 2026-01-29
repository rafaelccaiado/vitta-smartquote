import re

def smart_parse_prescription(full_text: str) -> str:
    lines = full_text.split('\n')
    cleaned_lines = []
    
    # Regex de padrões para ignorar (Ruído Comum)
    patterns_to_ignore = [
        r"cpf[:\s].*",  # CPF
        r"cnpj[:\s].*",
        r"rg[:\s].*",
        r"tel[:\s].*",
        r"rua\s.*",   # Endereços
        r"av\.?\s.*",
        r"avenida\s.*",
        r"alameda\s.*",
        r"bairro\s.*",
        r"cep[:\s].*",
        r"crm[:\s].*", # CRM geralmente no rodapé
        r"crm-?go.*",
        r"dra?\.?\s.*", # Nomes de médicos
        r"paciente[:\s].*",
        r"convênio[:\s].*",
        r"unimed.*",
        r"data[:\s].*",
        r"ass\..*",
        r"^\d{2}/\d{2}/\d{2,4}.*", # Datas soltas
        r"página\s\d.*",
        r"folha\s\d.*",
        r"^id[:\s]\d+", # IDs internos
        r"^unidade:.*",
        r"^exames$", # Titulo solto
        r"^solicito$", # Titulo solto
        r"^pedido de exame$",
        r"^indicação clínica.*",
        r"^código.*",
        r"^sexo:.*",
        r"^nascimento:.*",
        r"^idade:.*",
        r"^documento gerado.*",
        r"^assinado digitalmente.*",
        r"^responsável técnico.*"
    ]
    
    # Compilar regexes
    ignore_regexes = [re.compile(p, re.IGNORECASE) for p in patterns_to_ignore]
    
    # Marcador se já encontramos o início da lista de exames
    # Se encontrarmos "Solicito", tudo antes é provavel cabeçalho
    has_start_anchor = False
    start_anchors = ["solicito", "prescrição", "prescrevo", "exames abaixo", "lista de exames"]
    
    extracted_exams = []

    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean: continue
        
        # Checa âncora de início (Prioridade Máxima)
        if hasattr(start_anchors, '__iter__') and any(anchor in line_clean.lower() for anchor in start_anchors):
             has_start_anchor = True
             continue # Pula a linha que diz "Solicito"
             
        # Se NÃO achou âncora ainda, seremos agressivos no filtro
        # Mas se já achou, pegamos quase tudo, exceto rodapés óbvios
        
        # Aplica Regex de "blocklist"
        if any(regex.search(line_clean) for regex in ignore_regexes):
            continue
            
        # Filtro de tamanho mínimo
        if len(line_clean) < 3: continue
        
        # Filtro heurístico para nomes de médicos soltos no final (geralmente sem contexto)
        # Ex: "Aniele N. de Siqueira" -> Maioria Words start upper
        if not has_start_anchor and regex_is_name(line_clean):
             continue 
             
        # Se achou ancora, adiciona
        if has_start_anchor:
            extracted_exams.append(line_clean)
        else:
            # Se não tem ancora explicita, tentamos "adivinhar" que é exame se não caiu na blocklist
            # Mas é arriscado. Vamos confiar na Blocklist forte.
            extracted_exams.append(line_clean)
    
    return "\n".join(extracted_exams)

def regex_is_name(text):
    # Heurística simples: Maioria das palavras começa com maiúscula e não tem números
    words = text.split()
    if len(words) < 2: return False
    if any(char.isdigit() for char in text): return False
    capitalized = sum(1 for w in words if w[0].isupper())
    return capitalized / len(words) > 0.8

# ... (código de teste)
    
    # Se detectou ancora, tenta retornar só o que veio depois
    # Mas se a lista ficou vazia (ex: âncora no final errado), retorna o filtro padrão
    
    return "\n".join(parsed_lines)

# CASO DE TESTE (Do Print do Usuário)
sample_text = """
amorsaúde
ROSIVAN PAIVA DA SILVA
CPF: 05225022375
Sexo: Masculino
Nascimento: 06/01/1991
AmorSaúde Medicina, Odontologia
Exames
Av, Circular, 751, Qd 117
Dra. Aniele Neves de Siqueira
Pedido de Exame
Indicação Clínica: Rotina/ Distúrbio intestinal
SOLICITO
Hemograma completo
Glicemia de jejum
Hemoglobina glicada
Perfil lipídico
TSH
T4 livre
EAS
EPF
Vitamina D
Vitamina B12
Ferritina
Ferro sérico
Ácido úrico
Ureia
ID
A
1s
CRM: 19412/GO
Creatinina
Coprológico funcional
Pesquisa antígeno fecal para H.pylori
Aniele N. de Siqueira
CRM-GO 19412
Documento gerado eletronicamente
"""

print("--- TEXTO ORIGINAL ---")
print(sample_text)
print("\n--- TEXTO PROCESSADO (SMART PARSER) ---")
print(smart_parse_prescription(sample_text))
