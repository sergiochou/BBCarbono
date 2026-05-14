# Crédito de Carbono — Dashboard Corporativo

> Retrato consolidado das emissões de GEE registradas no **Registro Público de Emissões** da Fundação Getulio Vargas, com análise por escopos GHG Protocol e estimativa financeira de compensação no mercado voluntário brasileiro.

---

## Visão Geral

Pipeline de dados ponta-a-ponta que coleta, processa e visualiza os inventários de gases de efeito estufa (GEE) de empresas brasileiras publicados na plataforma FGV GHG Protocol. O resultado é um dashboard editorial interativo com design **Midnight Editorial** — alternável entre modo escuro e modo claro — cruzando emissões por escopo com a contrapartida financeira da compensação via créditos de carbono.

```
Registro Público FGV (API)
        │
        ▼
 Baixar PDF.py           ← Etapa 1 — coleta PDFs e metadados da API FGV
        │
        ▼
 extrator_pdf.py         ← Etapa 2 — extrai texto dos PDFs → JSON em lotes
        │
        ▼
 filtro_carbono_ia.py    ← Etapa 3 — estrutura dados de emissão via regex
        │
        ▼
 dashboard_carbono.py    ← Etapa 4 — gera dashboard HTML interativo (Plotly)
        │
        ▼
 web/html/dashboard_carbono.html
```

---

## Funcionalidades

| Etapa | Script | Descrição |
|---|---|---|
| **Coleta** | `Baixar PDF.py` | Acessa a API da FGV, baixa PDFs e metadados com downloads paralelos (8 workers) |
| **Extração** | `extrator_pdf.py` | Lê PDFs com `pdfplumber`, extrai texto e salva em lotes de 10 empresas em `JSON_Processados/` |
| **Filtragem** | `filtro_carbono_ia.py` | Aplica regex para estruturar Escopo 1, 2 e 3; salva lotes em `JSON_Filtrados_Carbono/` |
| **Dashboard** | `dashboard_carbono.py` | Gera HTML final com gráficos Plotly interativos e design editorial responsivo |

### Seções do Dashboard

| Seção | Conteúdo |
|---|---|
| **§00 — Panorama** | Visão macro — total de emissões, créditos necessários e custo estimado |
| **§01 — Emissores** | Ranking das 20 maiores empresas emissoras por escopo |
| **§02 — Escopos** | Distribuição agregada e correlação entre Escopos 1, 2 e 3 |
| **§03 — Geografia** | Emissões consolidadas por Unidade Federativa |
| **§04 — Compensação** | Créditos necessários e custo estimado de compensação (USD/tCO₂e) |
| **§05 — Registro** | Tabela completa paginada com filtros e busca por empresa |

---

## Estrutura do Projeto

```
.
├── Baixar PDF.py              # Etapa 1 — coleta de dados da API FGV
├── extrator_pdf.py            # Etapa 2 — extração de texto dos PDFs
├── filtro_carbono_ia.py       # Etapa 3 — filtragem e estruturação dos dados
├── dashboard_carbono.py       # Etapa 4 — geração do dashboard HTML
│
├── Base_Dados_FGV_Final/      # PDFs e metadados baixados
├── JSON_Processados/          # Texto extraído dos PDFs (lotes JSON)
├── JSON_Filtrados_Carbono/    # Dados de emissão estruturados (lotes JSON)
│
└── web/
    ├── html/
    │   └── dashboard_carbono.html   # Dashboard final (gerado por dashboard_carbono.py)
    ├── css/
    │   └── style.css                # Design system — Midnight Editorial (dark + light mode)
    └── js/
        └── dashboard.js             # Interatividade: navegação, animações, tema
```

---

## Pré-requisitos

**Python 3.10+**

```bash
pip install requests pdfplumber pandas plotly tqdm urllib3
```

---

## Como Usar

Execute os scripts na ordem do pipeline:

```bash
# Etapa 1 — Baixar PDFs e metadados da FGV
python "Baixar PDF.py"

# Etapa 2 — Extrair texto dos PDFs para JSON
python extrator_pdf.py

# Etapa 3 — Filtrar e estruturar os dados de emissão
python filtro_carbono_ia.py

# Etapa 4 — Gerar o dashboard interativo
python dashboard_carbono.py
```

O dashboard abre automaticamente no navegador após a Etapa 4. Para visualizar sem re-executar o pipeline, abra `web/html/dashboard_carbono.html` diretamente.

> Cada etapa depende da anterior. Os arquivos nas pastas intermediárias (`JSON_Processados/`, `JSON_Filtrados_Carbono/`) são gerados automaticamente.

---

## Fonte de Dados

| Campo | Detalhe |
|---|---|
| **Plataforma** | Registro Público de Emissões — FGV GHG Protocol |
| **API** | `registropublicodeemissoesapi.fgv.br` |
| **Cobertura** | ~902 organizações brasileiras |
| **Metodologia** | GHG Protocol — Escopos 1, 2 e 3 |
| **Precificação** | USD 8,50 / tCO₂e (mercado voluntário, estimativa conservadora 2023-2024) |

---

## Design

O dashboard segue o sistema visual **Midnight Editorial** com suporte a modo escuro (padrão) e modo claro, alternáveis via botão fixo no canto inferior direito. A preferência é salva entre sessões.

### Paleta de Cores

| Token | Cor | Uso |
|---|---|---|
| Escopo 1 | `#e2b84d` Gold | Emissões diretas |
| Escopo 2 | `#5d8fc9` Azure | Energia elétrica |
| Escopo 3 | `#8ab4e0` Ice | Cadeia de valor |
| Total | `#f0ca65` Gold-bright | Consolidado |
| Crédito | `#3a6ea5` Steel | Compensação financeira |

### Temas

| Modo | Fundo | Texto | Ativação |
|---|---|---|---|
| **Escuro** (padrão) | `#0a1220` Midnight | `#e0dff0` Paper | Padrão / botão ☀ |
| **Claro** | `#ffffff` White | `#1a2340` Navy | Botão 🌙 |

---

## Equipe

| Nome | Perfil |
|---|---|
| Pedro Monteiro | [linkedin.com/in/pedro-ism](https://www.linkedin.com/in/pedro-ism/) |
| Sérgio Chousino | [github.com/sergiochou](https://github.com/sergiochou) |
| Ricardo Severiano | [github.com/byteric](https://github.com/byteric) |
| Rafael Aimbere | [github.com/codeblack2301](https://github.com/codeblack2301) |

---

## Licença

Uso interno. Os dados são públicos e provêm do Registro Público de Emissões da FGV.
