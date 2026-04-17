# Carrossel da Tabela Completa + Animações do Dashboard

**Data**: 2026-04-16
**Escopo**: `dashboard_carbono.py`, `web/css/style.css`, `web/js/dashboard.js` (novo)

## Problema

A tabela "completa" no final do `dashboard_carbono.html` hoje lista todas as empresas em uma única `<table>`. Com 89 registros já fica longa; o dataset deve escalar para ~902 empresas, o que tornaria a página insustentável verticalmente. Além disso, o site tem poucas microinterações — hover states são sutis demais e falta vida ao clicar/passar o mouse.

## Objetivos

1. Substituir a tabela única por um **carrossel paginado** (41 empresas por página, nº de páginas dinâmico).
2. Adicionar **animações editoriais** em KPIs, chart cards, navegação, linhas da tabela, botões do carrossel e contagem progressiva dos valores.
3. Preservar o caráter estático, printável e editorial do site. Respeitar `prefers-reduced-motion`.

## Design

### 1. Paginação dinâmica da tabela

`_render_tabela_html(df, page_size=41)` em `dashboard_carbono.py` passa a:

- Calcular `n_pages = math.ceil(len(df) / page_size)`.
- Emitir uma `<div class="carousel-slide" data-page="i">` para cada chunk, contendo uma `<table class="data-table">` completa (com `<thead>` próprio).
- Envolver tudo em `<div class="data-carousel" data-total-pages="N">` com `.carousel-viewport > .carousel-track`, `.carousel-controls` (botões prev/next + `<nav class="carousel-pages">`) e `.carousel-meta` (texto "Página X de N · 41 empresas por página").

Exemplo de comportamento:
- 89 empresas → 3 páginas (41 + 41 + 7).
- 902 empresas → 22 páginas (41 × 22).

A paginação numérica é compacta, construída via JS:
- Menos de 8 páginas: `1 2 3 4 5`.
- Mais: `1 … 8 9 10 11 12 … 22` (sempre mostra primeiro, último e vizinhança do atual).

### 2. Animação de transição entre páginas

Estilo: **slide curto + fade** (40px de deslocamento horizontal, 420ms, `cubic-bezier(0.2, 0.8, 0.2, 1)`).

- Todas as slides ficam em `position: absolute` dentro do viewport; apenas a ativa é visível.
- Ao trocar para página maior: slide atual sai com `translateX(-40px)` + `opacity: 0`; nova entra de `translateX(+40px)` → `0`, 80ms depois.
- Direção inverte quando vai para página menor.
- `.carousel-viewport` tem altura controlada por JS via `ResizeObserver` (evita salto quando última página tem menos linhas).
- Nas extremidades os botões `‹` e `›` ficam desabilitados (opacidade 0.3, `pointer-events: none`). Sem loop circular.
- Teclado: setas `←` `→` avançam quando o carrossel está em foco.
- `prefers-reduced-motion`: transição cai para `0.01s` (troca instantânea).

### 3. Animações pelo site

**A — KPI tiles (`.kpi-tile`)**
- Hover: `translateY(-4px)`, sombra colorida pela var de accent (ember/slate/amber/paper), borda inferior em accent cresce de `scaleX(0)` → `scaleX(1)` em 400ms.
- Valor recebe leve `text-shadow` glow na cor do accent.

**B — Chart cards (`.chart-card`)**
- Hover: borda de `--hairline` → `--hairline-bright`, `translateY(-2px)` + sombra suave.
- Reveal progressivo via `IntersectionObserver` para cards fora do viewport inicial (fade-up extra, stagger por índice).

**C — Rail (`.rail a`)**
- Underline animado: `::after` com `transform: scaleX(0) → scaleX(1)` origem à esquerda, 320ms.
- Seção ativa detectada por `IntersectionObserver` nos `<article class="chapter">`: âncora correspondente recebe cor `--paper-bright` e underline persistente.

**D — Linhas da tabela (`.data-table tbody tr`)**
- Hover intensificado: `padding-left` 14px → 20px, `td.total` muda cor para `--ember-hot`, 220ms.

**E — Botões do carrossel**
- Hover: fundo `color-mix(var(--ember) 10%)`, borda acentuada.
- Click: ripple circular curto (200ms) + `transform: scale(0.95)` no `:active`.
- Página ativa em `--ember`.

**F — Count-up dos KPIs**
- `hero-value` e cada `.kpi-tile .value` contam de 0 ao valor final em ~1400ms com `easeOutExpo`, disparados uma única vez ao entrar no viewport.
- Formatação BR preservada (pontos, vírgulas, sufixos "M"/"tCO₂e"/"US$"). O JS detecta prefixo/sufixo no texto original e só anima a parte numérica.
- Em `prefers-reduced-motion`, mostra valor final direto.

### 4. Arquitetura de arquivos

| Arquivo | Mudança |
|---|---|
| `dashboard_carbono.py` | `_render_tabela_html` paginada; template do HTML referencia `dashboard.js`. |
| `web/css/style.css` | Novo bloco `/* Carousel */`; refinos em `.kpi-tile:hover`, `.chart-card:hover`, `.rail a::after`, `.data-table tbody tr:hover`. Bloco `@media print` revelando todas as slides. |
| `web/js/dashboard.js` | **Novo** — módulo único, sem dependências. Responsável por: carrossel, paginação compacta, teclado, `ResizeObserver` de altura, `IntersectionObserver` para rail ativo e count-up. Carregado com `<script defer>`. |

Pipeline de dados (geração dos JSONs, Plotly, layout geral, paleta, fontes) não muda.

## Acessibilidade

- Botões de paginação com `aria-label` ("Página anterior", "Próxima página", "Ir para página N").
- Página ativa com `aria-current="page"`.
- Wrapper com `role="region"` + `aria-label="Registro completo de empresas, paginado"`.
- Foco visível nos controles (outline respeitando a paleta).
- Todas as animações respeitam `prefers-reduced-motion`.

## Fora de escopo

- Busca/filtro na tabela. Seria útil, mas aumenta superfície e quebra a estética "registro impresso". Pode ser um próximo spec.
- Loop circular no carrossel.
- Cursor custom em áreas interativas (descartado na conversa).
- Export CSV / download direto (dataset já está no JSON de origem).

## Critérios de aceitação

1. Abrindo `dashboard_carbono.html` com 89 empresas, aparecem 3 páginas (41+41+7), navegáveis por setas, paginação numérica compacta e teclado.
2. Transição entre páginas é um slide curto (~40px) + fade de ~420ms; respeita `prefers-reduced-motion`.
3. Hover em KPIs eleva o tile, ilumina o valor e preenche a barra inferior do accent.
4. Chart cards respondem ao hover com borda acentuada e leve lift.
5. Links do rail têm underline animado e a seção atual é destacada conforme o scroll.
6. Linhas da tabela fazem push à direita no hover, com o total em cor ember.
7. Botões do carrossel têm ripple no click e são desabilitados nas extremidades.
8. Count-up executa uma única vez nos KPIs; formatação BR preservada.
9. Ao imprimir (Ctrl+P), o bloco `@media print` revela todas as slides do carrossel em sequência (as escondidas voltam a ficar visíveis; controles somem).
