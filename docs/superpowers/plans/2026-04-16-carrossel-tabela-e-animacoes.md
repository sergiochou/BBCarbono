# Carrossel da Tabela e Animações — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paginar a tabela completa em um carrossel dinâmico (41 empresas por página) e adicionar animações editoriais pelo dashboard.

**Architecture:** Python gera HTML estático com múltiplas `<table>` agrupadas como slides de carrossel. CSS cuida do layout, transições e hover states refinados. JS vanilla (sem dependências) controla troca de slides, paginação compacta, destaque do rail via `IntersectionObserver` e count-up dos KPIs.

**Tech Stack:** Python 3.14 + pandas (já existente), CSS3 com custom properties, JavaScript vanilla (ES2020+), sem build step.

**Project conventions:** Não existe `pytest` nem infraestrutura de testes automáticos. A verificação é funcional: rodar `python dashboard_carbono.py`, abrir `web/html/dashboard_carbono.html` no navegador e conferir o comportamento descrito em cada tarefa. Cada task termina com um commit.

**Arquivos afetados:**
- `dashboard_carbono.py` — modificar `_render_tabela_html` e adicionar referência ao novo `dashboard.js` no template.
- `web/css/style.css` — novos blocos (carrossel, count-up) e refinos em seletores existentes.
- `web/js/dashboard.js` — arquivo novo, módulo único.

---

## Task 1: Stub do dashboard.js e wiring no template Python

**Files:**
- Create: `web/js/dashboard.js`
- Modify: `dashboard_carbono.py:28-30` (adicionar constante `CAMINHO_JS`)
- Modify: `dashboard_carbono.py:670-672` (inserir `<script defer>` no `<head>`)

- [ ] **Step 1: Criar o arquivo stub `web/js/dashboard.js`**

Conteúdo inicial:

```javascript
/* ════════════════════════════════════════════════════════════════════
   BBCarbono — Dashboard interactions
   ════════════════════════════════════════════════════════════════════
   Carrossel da tabela, rail ativo no scroll, count-up dos KPIs.
   Vanilla JS, sem dependencias.
   ════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function init() {
    // Placeholders — preenchidos nas tasks seguintes.
    console.debug('[BBCarbono] dashboard.js carregado (reduced-motion:', prefersReducedMotion, ')');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Adicionar constante `CAMINHO_JS` em `dashboard_carbono.py`**

Em `dashboard_carbono.py`, logo após a linha 30 (`CAMINHO_CSS = "../css/style.css"`), adicionar:

```python
CAMINHO_JS = "../js/dashboard.js"
```

- [ ] **Step 3: Inserir `<script defer>` no template HTML**

Em `dashboard_carbono.py` (por volta da linha 670–672), alterar o bloco:

```python
    <link rel="stylesheet" href="{CAMINHO_CSS}">
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
</head>
```

para:

```python
    <link rel="stylesheet" href="{CAMINHO_CSS}">
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    <script defer src="{CAMINHO_JS}"></script>
</head>
```

- [ ] **Step 4: Regenerar o HTML e verificar no browser**

Run: `python dashboard_carbono.py`

Abrir `web/html/dashboard_carbono.html`, abrir o DevTools (F12) → console. Esperado: aparece a linha `[BBCarbono] dashboard.js carregado (reduced-motion: false)` (ou `true` se o OS estiver em reduced-motion). Nenhum 404 no Network tab para `../js/dashboard.js`.

- [ ] **Step 5: Commit**

```bash
git add web/js/dashboard.js dashboard_carbono.py
git commit -m "feat: adiciona stub dashboard.js e carrega no template HTML"
```

---

## Task 2: Paginação do Python — `_render_tabela_html` emite múltiplos slides

**Files:**
- Modify: `dashboard_carbono.py:400-454` (função `_render_tabela_html`)
- Modify: `dashboard_carbono.py:14-18` (adicionar `import math`)

- [ ] **Step 1: Adicionar `import math` no topo de `dashboard_carbono.py`**

Em `dashboard_carbono.py:14-18`, trocar:

```python
import html as _html
import json
import logging
import webbrowser
from pathlib import Path
```

por:

```python
import html as _html
import json
import logging
import math
import webbrowser
from pathlib import Path
```

- [ ] **Step 2: Substituir a função `_render_tabela_html` inteira**

Em `dashboard_carbono.py:400-454`, substituir toda a função por:

```python
def _render_tabela_html(df: pd.DataFrame, page_size: int = 41) -> str:
    """Renderiza a tabela completa como carrossel paginado de HTML nativo.

    Cada chunk de `page_size` empresas vira uma <table> dentro de uma slide
    do carrossel. O numero de paginas e dinamico (ceil(len(df)/page_size)).
    A interatividade e controlada por web/js/dashboard.js.
    """
    total = len(df)
    n_pages = max(1, math.ceil(total / page_size))

    thead_html = (
        '<thead>'
        '<tr>'
        '<th class="th-empresa">Empresa</th>'
        '<th class="th-uf">UF</th>'
        '<th class="num">Escopo 1</th>'
        '<th class="num">Escopo 2</th>'
        '<th class="num">Escopo 3</th>'
        '<th class="num">Total tCO₂e</th>'
        '<th class="num">Creditos</th>'
        '<th class="num">Custo USD</th>'
        '<th>Compensa</th>'
        '<th>Net Zero</th>'
        '</tr>'
        '</thead>'
    )

    slides = []
    for page in range(n_pages):
        inicio = page * page_size
        fim = inicio + page_size
        chunk = df.iloc[inicio:fim]

        linhas = []
        for _, r in chunk.iterrows():
            net_zero = (
                f'<span class="nz-year">{int(r["meta_net_zero"])}</span>'
                if pd.notna(r["meta_net_zero"]) else '<span class="muted">—</span>'
            )
            compensa = (
                '<span class="tag tag-yes">Sim</span>'
                if r["tem_projeto_compensacao"]
                else '<span class="muted">—</span>'
            )
            linhas.append(
                '<tr>'
                f'<td class="empresa">{_html.escape(str(r["empresa"]).strip())}</td>'
                f'<td class="uf">{_html.escape(str(r["estado"]))}</td>'
                f'<td class="num">{fmt_br(r["escopo_1"])}</td>'
                f'<td class="num">{fmt_br(r["escopo_2"])}</td>'
                f'<td class="num">{fmt_br(r["escopo_3"])}</td>'
                f'<td class="num total">{fmt_br(r["total"])}</td>'
                f'<td class="num">{fmt_br(r["creditos_necessarios"])}</td>'
                f'<td class="num">US$ {fmt_br(r["custo_compensacao_usd"])}</td>'
                f'<td class="cell-tag">{compensa}</td>'
                f'<td class="cell-tag">{net_zero}</td>'
                '</tr>'
            )

        active_attr = ' data-active="true"' if page == 0 else ''
        slides.append(
            f'<div class="carousel-slide" data-page="{page + 1}"{active_attr}>'
            f'<div class="data-table-wrap">'
            f'<table class="data-table">'
            f'{thead_html}'
            f'<tbody>{"".join(linhas)}</tbody>'
            f'</table>'
            f'</div>'
            f'</div>'
        )

    return f"""
    <div class="data-carousel" data-total-pages="{n_pages}" data-page-size="{page_size}"
         role="region" aria-label="Registro completo de empresas, paginado">
      <div class="carousel-viewport">
        <div class="carousel-track">
          {''.join(slides)}
        </div>
      </div>
      <div class="carousel-controls">
        <button class="carousel-btn prev" type="button" aria-label="Pagina anterior" disabled>‹</button>
        <nav class="carousel-pages" role="tablist" aria-label="Selecionar pagina"></nav>
        <button class="carousel-btn next" type="button" aria-label="Proxima pagina">›</button>
      </div>
      <div class="carousel-meta">
        Pagina <strong class="carousel-current">1</strong> de <strong>{n_pages}</strong>
        &nbsp;·&nbsp; {page_size} empresas por pagina
        &nbsp;·&nbsp; {total} empresas no total
      </div>
    </div>
    """
```

- [ ] **Step 3: Regenerar o HTML e verificar o markup**

Run: `python dashboard_carbono.py`

Abrir `web/html/dashboard_carbono.html`. No DevTools → Elements, localizar `<div class="data-carousel">`. Esperado com 89 empresas:
- `data-total-pages="3"`
- 3 `<div class="carousel-slide" data-page="1|2|3">`
- primeira slide com `data-active="true"`
- `<div class="carousel-meta">` diz "Pagina 1 de 3 · 41 empresas por pagina · 89 empresas no total"

Visualmente as 3 tabelas aparecem empilhadas (ainda sem CSS de carrossel) — isso é esperado nesta task.

- [ ] **Step 4: Commit**

```bash
git add dashboard_carbono.py
git commit -m "feat: pagina tabela completa em chunks de 41 empresas (carrossel)"
```

---

## Task 3: CSS base do carrossel — viewport, track, slides e transição

**Files:**
- Modify: `web/css/style.css` (adicionar bloco novo antes do `@media (max-width: 920px)` da tabela, aproximadamente linha 738)

- [ ] **Step 1: Adicionar o bloco `/* Carousel */` ao `style.css`**

Inserir o seguinte bloco em `web/css/style.css` imediatamente antes da linha que começa com `@media (max-width: 920px)` (a regex `^\s*@media \(max-width: 920px\)` acha a posição; o bloco fica logo acima dela):

```css
/* ── Carousel da tabela ──────────────────────────────────────────── */

.data-carousel {
    position: relative;
    margin-top: 1rem;
}

.carousel-viewport {
    position: relative;
    overflow: hidden;
    transition: height 0.35s var(--ease-fluid);
}

.carousel-track {
    position: relative;
}

.carousel-slide {
    position: absolute;
    inset: 0;
    opacity: 0;
    pointer-events: none;
    transform: translateX(40px);
    transition:
        opacity 0.42s var(--ease-fluid),
        transform 0.42s var(--ease-fluid);
}

.carousel-slide[data-active="true"] {
    position: relative;
    opacity: 1;
    pointer-events: auto;
    transform: translateX(0);
}

.carousel-slide.exiting {
    position: absolute;
    opacity: 0;
    transform: translateX(-40px);
}

.carousel-slide.entering-from-left {
    transform: translateX(-40px);
}

.carousel-slide.exiting-to-right {
    transform: translateX(40px);
}

@media (prefers-reduced-motion: reduce) {
    .carousel-slide,
    .carousel-viewport {
        transition-duration: 0.01ms !important;
    }
}
```

- [ ] **Step 2: Regenerar o HTML e verificar no browser**

Run: `python dashboard_carbono.py`

Abrir a página. Esperado:
- Apenas a primeira tabela (página 1) fica visível dentro do viewport.
- As outras slides existem no DOM mas estão com `opacity: 0` e `transform: translateX(40px)` (verificar em DevTools → Elements → Computed).
- O viewport tem `overflow: hidden` e a altura "colapsa" para a primeira tabela (pode ficar com altura 0 inicialmente porque as slides estão absolutas — isso será resolvido pelo JS na Task 5 via `ResizeObserver`. Por enquanto a altura pode parecer estranha; isso é esperado).

Observação: nesta etapa a altura do viewport provavelmente fica quebrada porque todas as slides têm `position: absolute` enquanto a slide ativa tem `position: relative`. A slide ativa ainda dá altura ao track, então deve aparecer corretamente. Se não aparecer nada, conferir que a primeira slide tem o atributo `data-active="true"` no HTML gerado.

- [ ] **Step 3: Commit**

```bash
git add web/css/style.css
git commit -m "style: adiciona layout base do carrossel (slides empilhadas com fade+slide)"
```

---

## Task 4: CSS dos controles do carrossel (botões + paginação + meta)

**Files:**
- Modify: `web/css/style.css` (adicionar ao mesmo bloco `/* Carousel */` criado na Task 3)

- [ ] **Step 1: Adicionar os estilos de controles ao bloco Carousel**

Em `web/css/style.css`, imediatamente abaixo do bloco criado na Task 3 (ainda antes do `@media (max-width: 920px)` da tabela), adicionar:

```css
.carousel-controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    margin-top: 1.5rem;
    flex-wrap: wrap;
}

.carousel-btn {
    background: transparent;
    border: 1px solid var(--hairline-bright);
    color: var(--paper-dim);
    font-family: var(--font-display);
    font-size: 22px;
    line-height: 1;
    width: 40px;
    height: 40px;
    border-radius: 3px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    transition:
        color 0.25s var(--ease-fluid),
        border-color 0.25s var(--ease-fluid),
        background 0.25s var(--ease-fluid),
        transform 0.15s var(--ease-fluid);
}

.carousel-btn:hover:not(:disabled) {
    color: var(--paper-bright);
    border-color: var(--ember);
    background: color-mix(in srgb, var(--ember) 10%, transparent);
}

.carousel-btn:active:not(:disabled) {
    transform: scale(0.95);
}

.carousel-btn:disabled {
    opacity: 0.25;
    cursor: not-allowed;
}

.carousel-btn .ripple {
    position: absolute;
    border-radius: 50%;
    transform: scale(0);
    background: color-mix(in srgb, var(--ember) 35%, transparent);
    pointer-events: none;
    animation: carousel-ripple 0.45s var(--ease-fluid);
}

@keyframes carousel-ripple {
    to { transform: scale(3); opacity: 0; }
}

.carousel-pages {
    display: flex;
    gap: 0.25rem;
    align-items: center;
    font-family: var(--font-mono);
}

.carousel-page {
    background: transparent;
    border: none;
    color: var(--paper-faint);
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.08em;
    padding: 6px 10px;
    min-width: 30px;
    cursor: pointer;
    border-bottom: 1px solid transparent;
    transition:
        color 0.2s var(--ease-fluid),
        border-color 0.2s var(--ease-fluid);
}

.carousel-page:hover {
    color: var(--paper-bright);
}

.carousel-page[aria-current="page"] {
    color: var(--ember);
    border-bottom-color: var(--ember);
}

.carousel-ellipsis {
    color: var(--paper-whisper);
    padding: 0 4px;
    font-family: var(--font-mono);
    font-size: 12px;
    user-select: none;
}

.carousel-meta {
    margin-top: 1rem;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--paper-faint);
    text-align: center;
}

.carousel-meta strong {
    color: var(--paper-bright);
    font-weight: 600;
}
```

- [ ] **Step 2: Verificar no browser**

Run: `python dashboard_carbono.py` (não estritamente necessário — só CSS mudou, basta recarregar a página).

Recarregar `dashboard_carbono.html`. Esperado:
- Abaixo da tabela aparecem os botões `‹` e `›` e o texto de meta "Pagina 1 de 3 · 41 empresas por pagina · 89 empresas no total".
- A `<nav class="carousel-pages">` está vazia ainda (o JS é quem preenche na Task 6).
- Botão `‹` está disabled (opaco, cursor proibido).
- Hover nos botões muda a cor da borda para ember e o fundo ganha tint laranja.

- [ ] **Step 3: Commit**

```bash
git add web/css/style.css
git commit -m "style: adiciona controles do carrossel (botoes, paginacao, meta)"
```

---

## Task 5: JS — lógica de troca de slides e ResizeObserver de altura

**Files:**
- Modify: `web/js/dashboard.js`

- [ ] **Step 1: Substituir todo o conteúdo de `web/js/dashboard.js`**

```javascript
/* ════════════════════════════════════════════════════════════════════
   BBCarbono — Dashboard interactions
   ════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Carousel ────────────────────────────────────────────────────

  function initCarousel(root) {
    const viewport = root.querySelector('.carousel-viewport');
    const track    = root.querySelector('.carousel-track');
    const slides   = Array.from(root.querySelectorAll('.carousel-slide'));
    const prevBtn  = root.querySelector('.carousel-btn.prev');
    const nextBtn  = root.querySelector('.carousel-btn.next');
    const pagesNav = root.querySelector('.carousel-pages');
    const current  = root.querySelector('.carousel-current');
    const total    = slides.length;

    if (!total) return;

    let active = 0;

    function updateViewportHeight() {
      const activeSlide = slides[active];
      if (!activeSlide) return;
      const h = activeSlide.getBoundingClientRect().height;
      viewport.style.height = h + 'px';
    }

    function goTo(next) {
      if (next === active || next < 0 || next >= total) return;

      const direction = next > active ? 'forward' : 'backward';
      const oldSlide  = slides[active];
      const newSlide  = slides[next];

      // Prepara a nova slide fora da tela, no lado correto.
      newSlide.classList.remove('exiting', 'exiting-to-right', 'entering-from-left');
      if (direction === 'forward') {
        newSlide.style.transform = 'translateX(40px)';
      } else {
        newSlide.classList.add('entering-from-left');
      }
      newSlide.style.opacity = '0';
      newSlide.setAttribute('data-active', 'true');
      // Força reflow antes de animar a entrada.
      newSlide.getBoundingClientRect();

      // Remove o ativo da antiga e faz ela sair.
      oldSlide.removeAttribute('data-active');
      oldSlide.classList.add('exiting');
      if (direction === 'backward') {
        oldSlide.classList.add('exiting-to-right');
      }

      // Anima a nova entrando (com pequeno stagger).
      setTimeout(() => {
        newSlide.style.transform = '';
        newSlide.style.opacity   = '';
        newSlide.classList.remove('entering-from-left');
      }, prefersReducedMotion ? 0 : 80);

      // Limpa classes de saida depois da transicao.
      setTimeout(() => {
        oldSlide.classList.remove('exiting', 'exiting-to-right');
      }, prefersReducedMotion ? 20 : 520);

      active = next;
      updateControls();
      updateViewportHeight();
    }

    function updateControls() {
      prevBtn.disabled = active === 0;
      nextBtn.disabled = active === total - 1;
      if (current) current.textContent = String(active + 1);
      renderPagination();
    }

    function renderPagination() {
      // Placeholder — implementado integralmente na Task 6.
      pagesNav.innerHTML = '';
    }

    prevBtn.addEventListener('click', () => goTo(active - 1));
    nextBtn.addEventListener('click', () => goTo(active + 1));

    // ResizeObserver para reajustar altura do viewport.
    if ('ResizeObserver' in window) {
      const ro = new ResizeObserver(() => updateViewportHeight());
      slides.forEach(s => ro.observe(s));
    }
    window.addEventListener('resize', updateViewportHeight);

    // Inicializacao.
    updateControls();
    // Pequeno delay para fonts/layout assentarem.
    requestAnimationFrame(() => {
      updateViewportHeight();
    });

    // Expor para proxima task (paginacao numerica).
    root._carousel = { goTo, getActive: () => active, total };
  }

  // ── Bootstrap ───────────────────────────────────────────────────

  function init() {
    document.querySelectorAll('.data-carousel').forEach(initCarousel);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Verificar navegação por setas no browser**

Run: `python dashboard_carbono.py` (regenera HTML para pegar qualquer mudança — CSS/JS já estão vinculados).

Abrir `dashboard_carbono.html`. Esperado:
- Viewport tem altura correspondente à primeira tabela (sem colapsar).
- Clicar em `›` faz a tabela 1 sair pela esquerda com fade e a tabela 2 entrar pela direita com fade, ~420ms.
- Clicar em `‹` faz o inverso.
- No início, botão `‹` disabled; ao chegar na última, `›` disabled.
- Texto "Pagina X de N" atualiza conforme navega.
- Redimensionar a janela ajusta a altura do viewport (a tabela 3 tem só 7 linhas — ao navegar pra ela, o viewport encolhe suavemente).

Caso alguma slide "suma" ou não volte, conferir no console erros de JS.

- [ ] **Step 3: Commit**

```bash
git add web/js/dashboard.js
git commit -m "feat: implementa troca de slides do carrossel com transicao fade+slide"
```

---

## Task 6: JS — paginação numérica compacta + teclado

**Files:**
- Modify: `web/js/dashboard.js` (substituir `renderPagination` e adicionar listener de teclado)

- [ ] **Step 1: Substituir a função `renderPagination` (atualmente um placeholder vazio) e adicionar listener de teclado**

Em `web/js/dashboard.js`, dentro de `initCarousel`, substituir:

```javascript
    function renderPagination() {
      // Placeholder — implementado integralmente na Task 6.
      pagesNav.innerHTML = '';
    }
```

por:

```javascript
    function renderPagination() {
      if (!pagesNav) return;
      pagesNav.innerHTML = '';

      // Gera a lista de tokens: numeros de pagina ou o simbolo '…'.
      const tokens = buildPageTokens(active, total);

      tokens.forEach(tok => {
        if (tok === '…') {
          const span = document.createElement('span');
          span.className = 'carousel-ellipsis';
          span.setAttribute('aria-hidden', 'true');
          span.textContent = '…';
          pagesNav.appendChild(span);
          return;
        }
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'carousel-page';
        btn.textContent = String(tok + 1);
        btn.setAttribute('role', 'tab');
        btn.setAttribute('aria-label', `Ir para pagina ${tok + 1}`);
        if (tok === active) btn.setAttribute('aria-current', 'page');
        btn.addEventListener('click', () => goTo(tok));
        pagesNav.appendChild(btn);
      });
    }
```

Ainda dentro de `initCarousel`, logo abaixo dos listeners dos botões prev/next, adicionar teclado:

```javascript
    // Teclado: setas esquerda/direita navegam quando o carrossel recebe foco.
    root.setAttribute('tabindex', '0');
    root.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); goTo(active + 1); }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); goTo(active - 1); }
    });
```

Fora de `initCarousel`, no topo do módulo (logo abaixo de `const prefersReducedMotion = ...`), adicionar o helper:

```javascript
  /**
   * Gera tokens de paginacao compacta. Sempre inclui primeira/ultima
   * e vizinhanca (±1) da atual. Insere '…' entre saltos maiores que 1.
   * Ex: active=10, total=22 -> [0, '…', 8, 9, 10, 11, 12, '…', 21]
   *     active=1,  total=3  -> [0, 1, 2]
   */
  function buildPageTokens(active, total) {
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i);
    }
    const result = new Set([0, total - 1, active - 1, active, active + 1]);
    const pages = Array.from(result)
      .filter(i => i >= 0 && i < total)
      .sort((a, b) => a - b);
    const tokens = [];
    for (let i = 0; i < pages.length; i++) {
      if (i > 0 && pages[i] - pages[i - 1] > 1) tokens.push('…');
      tokens.push(pages[i]);
    }
    return tokens;
  }
```

- [ ] **Step 2: Adicionar efeito ripple nos botões prev/next**

Dentro de `initCarousel`, depois de `prevBtn.addEventListener(...)` e `nextBtn.addEventListener(...)`, adicionar:

```javascript
    // Ripple nos cliques dos botoes.
    [prevBtn, nextBtn].forEach(btn => {
      btn.addEventListener('click', (e) => {
        if (prefersReducedMotion || btn.disabled) return;
        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        const rect = btn.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
        ripple.style.top  = (e.clientY - rect.top  - size / 2) + 'px';
        btn.appendChild(ripple);
        setTimeout(() => ripple.remove(), 500);
      });
    });
```

- [ ] **Step 3: Verificar no browser**

Recarregar `dashboard_carbono.html`. Esperado:
- Abaixo da tabela aparece `1 2 3` (porque total < 8).
- Número ativo em cor ember com underline.
- Clicar em "3" vai direto pra página 3 com animação correta (direção forward).
- Clicar em "1" volta com animação backward.
- Com foco no carrossel (clicar na área e usar Tab até chegar nele), setas `←`/`→` navegam.
- Clicar nos botões `‹ ›` gera um pulso circular sutil (ripple).

Para testar paginação compacta com muitas páginas: em `dashboard_carbono.py`, temporariamente chamar `_render_tabela_html(df, page_size=3)` e regenerar. Com 89 empresas e page_size=3 → 30 páginas. A paginação deve aparecer como `1 … N N+1 N+2 … 30` ao navegar. Reverter o `page_size=3` para `page_size=41` depois de verificar.

- [ ] **Step 4: Commit**

```bash
git add web/js/dashboard.js
git commit -m "feat: paginacao compacta, navegacao por teclado e ripple nos botoes"
```

---

## Task 7: CSS + JS — KPI tiles (hover refinado + count-up)

**Files:**
- Modify: `web/css/style.css:358-417` (bloco `.kpi-tile`) e adicionar regras novas
- Modify: `web/js/dashboard.js` (adicionar count-up)

- [ ] **Step 1: Refinar o hover dos KPI tiles no CSS**

Em `web/css/style.css`, localizar a regra `.kpi-tile` (linha ~358) e substituir o bloco inteiro do seletor `.kpi-tile` por:

```css
.kpi-tile {
    padding: 0.5rem 1.75rem;
    border-right: 1px solid var(--hairline);
    position: relative;
    transition:
        transform 0.4s var(--ease-fluid),
        box-shadow 0.4s var(--ease-fluid);
}

.kpi-tile::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: -1px;
    height: 2px;
    background: var(--paper-whisper);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.4s var(--ease-fluid);
}

.kpi-tile[data-accent="ember"]::after { background: var(--ember); }
.kpi-tile[data-accent="slate"]::after { background: var(--slate-pale); }
.kpi-tile[data-accent="amber"]::after { background: var(--amber); }
.kpi-tile[data-accent="moss"]::after  { background: var(--moss-bright); }
.kpi-tile[data-accent="paper"]::after { background: var(--paper-dim); }

.kpi-tile:hover {
    transform: translateY(-4px);
}

.kpi-tile:hover::after {
    transform: scaleX(1);
}

.kpi-tile:hover .value {
    text-shadow: 0 0 18px currentColor;
}

.kpi-tile[data-accent="ember"]:hover { box-shadow: 0 12px 32px -18px var(--ember); }
.kpi-tile[data-accent="slate"]:hover { box-shadow: 0 12px 32px -18px var(--slate); }
.kpi-tile[data-accent="amber"]:hover { box-shadow: 0 12px 32px -18px var(--amber); }
.kpi-tile[data-accent="moss"]:hover  { box-shadow: 0 12px 32px -18px var(--moss); }
.kpi-tile[data-accent="paper"]:hover { box-shadow: 0 12px 32px -18px rgba(237,232,223,0.25); }
```

Atenção: manter intactas as regras seguintes (`.kpi-tile:first-child`, `.kpi-tile:last-child`, `.kpi-tile .label`, `.kpi-tile .label::before`, `.kpi-tile[data-accent="..."] .label::before`, `.kpi-tile .value`, `.kpi-tile .value em`, `.kpi-tile .sublabel`).

- [ ] **Step 2: Adicionar count-up em `dashboard.js`**

Em `web/js/dashboard.js`, adicionar a função abaixo como um novo módulo fora de `initCarousel` (pode ser logo após `buildPageTokens`):

```javascript
  // ── Count-up de valores numericos ───────────────────────────────

  /**
   * Anima um elemento contando de 0 ate o numero final, preservando
   * prefixos (ex: "US$ ") e sufixos (ex: "M", "B"). Formatacao BR.
   */
  function animateCountUp(el, durationMs = 1400) {
    const original = el.textContent.trim();
    // Extrai o primeiro grupo numerico BR do texto (ex: "38,7", "329,1", "10").
    const match = original.match(/^([^\d-]*)(-?[\d.]+(?:,\d+)?)(.*)$/);
    if (!match) return;

    const prefix = match[1];
    const raw    = match[2];
    const suffix = match[3];

    // Converte "38,7" -> 38.7  e  "1.234,56" -> 1234.56
    const target = parseFloat(raw.replace(/\./g, '').replace(',', '.'));
    if (!isFinite(target)) return;

    const decimals = raw.includes(',') ? raw.split(',')[1].length : 0;
    const start = performance.now();

    function format(n) {
      const fixed = n.toFixed(decimals);
      const [intPart, decPart] = fixed.split('.');
      const intBr = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      return decPart != null ? `${intBr},${decPart}` : intBr;
    }

    function tick(now) {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / durationMs);
      // easeOutExpo
      const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      const value = target * eased;
      el.textContent = prefix + format(value) + suffix;
      if (t < 1) requestAnimationFrame(tick);
      else       el.textContent = original;
    }

    el.textContent = prefix + format(0) + suffix;
    requestAnimationFrame(tick);
  }

  function initCountUp() {
    if (prefersReducedMotion) return;
    const targets = document.querySelectorAll('.hero-value, .kpi-tile .value');
    if (!targets.length || !('IntersectionObserver' in window)) return;

    const obs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        animateCountUp(entry.target);
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.4 });

    targets.forEach(t => obs.observe(t));
  }
```

Em seguida, dentro de `function init()`, adicionar a chamada:

```javascript
  function init() {
    document.querySelectorAll('.data-carousel').forEach(initCarousel);
    initCountUp();
  }
```

- [ ] **Step 3: Verificar no browser**

Regenerar (`python dashboard_carbono.py`) e recarregar. Esperado:
- Ao carregar a página, o grande valor do hero ("38.718.163") conta progressivamente de 0 ao final em ~1.4s.
- Cada KPI tile (`19,7M`, `1,6M`, `17,4M`, `34`) faz o mesmo quando entra no viewport (se já estão visíveis no load, acontece imediatamente).
- Valor final exatamente igual ao original (incluindo `M`, `US$`, itálicos).
- Hover em um KPI tile: leve lift, barra colorida embaixo aparece (accent por tile), valor ganha glow na cor do accent.
- Em `prefers-reduced-motion` (Chrome DevTools → Rendering → "Emulate CSS prefers-reduced-motion: reduce"), os valores aparecem diretos sem animação.

- [ ] **Step 4: Commit**

```bash
git add web/css/style.css web/js/dashboard.js
git commit -m "feat: hover animado nos KPI tiles e count-up dos valores"
```

---

## Task 8: CSS — Rail com underline animado + chart cards refinados

**Files:**
- Modify: `web/css/style.css:216-239` (bloco `.rail a`)
- Modify: `web/css/style.css:548-577` (bloco `.chart-card`)

- [ ] **Step 1: Substituir o bloco `.rail a` (~linha 216) por versão com underline animado**

Em `web/css/style.css`, localizar e substituir o bloco:

```css
.rail a {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--paper-faint);
    text-decoration: none;
    white-space: nowrap;
    padding: 4px 0;
    border-bottom: 1px solid transparent;
    transition: color 0.25s var(--ease-fluid), border-color 0.25s var(--ease-fluid);
}

.rail a:hover {
    color: var(--paper-bright);
    border-bottom-color: var(--ember);
}
```

por:

```css
.rail a {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--paper-faint);
    text-decoration: none;
    white-space: nowrap;
    padding: 4px 0;
    position: relative;
    transition: color 0.32s var(--ease-fluid);
}

.rail a::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 1px;
    background: var(--ember);
    transform: scaleX(0);
    transform-origin: left center;
    transition: transform 0.32s var(--ease-fluid);
}

.rail a:hover,
.rail a[data-active="true"] {
    color: var(--paper-bright);
}

.rail a:hover::after,
.rail a[data-active="true"]::after {
    transform: scaleX(1);
}
```

- [ ] **Step 2: Substituir o bloco `.chart-card` (~linha 548) refinando o hover**

Localizar e substituir:

```css
.chart-card {
    background:
        linear-gradient(180deg,
            color-mix(in srgb, var(--ink-raised) 92%, transparent),
            color-mix(in srgb, var(--ink-deep) 88%, transparent));
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 24px 14px 12px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s var(--ease-fluid);
}
```

por:

```css
.chart-card {
    background:
        linear-gradient(180deg,
            color-mix(in srgb, var(--ink-raised) 92%, transparent),
            color-mix(in srgb, var(--ink-deep) 88%, transparent));
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 24px 14px 12px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    transition:
        border-color 0.3s var(--ease-fluid),
        transform 0.4s var(--ease-fluid),
        box-shadow 0.4s var(--ease-fluid);
}
```

E substituir:

```css
.chart-card:hover {
    border-color: var(--hairline-bright);
}
```

por:

```css
.chart-card:hover {
    border-color: var(--hairline-bright);
    transform: translateY(-2px);
    box-shadow: 0 14px 36px -20px rgba(0,0,0,0.55);
}
```

- [ ] **Step 3: Verificar no browser**

Recarregar. Esperado:
- Passar o mouse num item do rail: o underline cresce da esquerda pra direita (320ms) e a cor sobe para `paper-bright`.
- Passar o mouse num chart card: borda clareia, card sobe 2px, sombra aparece.
- Nenhum item do rail ainda fica destacado ao fazer scroll (isso entra na Task 9).

- [ ] **Step 4: Commit**

```bash
git add web/css/style.css
git commit -m "style: underline animado no rail e hover mais expressivo nos chart cards"
```

---

## Task 9: JS — IntersectionObserver para rail ativo + reveal dos chart cards

**Files:**
- Modify: `web/js/dashboard.js`

- [ ] **Step 1: Adicionar funções `initActiveRail` e `initChartReveal` ao módulo**

Em `web/js/dashboard.js`, abaixo da função `initCountUp`, adicionar:

```javascript
  // ── Rail ativo durante o scroll ─────────────────────────────────

  function initActiveRail() {
    const links = Array.from(document.querySelectorAll('.rail a[href^="#"]'));
    if (!links.length || !('IntersectionObserver' in window)) return;

    const byId = new Map();
    links.forEach(a => {
      const id = a.getAttribute('href').slice(1);
      const section = document.getElementById(id);
      if (section) byId.set(section, a);
    });

    const obs = new IntersectionObserver((entries) => {
      // Pega a entry mais visivel entre as que cruzam o viewport.
      const visible = entries
        .filter(e => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

      if (!visible.length) return;

      const top = visible[0].target;
      links.forEach(a => a.removeAttribute('data-active'));
      const activeLink = byId.get(top);
      if (activeLink) activeLink.setAttribute('data-active', 'true');
    }, {
      // O rail sticky fica no topo; considerar a secao ativa quando ela
      // ocupa o meio da viewport.
      rootMargin: '-35% 0px -55% 0px',
      threshold: 0,
    });

    byId.forEach((_, section) => obs.observe(section));
  }

  // ── Reveal escalonado dos chart cards ────────────────────────────

  function initChartReveal() {
    if (prefersReducedMotion) return;
    const cards = document.querySelectorAll('.chart-card');
    if (!cards.length || !('IntersectionObserver' in window)) return;

    cards.forEach(card => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(16px)';
      card.style.transition = 'opacity 0.6s var(--ease-fluid, cubic-bezier(0.2,0.8,0.2,1)), transform 0.6s var(--ease-fluid, cubic-bezier(0.2,0.8,0.2,1))';
    });

    let seen = 0;
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const delay = Math.min(seen, 4) * 80;
        seen++;
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, delay);
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.12 });

    cards.forEach(card => obs.observe(card));
  }
```

- [ ] **Step 2: Chamar as novas funções em `init`**

Ainda em `web/js/dashboard.js`, atualizar `function init()`:

```javascript
  function init() {
    document.querySelectorAll('.data-carousel').forEach(initCarousel);
    initCountUp();
    initActiveRail();
    initChartReveal();
  }
```

- [ ] **Step 3: Verificar no browser**

Recarregar a página. Esperado:
- Ao rolar a página, o item correspondente à seção atual no rail fica destacado (cor `paper-bright`, underline persistente).
- Ao mudar de seção, o destaque transita suavemente.
- Chart cards que estão fora do viewport inicial aparecem com um fade-up escalonado conforme entram (primeiro, segundo, etc. com pequenas diferenças de delay).
- Em `prefers-reduced-motion`, os cards não fazem fade-up (ficam visíveis direto — é respeitado via early return em `initChartReveal`).

Conferir em `prefers-reduced-motion`: os cards inicialmente teriam `opacity: 0`, mas como o early return em `initChartReveal` vem antes da marcação inicial, eles ficam no estado padrão (opacos e normais). Isso é o comportamento desejado.

- [ ] **Step 4: Commit**

```bash
git add web/js/dashboard.js
git commit -m "feat: rail ativo conforme scroll e reveal escalonado dos chart cards"
```

---

## Task 10: CSS — Linhas da tabela com hover intensificado

**Files:**
- Modify: `web/css/style.css:655-670` (blocos `.data-table tbody td`, `.data-table tbody tr:hover td`)

- [ ] **Step 1: Atualizar hover das linhas da tabela**

Em `web/css/style.css`, localizar e substituir:

```css
.data-table tbody td {
    padding: 11px 14px;
    border-bottom: 1px solid var(--hairline);
    vertical-align: middle;
    line-height: 1.4;
}
```

por:

```css
.data-table tbody td {
    padding: 11px 14px;
    border-bottom: 1px solid var(--hairline);
    vertical-align: middle;
    line-height: 1.4;
    transition:
        padding-left 0.22s var(--ease-fluid),
        color 0.22s var(--ease-fluid),
        background 0.22s var(--ease-fluid);
}
```

E logo depois, substituir:

```css
.data-table tbody tr:hover td {
    background: color-mix(in srgb, var(--ember) 7%, transparent);
}
```

por:

```css
.data-table tbody tr:hover td {
    background: color-mix(in srgb, var(--ember) 8%, transparent);
}

.data-table tbody tr:hover td:first-child {
    padding-left: 20px;
}

.data-table tbody tr:hover td.total {
    color: var(--ember-hot);
}
```

- [ ] **Step 2: Verificar no browser**

Recarregar. Esperado:
- Passar o mouse numa linha: fundo ganha tint ember mais forte; a primeira célula (nome da empresa) ganha um leve push à direita (14→20px); o total fica em laranja vivo `--ember-hot`.
- Transição suave (~220ms) sem "flicker".

- [ ] **Step 3: Commit**

```bash
git add web/css/style.css
git commit -m "style: hover da tabela mais expressivo (push lateral + total em ember)"
```

---

## Task 11: CSS — Overrides de impressão (@media print) para o carrossel

**Files:**
- Modify: `web/css/style.css` (adicionar no final do arquivo, antes do último `@media (prefers-reduced-motion)`)

- [ ] **Step 1: Adicionar bloco `@media print`**

Em `web/css/style.css`, adicionar no final do arquivo (após todos os outros blocos):

```css
/* ── Impressao ──────────────────────────────────────────────────── */

@media print {
    .carousel-viewport {
        height: auto !important;
        overflow: visible !important;
    }
    .carousel-slide {
        position: static !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        transform: none !important;
        page-break-inside: avoid;
        break-inside: avoid;
        margin-bottom: 1.5rem;
    }
    .carousel-controls,
    .carousel-meta {
        display: none !important;
    }
}
```

- [ ] **Step 2: Verificar impressão**

No Chrome: `Ctrl+P` (imprimir) na página. Esperado:
- Todas as N páginas do carrossel aparecem empilhadas no preview de impressão.
- Controles (`‹`, `›`, paginação) e meta "Pagina X de N..." ficam ocultos.
- Nenhuma tabela é cortada no meio entre páginas impressas (page-break respeitado).

- [ ] **Step 3: Commit**

```bash
git add web/css/style.css
git commit -m "style: @media print mostra todas as slides do carrossel para impressao"
```

---

## Task 12: Verificação final completa

**Files:** nenhum (apenas revisão).

- [ ] **Step 1: Checklist de aceitação**

Rodar `python dashboard_carbono.py` e abrir `web/html/dashboard_carbono.html`. Conferir um por um:

1. Aparecem 3 páginas do carrossel (com 89 empresas atuais). Meta diz "Pagina 1 de 3 · 41 empresas por pagina · 89 empresas no total".
2. Clicar `›` → slide 1 sai com fade+slide pra esquerda, slide 2 entra da direita, ~420ms.
3. Clicar `‹` → direção invertida.
4. Páginas `1 2 3` aparecem na navegação; ativa em cor ember com underline.
5. Seta `‹` fica disabled na página 1; `›` fica disabled na página 3.
6. Focar o carrossel (Tab) e navegar com setas `←`/`→`.
7. Hover num KPI tile: lift + glow + barra colorida embaixo.
8. Valor grande do hero e dos 4 KPI tiles contam de 0 ao valor final ao carregar a página.
9. Hover num link do rail: underline cresce da esquerda.
10. Ao rolar, a seção atual do rail fica destacada automaticamente.
11. Hover num chart card: lift de 2px e sombra.
12. Chart cards fora do viewport fazem fade-up escalonado ao aparecer.
13. Hover numa linha da tabela: fundo ember, nome desloca 6px para a direita, total muda para `ember-hot`.
14. Clique nos botões `‹ ›`: ripple circular sutil.
15. Ativar `prefers-reduced-motion` (DevTools → Rendering): troca de slides fica instantânea, count-up não roda, fade-ups não rodam. Site continua funcional.
16. `Ctrl+P`: preview mostra todas as 3 tabelas em sequência, sem controles.

- [ ] **Step 2: Stress test rápido de escala**

Em `dashboard_carbono.py`, na chamada de `_render_tabela_html` (linha 658), trocar temporariamente para `_render_tabela_html(df, page_size=3)` para simular 30 páginas. Regenerar e confirmar:

- Paginação compacta: `‹ 1 … 14 15 16 … 30 ›` quando na página 15.
- Clicar no "30" vai direto para a última com direção forward.
- Clicar no "1" volta com direção backward.

Reverter para `_render_tabela_html(df)` (page_size default 41). Regenerar.

- [ ] **Step 3: Confirmar que não há erros no console**

DevTools → Console: esperado zero erros vermelhos. Um único `console.debug` "[BBCarbono] dashboard.js carregado" é aceitável (pode ser removido se preferir ruído zero, mas não é obrigatório).

- [ ] **Step 4: Commit final (se houve ajuste no stress test)**

Se nada mudou após o stress test, pular. Caso contrário:

```bash
git add -u
git commit -m "chore: verificacao final do carrossel e animacoes"
```

---

## Resumo de commits esperados

1. `feat: adiciona stub dashboard.js e carrega no template HTML`
2. `feat: pagina tabela completa em chunks de 41 empresas (carrossel)`
3. `style: adiciona layout base do carrossel (slides empilhadas com fade+slide)`
4. `style: adiciona controles do carrossel (botoes, paginacao, meta)`
5. `feat: implementa troca de slides do carrossel com transicao fade+slide`
6. `feat: paginacao compacta, navegacao por teclado e ripple nos botoes`
7. `feat: hover animado nos KPI tiles e count-up dos valores`
8. `style: underline animado no rail e hover mais expressivo nos chart cards`
9. `feat: rail ativo conforme scroll e reveal escalonado dos chart cards`
10. `style: hover da tabela mais expressivo (push lateral + total em ember)`
11. `style: @media print mostra todas as slides do carrossel para impressao`
12. `chore: verificacao final do carrossel e animacoes` (opcional)
