# Crédito de Carbono — Dashboard Corporativo

> Retrato consolidado das emissões de GEE registradas no **Registro Público de Emissões** da Fundação Getulio Vargas, com análise por escopos (1, 2 e 3) e estimativa financeira de compensação no mercado voluntário brasileiro.

---

## Visão Geral

Este projeto é um pipeline de dados ponta-a-ponta que coleta, processa e visualiza os inventários de gases de efeito estufa (GEE) de empresas brasileiras, conforme publicados na plataforma FGV GHG Protocol. O resultado é um dashboard editorial interativo — design Midnight Editorial — que cruza emissões por escopo com a contrapartida financeira da compensação via créditos de carbono.

```
Registro Público FGV (API)
        │
        ▼
 Baixar PDF.py          ← coleta PDFs + metadados (~220 empresas)
        │
        ▼
 extrator_pdf.py        ← extrai texto dos PDFs → JSON em lotes
        │
        ▼
 filtro_carbono_ia.py   ← estrutura dados de emissão via regex
        │
        ▼
 dashboard_carbono.py   ← gera dashboard HTML interativo (Plotly)
        │
        ▼
 web/html/dashboard_carbono.html
```

---

## Funcionalidades

| Etapa         | Script                 | Descrição                                                                                                    |
| ------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Coleta**    | `Baixar PDF.py`        | Acessa a API de busca da FGV, baixa PDFs e metadados de até 220 empresas com downloads paralelos (8 workers) |
| **Extração**  | `extrator_pdf.py`      | Lê os PDFs com `pdfplumber`, extrai texto e salva em lotes de 10 empresas em `JSON_Processados/`             |
| **Filtragem** | `filtro_carbono_ia.py` | Aplica regex para estruturar dados de Escopo 1, 2 e 3 e salva em lotes em `JSON_Filtrados_Carbono/`          |
| **Dashboard** | `dashboard_carbono.py` | Gera o HTML final com gráficos Plotly (emissões, ranking, escopos, geografia, compensação)                   |

**Seções do Dashboard:**

- **§00 — Panorama:** visão macro das emissões consolidadas
- **§01 — Emissores:** ranking das maiores empresas emissoras
- **§02 — Escopos:** comparativo Escopo 1, 2 e 3 por empresa
- **§03 — Geografia:** distribuição geográfica das emissões
- **§04 — Compensação:** estimativa financeira de créditos de carbono (USD 8,50/tCO₂e)
- **§05 — Registro:** tabela completa com todos os dados

---

## Estrutura do Projeto

```
.
├── Baixar PDF.py              # Etapa 1 — coleta de dados da API FGV
├── extrator_pdf.py            # Etapa 2 — extração de texto dos PDFs
├── filtro_carbono_ia.py       # Etapa 3 — filtragem e estruturação dos dados
├── dashboard_carbono.py       # Etapa 4 — geração do dashboard HTML
│
├── Base_Dados_FGV_Final/      # PDFs e metadados baixados (~220 empresas)
├── JSON_Processados/          # Texto extraído dos PDFs (lotes JSON)
├── JSON_Filtrados_Carbono/    # Dados de emissão estruturados (lotes JSON)
│
└── web/
    ├── html/
    │   └── dashboard_carbono.html   # Dashboard final (gerado automaticamente)
    ├── css/
    │   └── style.css                # Design system — Midnight Editorial
    └── js/
        └── dashboard.js             # Interatividade (navegação, animações)
```

---

## Pré-requisitos

**Python 3.10+** com as seguintes dependências:

```bash
pip install requests pdfplumber pandas plotly tqdm urllib3
```

---

## Como Usar

Execute os scripts na ordem do pipeline:

```bash
# 1. Baixar PDFs e metadados da FGV (~220 empresas)
python "Baixar PDF.py"

# 2. Extrair texto dos PDFs para JSON
python extrator_pdf.py

# 3. Filtrar e estruturar os dados de emissão
python filtro_carbono_ia.py

# 4. Gerar o dashboard interativo
python dashboard_carbono.py
```

Após a etapa 4, abra `web/html/dashboard_carbono.html` no navegador.

> **Nota:** cada etapa depende da anterior. Os arquivos das pastas intermediárias (`JSON_Processados/`, `JSON_Filtrados_Carbono/`) são gerados automaticamente e não precisam de edição manual.

---

## Fonte de Dados

| Campo            | Detalhe                                                                  |
| ---------------- | ------------------------------------------------------------------------ |
| **Plataforma**   | Registro Público de Emissões — FGV GHG Protocol                          |
| **API de busca** | `registropublicodeemissoesapi.fgv.br`                                    |
| **Empresas**     | ~902 organizações brasileiras                                            |
| **Escopos**      | GHG Protocol — Escopos 1, 2 e 3                                          |
| **Precificação** | USD 8,50 / tCO₂e (mercado voluntário, estimativa conservadora 2023-2024) |

---

## Design

O dashboard segue o sistema visual **Midnight Editorial** — paleta escura de alto contraste com tipografia editorial e acentos em gold/azure:

| Token    | Cor                   | Uso                    |
| -------- | --------------------- | ---------------------- |
| Escopo 1 | `#e2b84d` Gold        | Emissões diretas       |
| Escopo 2 | `#5d8fc9` Azure       | Energia elétrica       |
| Escopo 3 | `#8ab4e0` Ice         | Cadeia de valor        |
| Total    | `#f0ca65` Gold-bright | Consolidado            |
| Crédito  | `#3a6ea5` Steel       | Compensação financeira |

---

## Licença

Uso interno. Os dados são públicos e provêm do Registro Público de Emissões da FGV.
