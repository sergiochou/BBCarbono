(function () {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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


  /**
   * Anima um elemento contando de 0 ate o numero final, preservando
   * prefixos (ex: "US$ ") e sufixos (ex: "M", "B"). Formatacao BR.
   */
  function animateCountUp(el, durationMs = 2200) {
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
      // easeInOutCubic
      const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
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

    prevBtn.addEventListener('click', () => goTo(active - 1));
    nextBtn.addEventListener('click', () => goTo(active + 1));

    // Teclado: setas esquerda/direita navegam quando o carrossel recebe foco.
    root.setAttribute('tabindex', '0');
    root.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); goTo(active + 1); }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); goTo(active - 1); }
    });

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


  function initTableSearch() {
    var toolbar = document.querySelector('.table-toolbar');
    if (!toolbar) return;

    var input      = toolbar.querySelector('.table-search-input');
    var clearBtn   = toolbar.querySelector('.table-search-clear');
    var filterBtn  = toolbar.querySelector('.filter-toggle');
    var filterPanel = document.querySelector('.filter-panel');
    if (!input) return;

    // Ambas as views e seus carousels.
    var viewDetalhada   = document.querySelector('.table-view[data-view="detalhada"]');
    var viewConsolidada = document.querySelector('.table-view[data-view="consolidada"]');

    function getActiveView() {
      if (viewConsolidada && !viewConsolidada.hidden) return 'consolidada';
      return 'detalhada';
    }

    function getActiveCarousel() {
      var view = getActiveView() === 'consolidada' ? viewConsolidada : viewDetalhada;
      return view ? view.querySelector('.data-carousel') : null;
    }

    function getAllRows() {
      var carousel = getActiveCarousel();
      return carousel ? Array.from(carousel.querySelectorAll('.data-table tbody tr')) : [];
    }

    function getThead() {
      var carousel = getActiveCarousel();
      return carousel ? carousel.querySelector('.data-table thead') : null;
    }

    function getPageSize() {
      var carousel = getActiveCarousel();
      return carousel ? (parseInt(carousel.getAttribute('data-page-size'), 10) || 41) : 41;
    }

    // Controles do painel de filtros.
    var sortCol     = document.getElementById('sort-column');
    var sortDirBtns = filterPanel ? Array.from(filterPanel.querySelectorAll('.sort-dir-btn')) : [];
    var ufList      = document.getElementById('filter-uf-list');
    var anoList     = document.getElementById('filter-ano-list');
    var filterComp  = document.getElementById('filter-compensa');
    var filterNZ    = document.getElementById('filter-netzero');
    var applyBtn    = filterPanel ? filterPanel.querySelector('.filter-apply') : null;
    var resetBtn    = filterPanel ? filterPanel.querySelector('.filter-reset') : null;
    var badge       = toolbar.querySelector('.filter-badge');

    var sortDirection = 'asc';
    var filtersActive = false;

    // Indice de colunas no <tr> (mesmo para ambas as views):
    // 0=empresa, 1=uf, 2=ano|inventarios, 3=escopo1, 4=escopo2, 5=escopo3,
    // 6=total, 7=creditos, 8=custo, 9=compensa, 10=netzero
    var colIndex = {
      empresa: 0, uf: 1, ano: 2, inventarios: 2, escopo1: 3, escopo2: 4,
      escopo3: 5, total: 6, creditos: 7, custo: 8
    };

    function numVal(td) {
      var txt = td.textContent.replace(/[^\d.,-]/g, '');
      return parseFloat(txt.replace(/\./g, '').replace(',', '.')) || 0;
    }

    function normalize(s) {
      return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    }

    if (filterBtn && filterPanel) {
      filterBtn.addEventListener('click', function () {
        var open = filterPanel.hidden;
        filterPanel.hidden = !open;
        filterBtn.setAttribute('aria-expanded', String(open));
      });
    }

    sortDirBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        sortDirBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        sortDirection = btn.getAttribute('data-dir');
      });
    });

    if (filterPanel) {
      filterPanel.querySelectorAll('.filter-section').forEach(function (section) {
        var grid = section.querySelector('.filter-uf-grid');
        if (!grid) return;
        section.querySelectorAll('.filter-link').forEach(function (link) {
          link.addEventListener('click', function () {
            var action = link.getAttribute('data-action');
            grid.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
              cb.checked = action === 'check-all';
            });
          });
        });
      });
    }

    var filterContainerMap = {};
    var noResElMap         = {};
    var filteredRows       = [];
    var filterPage         = 0;

    function getFilterState(viewKey) {
      if (!filterContainerMap[viewKey]) {
        var container = document.createElement('div');
        container.className = 'filter-results';
        container.style.display = 'none';

        var tableWrap = document.createElement('div');
        tableWrap.className = 'data-table-wrap';
        var tbl = document.createElement('table');
        tbl.className = 'data-table';
        var thead = getThead();
        if (thead) tbl.appendChild(thead.cloneNode(true));
        var tbody = document.createElement('tbody');
        tbl.appendChild(tbody);
        tableWrap.appendChild(tbl);

        var controls = document.createElement('div');
        controls.className = 'carousel-controls';

        var meta = document.createElement('div');
        meta.className = 'carousel-meta';

        container.appendChild(tableWrap);
        container.appendChild(controls);
        container.appendChild(meta);

        var noRes = document.createElement('div');
        noRes.className = 'table-search-no-results';
        noRes.textContent = 'Nenhuma empresa encontrada';
        noRes.style.display = 'none';

        var carousel = getActiveCarousel();
        if (carousel) {
          carousel.parentNode.insertBefore(container, carousel.nextSibling);
          carousel.parentNode.insertBefore(noRes, container.nextSibling);
        }

        filterContainerMap[viewKey] = { container: container, tableWrap: tableWrap, tbody: tbody, controls: controls, meta: meta };
        noResElMap[viewKey] = noRes;
      }
      return filterContainerMap[viewKey];
    }

    function renderFilterPage() {
      var viewKey = getActiveView();
      var state = getFilterState(viewKey);
      var pageSize = getPageSize();
      state.tbody.innerHTML = '';

      var start = filterPage * pageSize;
      var end = Math.min(start + pageSize, filteredRows.length);
      for (var i = start; i < end; i++) {
        state.tbody.appendChild(filteredRows[i].cloneNode(true));
      }

      var totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));

      state.controls.innerHTML = '';
      var prevBtn = document.createElement('button');
      prevBtn.className = 'carousel-btn prev';
      prevBtn.type = 'button';
      prevBtn.textContent = '\u2039';
      prevBtn.disabled = filterPage === 0;
      prevBtn.addEventListener('click', function () {
        if (filterPage > 0) { filterPage--; renderFilterPage(); }
      });

      var nextBtn = document.createElement('button');
      nextBtn.className = 'carousel-btn next';
      nextBtn.type = 'button';
      nextBtn.textContent = '\u203A';
      nextBtn.disabled = filterPage >= totalPages - 1;
      nextBtn.addEventListener('click', function () {
        if (filterPage < totalPages - 1) { filterPage++; renderFilterPage(); }
      });

      var pagesNav = document.createElement('nav');
      pagesNav.className = 'carousel-pages';
      pagesNav.setAttribute('role', 'tablist');

      var tokens = buildPageTokens(filterPage, totalPages);
      tokens.forEach(function (tok) {
        if (tok === '\u2026') {
          var span = document.createElement('span');
          span.className = 'carousel-ellipsis';
          span.textContent = '\u2026';
          pagesNav.appendChild(span);
          return;
        }
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'carousel-page';
        btn.textContent = String(tok + 1);
        if (tok === filterPage) btn.setAttribute('aria-current', 'page');
        btn.addEventListener('click', function () {
          filterPage = tok;
          renderFilterPage();
        });
        pagesNav.appendChild(btn);
      });

      state.controls.appendChild(prevBtn);
      state.controls.appendChild(pagesNav);
      state.controls.appendChild(nextBtn);

      state.meta.innerHTML =
        'Pagina <strong>' + (filterPage + 1) + '</strong> de <strong>' + totalPages + '</strong>' +
        ' &middot; ' + pageSize + ' registros por pagina' +
        ' &middot; ' + filteredRows.length + ' resultados';
    }

    function checkboxFilterActive(list) {
      if (!list) return false;
      var all = list.querySelectorAll('input[type="checkbox"]');
      var checked = list.querySelectorAll('input[type="checkbox"]:checked');
      return checked.length < all.length;
    }

    function countActiveFilters() {
      var isConsolidada = getActiveView() === 'consolidada';
      var n = 0;
      if (sortCol && sortCol.value) n++;
      if (filterComp && filterComp.value) n++;
      if (filterNZ && filterNZ.value) n++;
      if (checkboxFilterActive(ufList)) n++;
      if (!isConsolidada && checkboxFilterActive(anoList)) n++;
      return n;
    }

    function updateBadge() {
      var n = countActiveFilters();
      if (badge) {
        badge.hidden = n === 0;
        badge.textContent = String(n);
      }
      filtersActive = n > 0;
    }

    function applyAll() {
      var q = normalize(input.value.trim());
      var isConsolidada = getActiveView() === 'consolidada';
      var allRows = getAllRows();
      var carousel = getActiveCarousel();
      var pageSize = getPageSize();
      clearBtn.hidden = !q;
      updateBadge();

      var needsCustomView = q || filtersActive;

      if (!needsCustomView) {
        if (carousel) carousel.style.display = '';
        // Esconde containers de filtro de ambas as views.
        Object.keys(filterContainerMap).forEach(function (k) {
          filterContainerMap[k].container.style.display = 'none';
        });
        Object.keys(noResElMap).forEach(function (k) {
          noResElMap[k].style.display = 'none';
        });
        return;
      }

      // Coleta UFs permitidas.
      var allowedUFs = null;
      if (checkboxFilterActive(ufList)) {
        allowedUFs = new Set();
        ufList.querySelectorAll('input[type="checkbox"]:checked').forEach(function (cb) {
          allowedUFs.add(cb.value);
        });
      }

      // Coleta anos permitidos (apenas na detalhada).
      var allowedAnos = null;
      if (!isConsolidada && checkboxFilterActive(anoList)) {
        allowedAnos = new Set();
        anoList.querySelectorAll('input[type="checkbox"]:checked').forEach(function (cb) {
          allowedAnos.add(cb.value);
        });
      }

      var compVal = filterComp ? filterComp.value : '';
      var nzVal   = filterNZ ? filterNZ.value : '';

      // Filtra linhas.
      var filtered = allRows.filter(function (row) {
        var cells = row.children;

        if (q) {
          var name = normalize(cells[0].textContent);
          if (name.indexOf(q) === -1) return false;
        }

        if (allowedUFs) {
          var uf = cells[1].textContent.trim();
          if (!allowedUFs.has(uf)) return false;
        }

        if (allowedAnos) {
          var ano = cells[2].textContent.trim();
          if (!allowedAnos.has(ano)) return false;
        }

        if (compVal === 'sim') {
          if (cells[9].querySelector('.tag-yes') === null) return false;
        } else if (compVal === 'nao') {
          if (cells[9].querySelector('.tag-yes') !== null) return false;
        }

        if (nzVal === 'sim') {
          if (cells[10].querySelector('.nz-year') === null) return false;
        } else if (nzVal === 'nao') {
          if (cells[10].querySelector('.nz-year') !== null) return false;
        }

        return true;
      });

      // Ordenacao.
      var sortKey = sortCol ? sortCol.value : '';
      if (sortKey && colIndex[sortKey] !== undefined) {
        var idx = colIndex[sortKey];
        var isNum = idx >= 2;
        var dir = sortDirection === 'desc' ? -1 : 1;

        filtered.sort(function (a, b) {
          var va, vb;
          if (isNum) {
            va = numVal(a.children[idx]);
            vb = numVal(b.children[idx]);
          } else {
            va = normalize(a.children[idx].textContent);
            vb = normalize(b.children[idx].textContent);
          }
          if (va < vb) return -1 * dir;
          if (va > vb) return 1 * dir;
          return 0;
        });
      }

      // Renderiza com paginacao.
      var viewKey = getActiveView();
      getFilterState(viewKey);
      filteredRows = filtered;
      filterPage = 0;

      if (carousel) carousel.style.display = 'none';
      var state = filterContainerMap[viewKey];
      var noRes = noResElMap[viewKey];
      if (filtered.length) {
        state.container.style.display = '';
        if (noRes) noRes.style.display = 'none';
        renderFilterPage();
      } else {
        state.container.style.display = 'none';
        if (noRes) noRes.style.display = '';
      }
    }

    // Expor applyAll para o toggle poder resetar filtros ao trocar view.
    window._tableApplyAll = applyAll;

    var timer;
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(applyAll, 150);
    });

    clearBtn.addEventListener('click', function () {
      input.value = '';
      applyAll();
      input.focus();
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        input.value = '';
        applyAll();
      }
    });

    if (applyBtn) {
      applyBtn.addEventListener('click', function () {
        applyAll();
        filterPanel.hidden = true;
        filterBtn.setAttribute('aria-expanded', 'false');
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        if (sortCol) sortCol.value = '';
        if (filterComp) filterComp.value = '';
        if (filterNZ) filterNZ.value = '';
        sortDirBtns.forEach(function (b) {
          b.classList.toggle('active', b.getAttribute('data-dir') === 'asc');
        });
        sortDirection = 'asc';
        [ufList, anoList].forEach(function (list) {
          if (!list) return;
          list.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
            cb.checked = true;
          });
        });
        applyAll();
      });
    }
  }


  function initTableViewToggle() {
    var toggleContainer = document.querySelector('.table-view-toggle');
    if (!toggleContainer) return;

    var buttons = Array.from(toggleContainer.querySelectorAll('.view-btn'));
    var views = Array.from(document.querySelectorAll('.table-view'));

    // Elementos que devem sumir na consolidada.
    var anoOnlyEls = document.querySelectorAll('[data-only-view="detalhada"]');
    var consolOnlyEls = document.querySelectorAll('[data-only-view="consolidada"]');

    // Option "Ano" no sort select.
    var sortCol = document.getElementById('sort-column');
    var anoOption = sortCol ? sortCol.querySelector('option[value="ano"]') : null;
    var invOption = sortCol ? sortCol.querySelector('option[value="inventarios"]') : null;

    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var target = btn.getAttribute('data-view');
        var isConsolidada = target === 'consolidada';

        buttons.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');

        // Mostra/esconde views.
        views.forEach(function (v) {
          var isTarget = v.getAttribute('data-view') === target;
          v.hidden = !isTarget;

          if (isTarget) {
            var carousel = v.querySelector('.data-carousel');
            if (carousel) {
              carousel.style.display = '';
              if (carousel._carousel) {
                requestAnimationFrame(function () {
                  var activeSlide = carousel.querySelectorAll('.carousel-slide')[carousel._carousel.getActive()];
                  if (activeSlide) {
                    var viewport = carousel.querySelector('.carousel-viewport');
                    if (viewport) viewport.style.height = activeSlide.getBoundingClientRect().height + 'px';
                  }
                });
              }
            }
          }
        });

        // Esconde/mostra elementos exclusivos de cada view.
        anoOnlyEls.forEach(function (el) {
          if (el.tagName === 'OPTION') {
            el.disabled = isConsolidada;
            el.hidden = isConsolidada;
          } else {
            el.hidden = isConsolidada;
          }
        });
        consolOnlyEls.forEach(function (el) {
          if (el.tagName === 'OPTION') {
            el.disabled = !isConsolidada;
            el.hidden = !isConsolidada;
          } else {
            el.hidden = !isConsolidada;
          }
        });

        // Se sort estava em "ano" e trocou pra consolidada, reseta.
        if (isConsolidada && sortCol && sortCol.value === 'ano') {
          sortCol.value = '';
        }
        if (!isConsolidada && sortCol && sortCol.value === 'inventarios') {
          sortCol.value = '';
        }

        // Esconde resultados de filtro da view anterior.
        document.querySelectorAll('.filter-results').forEach(function (el) {
          el.style.display = 'none';
        });
        document.querySelectorAll('.table-search-no-results').forEach(function (el) {
          el.style.display = 'none';
        });

        // Re-aplica filtros na nova view.
        if (window._tableApplyAll) window._tableApplyAll();

        // Scroll ate o toggle.
        toggleContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }


  function init() {
    document.querySelectorAll('.data-carousel').forEach(initCarousel);
    initTableSearch();
    initTableViewToggle();
    initCountUp();
    initActiveRail();
    initChartReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
