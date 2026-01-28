# Sistema de Curadoria - Vittá SmartQuote

## 📋 Visão Geral

Sistema automático de logging e sugestões para melhorar a qualidade do matching de exames.

## 🎯 Funcionalidades

### 1. **Rastreamento de Termos Não Encontrados**
- Registra automaticamente exames que não foram encontrados em nenhuma tabela
- Agrupa por frequência e unidade
- Sugere adição na tabela de preços

### 2. **Sugestões de Sinônimos**
- Identifica termos que só foram encontrados via fuzzy/substring matching
- Sugere criação de sinônimos para melhorar precisão
- Prioriza por frequência de uso

## 📊 Como Usar

### Opção 1: Via API

```bash
# Gerar relatório via endpoint
curl http://localhost:8000/api/curation-report
```

Retorna:
```json
{
  "report": "# Relatório de Curadoria...",
  "file_path": "logs/relatorio_curadoria_20260127_203058.md",
  "not_found_count": 5,
  "synonym_suggestions_count": 12
}
```

### Opção 2: Via Script Python

```python
from services.missing_terms_logger import missing_terms_logger

# Gerar relatório
report = missing_terms_logger.generate_report()
print(report)

# Exportar para arquivo
file_path = missing_terms_logger.export_report()
```

### Opção 3: Automático

O sistema registra automaticamente durante o uso normal da aplicação. Basta:

1. Usar o sistema normalmente (fazer cotações)
2. Periodicamente, acessar `/api/curation-report` para ver sugestões
3. Implementar as melhorias sugeridas

## 📁 Arquivos Gerados

### `logs/exames_nao_encontrados.json`
```json
{
  "coprologico funcional": {
    "original_term": "Coprologico funcional",
    "occurrences": [
      {
        "timestamp": "2026-01-27T20:30:58",
        "unit": "Plano Piloto",
        "context": null
      }
    ],
    "status": "pending",
    "notes": ""
  }
}
```

### `logs/sugestoes_sinonimos.json`
```json
{
  "glicemia jejum -> glicemia de jejum": {
    "input_term": "Glicemia jejum",
    "matched_exam": "glicemia de jejum",
    "strategy": "fuzzy",
    "occurrences": [...],
    "status": "pending",
    "suggested_action": "Adicionar sinônimo: 'Glicemia jejum' -> 'glicemia de jejum'"
  }
}
```

### `logs/relatorio_curadoria_YYYYMMDD_HHMMSS.md`
Relatório em markdown para revisão humana.

## 🔄 Workflow de Curadoria

1. **Coleta Automática** (Sistema em produção)
   - Logs são gerados automaticamente durante uso normal

2. **Revisão Periódica** (Semanal/Mensal)
   - Acessar `/api/curation-report`
   - Revisar termos não encontrados
   - Revisar sugestões de sinônimos

3. **Implementação**
   - **Exames não encontrados**: Adicionar na tabela de preços do BigQuery
   - **Sinônimos**: Adicionar em `validation_logic.py` no dicionário `SYNONYMS`

4. **Marcar como Resolvido**
   - Editar JSON e mudar `"status": "pending"` para `"status": "added"`
   - Ou adicionar notas: `"notes": "Adicionado em 27/01/2026"`

## 🛠️ Exemplo de Implementação

### Adicionar Sinônimo Sugerido

Se o relatório sugerir:
```
Adicionar sinônimo: 'Glicemia jejum' -> 'glicemia de jejum'
```

Edite `validation_logic.py`:
```python
SYNONYMS = {
    # ... sinônimos existentes ...
    "glicemia jejum": ["glicemia de jejum"],  # NOVO
}
```

### Adicionar Exame Faltante

Se o relatório indicar:
```
Exame não encontrado: "Coprologico funcional"
```

1. Verificar se o exame realmente existe
2. Adicionar na tabela de preços do BigQuery
3. Ou criar sinônimo para exame equivalente

## 📈 Métricas

O sistema rastreia:
- **Frequência**: Quantas vezes cada termo foi buscado
- **Unidades**: Em quais unidades o termo foi buscado
- **Timestamp**: Quando ocorreu cada busca
- **Estratégia**: Como o match foi feito (fuzzy, substring, etc)

## 🔐 Privacidade

- Não armazena dados de pacientes
- Apenas termos de exames e metadados de busca
- Logs locais (não enviados para nuvem)

## 📝 Notas

- Logs são incrementais (não sobrescrevem)
- Relatórios markdown são timestamped
- Status pode ser: `pending`, `added`, `ignored`
