"""
dashboard_carbono.py
====================
Gera um dashboard interativo em HTML com graficos de emissoes de carbono
e estimativa de creditos de carbono para cada empresa.

Le os dados filtrados de JSON_Filtrados_Carbono/ e produz o arquivo
web/html/dashboard_carbono.html (o estilo fica em web/css/style.css).

Uso:
    python dashboard_carbono.py
"""

import html as _html
import json
import logging
import math
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

PASTA_ENTRADA = Path("JSON_Filtrados_Carbono")
PASTA_WEB = Path("web")
ARQUIVO_SAIDA = PASTA_WEB / "html" / "dashboard_carbono.html"
CAMINHO_CSS = "../css/style.css"
CAMINHO_JS = "../js/dashboard.js"

# Preco medio do credito de carbono no mercado voluntario brasileiro (USD)
# Fonte: estimativa conservadora do mercado voluntario 2023-2024
PRECO_CREDITO_USD = 8.50
# 1 credito de carbono = 1 tCO2e

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paleta editorial (espelha o CSS em web/css/style.css) ───────────────

COR_ESCOPO1 = "#e2b84d"   # Gold   — emissoes diretas
COR_ESCOPO2 = "#5d8fc9"   # Azure  — energia eletrica
COR_ESCOPO3 = "#8ab4e0"   # Ice    — cadeia de valor
COR_TOTAL   = "#f0ca65"   # Gold-bright — total consolidado
COR_CREDITO = "#3a6ea5"   # Steel  — contrapartida financeira

COR_PAPEL        = "#e0dff0"
COR_PAPEL_BRIGHT = "#f0eff6"
COR_PAPEL_DIM    = "#8a92a8"
COR_PAPEL_FAINT  = "#5a6580"

COR_INK_RAISED   = "#111d33"
COR_INK_ELEVATED = "#162640"
COR_INK_DEEP     = "#0c1526"
COR_HAIRLINE        = "rgba(224,223,240,0.07)"
COR_HAIRLINE_BRIGHT = "rgba(224,223,240,0.18)"

FONTE_DISPLAY = "Fraunces, Georgia, serif"
FONTE_BODY    = "Geist, Helvetica Neue, system-ui, sans-serif"
FONTE_MONO    = "JetBrains Mono, Courier New, monospace"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "responsive": True,
}

def _registrar_tema_plotly() -> None:
    """Registra um template escuro editorial alinhado ao CSS."""
    eixo = dict(
        gridcolor=COR_HAIRLINE,
        linecolor=COR_HAIRLINE_BRIGHT,
        tickcolor=COR_HAIRLINE_BRIGHT,
        zerolinecolor=COR_HAIRLINE_BRIGHT,
        tickfont=dict(family=FONTE_MONO, size=10.5, color=COR_PAPEL_DIM),
        title=dict(font=dict(family=FONTE_MONO, size=11, color=COR_PAPEL_FAINT)),
        zeroline=False,
        automargin=True,
    )

    pio.templates["bbcarbono"] = go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONTE_BODY, color=COR_PAPEL, size=12),
            title=dict(
                font=dict(family=FONTE_DISPLAY, size=19, color=COR_PAPEL_BRIGHT),
                x=0.01, xanchor="left",
                y=0.97, yanchor="top",
                pad=dict(l=4, t=10, b=14),
            ),
            xaxis=eixo,
            yaxis=eixo,
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(0,0,0,0)",
                font=dict(family=FONTE_MONO, size=10, color=COR_PAPEL_DIM),
            ),
            hoverlabel=dict(
                bgcolor=COR_INK_ELEVATED,
                bordercolor=COR_HAIRLINE_BRIGHT,
                font=dict(family=FONTE_MONO, size=11, color=COR_PAPEL_BRIGHT),
            ),
            colorway=[COR_ESCOPO1, COR_ESCOPO3, COR_ESCOPO2, COR_TOTAL, COR_CREDITO],
            margin=dict(l=60, r=30, t=80, b=55),
        )
    )
    pio.templates.default = "bbcarbono"


def carregar_dados() -> pd.DataFrame:
    """Carrega todos os lotes filtrados e retorna um DataFrame.

    Cada inventario (ano) de cada empresa vira uma linha separada.
    Projetos e metas sao copiados para todas as linhas da empresa.
    """
    registros = []

    for arquivo in sorted(PASTA_ENTRADA.glob("lote_filtrado_*.json")):
        with open(arquivo, "r", encoding="utf-8") as f:
            lote = json.load(f)

        for emp in lote:
            dc = emp.get("dados_carbono", {})
            if dc.get("status") not in ("sucesso", "parcial"):
                continue

            nome = emp.get("nome_oficial", emp.get("empresa_pasta", "?"))
            estado = emp.get("estado", "??")
            tem_projeto = len(dc.get("projetos_carbono", [])) > 0
            projetos_str = ", ".join(dc.get("projetos_carbono", []))
            meta_nz = dc.get("metas_net_zero", {}).get("ano") if dc.get("metas_net_zero") else None

            inventarios = dc.get("inventarios", [])
            for inv in inventarios:
                if inv.get("status") != "sucesso":
                    continue
                registros.append({
                    "empresa": nome,
                    "estado": estado,
                    "setor": inv.get("setor_economico") or "Não informado",
                    "escopo_1": inv.get("emissoes_escopo_1") or 0,
                    "escopo_2": inv.get("emissoes_escopo_2") or 0,
                    "escopo_3": inv.get("emissoes_escopo_3") or 0,
                    "total": inv.get("total_emissoes") or 0,
                    "ano": inv.get("ano_inventario"),
                    "pdf_origem": inv.get("pdf_origem", ""),
                    "tem_projeto_compensacao": tem_projeto,
                    "projetos_carbono": projetos_str,
                    "meta_net_zero": meta_nz,
                })

    df = pd.DataFrame(registros)
    df["creditos_necessarios"] = df["total"]  # 1 credito = 1 tCO2e
    df["custo_compensacao_usd"] = df["total"] * PRECO_CREDITO_USD
    df.sort_values(["empresa", "ano"], ascending=[True, False], inplace=True, ignore_index=True)

    n_empresas = df["empresa"].nunique() if len(df) else 0
    logger.info(f"Carregados {len(df)} inventarios de {n_empresas} empresas.")
    return df


def fmt_br(valor: float, casas: int = 0) -> str:
    """Formata numero no padrao brasileiro (1.234.567,89)."""
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_compacto(valor: float) -> str:
    """Formata numero como 1,2M / 345k / 89 (pt-BR)."""
    abs_v = abs(valor)
    if abs_v >= 1_000_000:
        return fmt_br(valor / 1_000_000, 1) + "M"
    if abs_v >= 1_000:
        return fmt_br(valor / 1_000, 1) + "k"
    return fmt_br(valor, 0)


def grafico_top_emissores(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Barras horizontais empilhadas: top N empresas por emissao total."""
    top = df.head(top_n).iloc[::-1]  # maior no topo

    escopos = [
        ("escopo_1", "Escopo 1 · Diretas", COR_ESCOPO1),
        ("escopo_2", "Escopo 2 · Energia", COR_ESCOPO2),
        ("escopo_3", "Escopo 3 · Cadeia",  COR_ESCOPO3),
    ]

    fig = go.Figure()
    for coluna, nome, cor in escopos:
        fig.add_trace(go.Bar(
            y=top["empresa"], x=top[coluna], name=nome,
            orientation="h",
            marker=dict(color=cor, line=dict(width=0)),
            hovertemplate=f"<b>%{{y}}</b><br>{nome}<br>%{{x:,.0f}} tCO₂e<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        bargap=0.35,
        title=f"Top {top_n} Maiores Emissores · Média Anual tCO₂e por Escopo",
        xaxis_title="Média anual de emissões (tCO₂e)",
        height=720,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left"),
        margin=dict(l=260, r=30, t=90, b=60),
    )
    return fig


def grafico_creditos_carbono(df: pd.DataFrame, top_n: int = 25) -> go.Figure:
    """Barras: creditos necessarios e custo estimado de compensacao."""
    top = df.head(top_n)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "Créditos necessários · média anual tCO₂e",
            f"Custo estimado anual · USD {fmt_br(PRECO_CREDITO_USD, 2)}/tCO₂e",
        ),
        horizontal_spacing=0.14,
    )

    fig.add_trace(go.Bar(
        x=top["empresa"], y=top["creditos_necessarios"],
        marker=dict(color=COR_ESCOPO3, line=dict(width=0)),
        name="Créditos",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} créditos/ano<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=top["empresa"], y=top["custo_compensacao_usd"],
        marker=dict(color=COR_CREDITO, line=dict(width=0)),
        name="Custo USD",
        hovertemplate="<b>%{x}</b><br>USD %{y:,.0f}<extra></extra>",
    ), row=1, col=2)

    fig.update_annotations(
        font=dict(family=FONTE_MONO, size=11, color=COR_PAPEL_DIM),
    )
    fig.update_layout(
        title=f"Contrapartida Financeira Anual · Top {top_n}",
        height=560,
        showlegend=False,
        bargap=0.3,
    )
    fig.update_xaxes(tickangle=-45)
    return fig


def grafico_distribuicao_escopos(df: pd.DataFrame) -> go.Figure:
    """Donut: proporcao agregada de cada escopo no total geral."""
    totais = [df["escopo_1"].sum(), df["escopo_2"].sum(), df["escopo_3"].sum()]
    labels = ["Escopo 1 · Diretas", "Escopo 2 · Energia", "Escopo 3 · Cadeia"]
    cores = [COR_ESCOPO1, COR_ESCOPO2, COR_ESCOPO3]

    fig = go.Figure(go.Pie(
        labels=labels, values=totais,
        hole=0.62,
        marker=dict(colors=cores, line=dict(color=COR_INK_DEEP, width=2)),
        textinfo="percent",
        textfont=dict(family=FONTE_DISPLAY, size=20, color=COR_PAPEL_BRIGHT),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} tCO₂e<br>%{percent}<extra></extra>",
        sort=False,
    ))

    fig.update_layout(
        title="Distribuição por Escopo · Média Anual",
        height=460,
        legend=dict(orientation="h", yanchor="top", y=-0.05, x=0.5, xanchor="center"),
        margin=dict(l=30, r=30, t=80, b=80),
        annotations=[dict(
            text=f"<b>{fmt_compacto(sum(totais))}</b><br><span style='font-size:11px;color:{COR_PAPEL_FAINT};letter-spacing:0.2em'>TCO₂E/ANO</span>",
            showarrow=False, x=0.5, y=0.5,
            font=dict(family=FONTE_DISPLAY, size=34, color=COR_PAPEL_BRIGHT),
        )],
    )
    return fig


def grafico_por_estado(df: pd.DataFrame) -> go.Figure:
    """Barras empilhadas por estado."""
    por_estado = df.groupby("estado")[["escopo_1", "escopo_2", "escopo_3"]].sum()
    por_estado["total"] = por_estado.sum(axis=1)
    por_estado.sort_values("total", ascending=False, inplace=True)

    fig = go.Figure()
    for coluna, nome, cor in [
        ("escopo_1", "Escopo 1", COR_ESCOPO1),
        ("escopo_2", "Escopo 2", COR_ESCOPO2),
        ("escopo_3", "Escopo 3", COR_ESCOPO3),
    ]:
        fig.add_trace(go.Bar(
            x=por_estado.index, y=por_estado[coluna],
            name=nome,
            marker=dict(color=cor, line=dict(width=0)),
            hovertemplate=f"<b>%{{x}}</b><br>{nome}: %{{y:,.0f}} tCO₂e<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        bargap=0.25,
        title="Emissões por Estado · Média Anual tCO₂e",
        xaxis_title="Unidade Federativa",
        yaxis_title="Média anual de emissões (tCO₂e)",
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left"),
    )
    return fig


def grafico_scatter_escopos(df: pd.DataFrame) -> go.Figure:
    """Scatter log-log: Escopo 1 vs Escopo 3, tamanho = Escopo 2."""
    tamanhos = df["escopo_2"].clip(lower=1).apply(lambda v: max(6, min(52, v ** 0.3 * 3.2)))

    fig = go.Figure(go.Scatter(
        x=df["escopo_1"],
        y=df["escopo_3"],
        mode="markers",
        marker=dict(
            size=tamanhos,
            color=df["total"],
            colorscale=[[0, COR_ESCOPO2], [0.5, COR_ESCOPO3], [1, COR_ESCOPO1]],
            showscale=True,
            line=dict(color=COR_INK_DEEP, width=1.2),
            opacity=0.88,
            colorbar=dict(
                title=dict(text="Média anual tCO₂e", font=dict(family=FONTE_MONO, size=10, color=COR_PAPEL_DIM)),
                tickfont=dict(family=FONTE_MONO, size=10, color=COR_PAPEL_DIM),
                thickness=10,
                outlinewidth=0,
                bgcolor="rgba(0,0,0,0)",
            ),
        ),
        text=df["empresa"],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Escopo 1: %{x:,.0f} tCO₂e<br>"
            "Escopo 3: %{y:,.0f} tCO₂e<br>"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        title="Correlação entre Escopos · Média Anual · Log-log",
        xaxis_title="Escopo 1 · Diretas (log · média anual tCO₂e)",
        yaxis_title="Escopo 3 · Cadeia de valor (log · média anual tCO₂e)",
        height=560,
    )
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return fig


def grafico_compensacao_status(df: pd.DataFrame) -> go.Figure:
    """Barras: empresas com vs sem projetos de compensacao."""
    com = df[df["tem_projeto_compensacao"]]
    sem = df[~df["tem_projeto_compensacao"]]

    media_com = com["total"].mean() if len(com) > 0 else 0
    media_sem = sem["total"].mean() if len(sem) > 0 else 0

    fig = go.Figure(go.Bar(
        x=["Com projeto", "Sem projeto"],
        y=[len(com), len(sem)],
        marker=dict(
            color=[COR_TOTAL, COR_ESCOPO1],
            line=dict(width=0),
        ),
        text=[len(com), len(sem)],
        textposition="outside",
        textfont=dict(family=FONTE_DISPLAY, size=28, color=COR_PAPEL_BRIGHT),
        hovertemplate="<b>%{x}</b><br>%{y} empresas<extra></extra>",
        width=[0.52, 0.52],
    ))

    fig.add_annotation(
        x="Com projeto", y=len(com),
        text=f"média: {fmt_br(media_com)} tCO₂e",
        showarrow=False, yshift=45,
        font=dict(family=FONTE_MONO, size=10, color=COR_PAPEL_FAINT),
    )
    fig.add_annotation(
        x="Sem projeto", y=len(sem),
        text=f"média: {fmt_br(media_sem)} tCO₂e",
        showarrow=False, yshift=45,
        font=dict(family=FONTE_MONO, size=10, color=COR_PAPEL_FAINT),
    )

    fig.update_layout(
        title="Empresas com Compensação de Carbono",
        yaxis_title="Quantidade de empresas",
        height=440,
        showlegend=False,
        margin=dict(l=60, r=30, t=90, b=80),
    )
    return fig


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
        '<th class="num">Ano</th>'
        '<th class="num">Escopo 1</th>'
        '<th class="num">Escopo 2</th>'
        '<th class="num">Escopo 3</th>'
        '<th class="num">Total tCO₂e</th>'
        '<th class="num">Créditos</th>'
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
            ano_str = str(int(r["ano"])) if pd.notna(r["ano"]) else "—"
            linhas.append(
                '<tr>'
                f'<td class="empresa">{_html.escape(str(r["empresa"]).strip())}</td>'
                f'<td class="uf">{_html.escape(str(r["estado"]))}</td>'
                f'<td class="num ano">{ano_str}</td>'
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
        <button class="carousel-btn prev" type="button" aria-label="Página anterior" disabled>‹</button>
        <nav class="carousel-pages" role="tablist" aria-label="Selecionar página"></nav>
        <button class="carousel-btn next" type="button" aria-label="Próxima página">›</button>
      </div>
      <div class="carousel-meta">
        Página <strong class="carousel-current">1</strong> de <strong>{n_pages}</strong>
        &nbsp;·&nbsp; {page_size} inventários por página
        &nbsp;·&nbsp; {total} inventários no total
      </div>
    </div>
    """


def _render_tabela_consolidada_html(df: pd.DataFrame, page_size: int = 41) -> str:
    """Tabela consolidada: uma linha por empresa, emissoes somadas."""
    df_dedup = df.drop_duplicates(subset=["empresa", "ano"], keep="first")
    agg = df_dedup.groupby("empresa", sort=False).agg(
        estado=("estado", "first"),
        escopo_1=("escopo_1", "sum"),
        escopo_2=("escopo_2", "sum"),
        escopo_3=("escopo_3", "sum"),
        total=("total", "sum"),
        n_inventarios=("ano", "count"),
        tem_projeto_compensacao=("tem_projeto_compensacao", "first"),
        meta_net_zero=("meta_net_zero", "first"),
    ).reset_index()
    agg["creditos_necessarios"] = agg["total"]
    agg["custo_compensacao_usd"] = agg["total"] * PRECO_CREDITO_USD
    agg = agg.sort_values("total", ascending=False, ignore_index=True)

    total = len(agg)
    n_pages = max(1, math.ceil(total / page_size))

    thead_html = (
        '<thead>'
        '<tr>'
        '<th class="th-empresa">Empresa</th>'
        '<th class="th-uf">UF</th>'
        '<th class="num">Inventários</th>'
        '<th class="num">Escopo 1</th>'
        '<th class="num">Escopo 2</th>'
        '<th class="num">Escopo 3</th>'
        '<th class="num">Total tCO₂e</th>'
        '<th class="num">Créditos</th>'
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
        chunk = agg.iloc[inicio:fim]

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
                f'<td class="num ano">{int(r["n_inventarios"])}</td>'
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
         role="region" aria-label="Registro consolidado de empresas, paginado">
      <div class="carousel-viewport">
        <div class="carousel-track">
          {''.join(slides)}
        </div>
      </div>
      <div class="carousel-controls">
        <button class="carousel-btn prev" type="button" aria-label="Página anterior" disabled>‹</button>
        <nav class="carousel-pages" role="tablist" aria-label="Selecionar página"></nav>
        <button class="carousel-btn next" type="button" aria-label="Próxima página">›</button>
      </div>
      <div class="carousel-meta">
        Página <strong class="carousel-current">1</strong> de <strong>{n_pages}</strong>
        &nbsp;·&nbsp; {page_size} empresas por página
        &nbsp;·&nbsp; {total} empresas no total
      </div>
    </div>
    """


def _render_tabelas_section(df: pd.DataFrame) -> str:
    """Renderiza ambas as tabelas com toolbar compartilhada e toggle."""
    tabela_detalhada = _render_tabela_html(df)
    tabela_consolidada = _render_tabela_consolidada_html(df)

    ufs_sorted = sorted(df["estado"].dropna().unique())
    uf_checks = "\n".join(
        f'<label class="filter-check">'
        f'<input type="checkbox" value="{_html.escape(str(uf))}" checked />'
        f'<span>{_html.escape(str(uf))}</span>'
        f'</label>'
        for uf in ufs_sorted
    )

    anos_sorted = sorted(df["ano"].dropna().unique(), reverse=True)
    ano_checks = "\n".join(
        f'<label class="filter-check">'
        f'<input type="checkbox" value="{int(a)}" checked />'
        f'<span>{int(a)}</span>'
        f'</label>'
        for a in anos_sorted
    )

    return f"""
    <div class="table-view-toggle">
      <button class="view-btn active" type="button" data-view="detalhada">Por inventário</button>
      <button class="view-btn" type="button" data-view="consolidada">Consolidada</button>
    </div>

    <div class="table-toolbar">
      <div class="table-search">
        <svg class="table-search-icon" viewBox="0 0 24 24" width="18" height="18"
             fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input class="table-search-input" type="text"
               placeholder="Pesquisar empresa..."
               aria-label="Pesquisar empresa pelo nome"
               autocomplete="off" spellcheck="false" />
        <button class="table-search-clear" type="button"
                aria-label="Limpar pesquisa" hidden>
          <svg viewBox="0 0 24 24" width="16" height="16"
               fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <button class="filter-toggle" type="button" aria-label="Filtros e ordenação">
        <svg viewBox="0 0 24 24" width="18" height="18"
             fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="6" x2="20" y2="6"/>
          <line x1="7" y1="12" x2="17" y2="12"/>
          <line x1="10" y1="18" x2="14" y2="18"/>
        </svg>
        <span>Filtros</span>
        <span class="filter-badge" hidden>0</span>
      </button>
    </div>

    <div class="filter-panel" hidden>
      <div class="filter-panel-inner">

        <section class="filter-section">
          <h4 class="filter-heading">Ordenar por</h4>
          <div class="filter-row">
            <select class="filter-select" id="sort-column">
              <option value="">Nenhum</option>
              <option value="empresa">Empresa</option>
              <option value="uf">UF</option>
              <option value="ano" data-only-view="detalhada">Ano</option>
              <option value="inventarios" data-only-view="consolidada" disabled hidden>Inventários</option>
              <option value="escopo1">Escopo 1</option>
              <option value="escopo2">Escopo 2</option>
              <option value="escopo3">Escopo 3</option>
              <option value="total">Total tCO&#8322;e</option>
              <option value="creditos">Créditos</option>
              <option value="custo">Custo USD</option>
            </select>
            <div class="sort-dir-group">
              <button class="sort-dir-btn active" type="button" data-dir="asc"
                      aria-label="Ordem crescente" title="Crescente">
                <svg viewBox="0 0 24 24" width="16" height="16"
                     fill="none" stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="19" x2="12" y2="5"/>
                  <polyline points="5 12 12 5 19 12"/>
                </svg>
              </button>
              <button class="sort-dir-btn" type="button" data-dir="desc"
                      aria-label="Ordem decrescente" title="Decrescente">
                <svg viewBox="0 0 24 24" width="16" height="16"
                     fill="none" stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <polyline points="19 12 12 19 5 12"/>
                </svg>
              </button>
            </div>
          </div>
        </section>

        <section class="filter-section">
          <h4 class="filter-heading">Estado (UF)</h4>
          <div class="filter-row filter-uf-actions">
            <button class="filter-link" type="button" data-action="check-all">Todos</button>
            <button class="filter-link" type="button" data-action="uncheck-all">Nenhum</button>
          </div>
          <div class="filter-uf-grid" id="filter-uf-list">
            {uf_checks}
          </div>
        </section>

        <section class="filter-section" data-only-view="detalhada">
          <h4 class="filter-heading">Ano do inventário</h4>
          <div class="filter-row filter-uf-actions">
            <button class="filter-link" type="button" data-action="check-all">Todos</button>
            <button class="filter-link" type="button" data-action="uncheck-all">Nenhum</button>
          </div>
          <div class="filter-uf-grid" id="filter-ano-list">
            {ano_checks}
          </div>
        </section>

        <section class="filter-section">
          <h4 class="filter-heading">Compensação</h4>
          <div class="filter-row">
            <select class="filter-select" id="filter-compensa">
              <option value="">Todos</option>
              <option value="sim">Apenas quem compensa</option>
              <option value="nao">Apenas quem não compensa</option>
            </select>
          </div>
        </section>

        <section class="filter-section">
          <h4 class="filter-heading">Meta Net Zero</h4>
          <div class="filter-row">
            <select class="filter-select" id="filter-netzero">
              <option value="">Todos</option>
              <option value="sim">Com meta declarada</option>
              <option value="nao">Sem meta declarada</option>
            </select>
          </div>
        </section>

        <div class="filter-actions">
          <button class="filter-apply" type="button">Aplicar filtros</button>
          <button class="filter-reset" type="button">Limpar tudo</button>
        </div>
      </div>
    </div>

    <div class="table-view" data-view="detalhada">
      {tabela_detalhada}
    </div>
    <div class="table-view" data-view="consolidada" hidden>
      {tabela_consolidada}
    </div>
    """


def _render_chart(fig: go.Figure) -> str:
    """Envolve uma figura Plotly num chart-card."""
    return (
        f'<div class="chart-card">'
        f'{fig.to_html(full_html=False, include_plotlyjs=False, config=PLOTLY_CONFIG)}'
        f'</div>'
    )


def _render_chart_grid(*figs: go.Figure) -> str:
    """Renderiza varias figuras lado a lado."""
    cards = "\n".join(
        f'<div class="chart-card">'
        f'{f.to_html(full_html=False, include_plotlyjs=False, config=PLOTLY_CONFIG)}'
        f'</div>'
        for f in figs
    )
    return f'<div class="chart-grid">{cards}</div>'


def _render_chapter(num: str, kicker: str, titulo: str, deck: str,
                    conteudo: str, anchor: str) -> str:
    return f"""
    <article class="chapter" id="{anchor}">
      <div class="chapter-head">
        <div class="chapter-num">{num}</div>
        <div>
          <div class="chapter-kicker">{kicker}</div>
          <h2 class="chapter-heading">{titulo}</h2>
          <p class="chapter-deck">{deck}</p>
        </div>
      </div>
      {conteudo}
    </article>
    """


def _render_hero(df: pd.DataFrame) -> str:
    total_geral = df["total"].sum()
    custo_total = df["custo_compensacao_usd"].sum()
    n_empresas = df["empresa"].nunique()
    n_com_projeto = int(df.drop_duplicates("empresa")["tem_projeto_compensacao"].sum())
    n_estados = df["estado"].nunique()

    return f"""
    <section class="hero" id="panorama">
      <div class="hero-main">
        <span class="hero-label">Média anual de emissões estimada</span>
        <div class="hero-value">{fmt_br(total_geral)}</div>
        <div class="hero-unit">toneladas de <strong>CO₂ equivalente</strong> &nbsp;·&nbsp; {n_empresas} empresas &nbsp;·&nbsp; {n_estados} estados</div>
      </div>
      <aside class="hero-side">
        <dl>
          <dt>Créditos necessários</dt>
          <dd>{fmt_compacto(total_geral)}<small>tCO₂e/ano</small></dd>
        </dl>
        <dl>
          <dt>Compensação estimada</dt>
          <dd>US$ {fmt_compacto(custo_total)}<small>@ {fmt_br(PRECO_CREDITO_USD, 2)}</small></dd>
        </dl>
        <dl>
          <dt>Com projeto ativo</dt>
          <dd>{n_com_projeto}<small>de {n_empresas}</small></dd>
        </dl>
      </aside>
    </section>
    """


def _render_kpi_row(df: pd.DataFrame) -> str:
    e1 = df["escopo_1"].sum()
    e2 = df["escopo_2"].sum()
    e3 = df["escopo_3"].sum()
    n_setores = df["setor"].nunique()

    return f"""
    <div class="kpi-row">
      <div class="kpi-tile" data-accent="gold">
        <div class="label">Escopo 1 · Diretas</div>
        <div class="value">{fmt_compacto(e1)}</div>
        <div class="sublabel">tCO₂e/ano · emissões próprias</div>
      </div>
      <div class="kpi-tile" data-accent="azure">
        <div class="label">Escopo 2 · Energia</div>
        <div class="value">{fmt_compacto(e2)}</div>
        <div class="sublabel">tCO₂e/ano · eletricidade comprada</div>
      </div>
      <div class="kpi-tile" data-accent="ice">
        <div class="label">Escopo 3 · Cadeia</div>
        <div class="value">{fmt_compacto(e3)}</div>
        <div class="sublabel">tCO₂e/ano · cadeia de valor</div>


              </div>
      <div class="kpi-tile" data-accent="paper">
        <div class="label">Setores cobertos</div>
        <div class="value"><em>{n_setores}</em></div>
        <div class="sublabel">ramos economicos</div>
      </div>
    </div>
    """


def _render_note() -> str:
    return f"""
    <section class="note">
      <div class="note-kicker">Metodologia</div>
      <p class="note-body">
        Cada <strong>crédito de carbono</strong> equivale a <em>1 tCO₂e</em> —
        uma tonelada de CO₂ equivalente. O custo estimado usa o preço médio do
        mercado voluntário brasileiro de <strong>USD {fmt_br(PRECO_CREDITO_USD, 2)}</strong>
        por crédito. <strong>Escopo 1</strong> refere-se a emissões diretas
        (combustão própria); <strong>Escopo 2</strong>, a eletricidade comprada;
        <strong>Escopo 3</strong>, a cadeia de valor — transporte, fornecedores
        e uso dos produtos.
      </p>
      <p class="note-body">
        <strong>Critério de agregação:</strong> para empresas com mais de um
        relatório de emissão, os valores exibidos nos gráficos representam a
        <em>média anual</em> de seus inventários. Isso garante comparação justa
        entre empresas com diferentes quantidades de relatórios históricos.
        Para dados detalhados por ano e por empresa, consulte a
        <a href="#tabela" style="color:#e2b84d;text-decoration:underline;text-underline-offset:3px">tabela completa na seção §05 Registro</a>.
      </p>
    </section>
    """


def _agregar_por_empresa(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a media anual de emissoes por empresa.

    Deduplica por (empresa, ano) antes de calcular para evitar contar o
    mesmo inventario duas vezes quando multiplos PDFs cobrem o mesmo ano.
    Usa media (nao soma) para comparacao justa entre empresas com
    quantidades diferentes de relatorios.
    """
    df_dedup = df.drop_duplicates(subset=["empresa", "ano"], keep="first")

    numericas = df_dedup.groupby("empresa", sort=False).agg(
        escopo_1=("escopo_1", "mean"),
        escopo_2=("escopo_2", "mean"),
        escopo_3=("escopo_3", "mean"),
        total=("total", "mean"),
        n_inventarios=("ano", "count"),
    ).reset_index()

    meta_cols = ["empresa", "estado", "setor",
                 "tem_projeto_compensacao", "projetos_carbono", "meta_net_zero"]
    metadata = (
        df_dedup.drop_duplicates(subset="empresa", keep="first")[meta_cols]
    )

    result = numericas.merge(metadata, on="empresa")
    result["creditos_necessarios"] = result["total"]
    result["custo_compensacao_usd"] = result["total"] * PRECO_CREDITO_USD
    result = result.sort_values("total", ascending=False, ignore_index=True)
    return result


def montar_dashboard(df: pd.DataFrame) -> str:
    """Gera o HTML completo do dashboard combinando todos os graficos."""

    df_recente = _agregar_por_empresa(df)

    capitulos = [
        _render_chapter(
            num="01",
            kicker="§ Ranking",
            titulo="Os maiores <em>emissores</em>",
            deck=(
                "Empresas ordenadas pelo volume total de emissões, desmembradas "
                "por escopo. Poucos nomes concentram uma fração desproporcional "
                "do total registrado."
            ),
            conteudo=_render_chart(grafico_top_emissores(df_recente)),
            anchor="emissores",
        ),
        _render_chapter(
            num="02",
            kicker="§ Anatomia",
            titulo="Composição por <em>escopo</em>",
            deck=(
                "Onde as emissões realmente acontecem. A distribuição agregada "
                "revela o peso da cadeia de valor, enquanto a correlação entre "
                "escopos 1 e 3 expõe perfis distintos de negócio."
            ),
            conteudo=_render_chart_grid(
                grafico_distribuicao_escopos(df_recente),
                grafico_scatter_escopos(df_recente),
            ),
            anchor="escopos",
        ),
        _render_chapter(
            num="03",
            kicker="§ Territorio",
            titulo="Geografia das <em>emissões</em>",
            deck=(
                "Distribuição por unidade federativa. A concentração geográfica "
                "reflete a presença dos grandes polos industriais e energéticos "
                "do país."
            ),
            conteudo=_render_chart(grafico_por_estado(df_recente)),
            anchor="geografia",
        ),
        _render_chapter(
            num="04",
            kicker="§ Contrapartida",
            titulo="Créditos e <em>compensação</em>",
            deck=(
                "A tradução financeira da pegada de carbono. Quantos créditos "
                "são necessários e quantas empresas já mantêm projetos ativos "
                "de compensação voluntária."
            ),
            conteudo=_render_chart_grid(
                grafico_creditos_carbono(df_recente),
                grafico_compensacao_status(df_recente),
            ),
            anchor="compensacao",
        ),
        _render_chapter(
            num="05",
            kicker="§ Registro",
            titulo="Tabela <em>completa</em>",
            deck=(
                "Registro detalhado de cada empresa — volumes por escopo, "
                "créditos necessários, custo de compensação e metas de net zero "
                "declaradas."
            ),
            conteudo=_render_tabelas_section(df),
            anchor="tabela",
        ),
    ]

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crédito de Carbono · Dashboard</title>
    <meta name="description" content="Dashboard editorial de emissões de carbono corporativo — Registro Público FGV · GHG Protocol.">
    <link rel="stylesheet" href="{CAMINHO_CSS}">
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    <script defer src="{CAMINHO_JS}"></script>
</head>
<body>
    <div class="shell">
        <header class="masthead">
            <div class="masthead-content">
                <div class="masthead-text">
                    <h1 class="masthead-title">Crédito<br><em>de Carbono</em></h1>
                    <p class="masthead-standfirst">
                        Retrato consolidado das emissões registradas no <strong>Registro
                        Público de Emissões</strong> da Fundação Getulio Vargas. Escopos
                        1, 2 e 3 lado a lado com a contrapartida financeira da
                        compensação no mercado voluntário brasileiro.
                    </p>
                </div>
                <div class="masthead-team">
                    <span class="masthead-team-label">Equipe</span>
                    <ul class="masthead-team-list">
                        <li><a href="https://www.linkedin.com/in/pedro-ism/" target="_blank" rel="noopener" class="masthead-team-link"><span class="team-icon">&#8599;</span>Pedro Monteiro</a></li>
                        <li><a href="https://www.linkedin.com/in/sergio-chousinho-a34278249?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=ios_app" target="_blank" rel="noopener" class="masthead-team-link"><span class="team-icon">&#8599;</span>Sérgio Chousino</a></li>
                        <li><a href="https://www.linkedin.com/in/ricardofilhodev?utm_source=share_via&utm_content=profile&utm_medium=member_android" target="_blank" rel="noopener" class="masthead-team-link"><span class="team-icon">&#8599;</span>Ricardo Severiano</a></li>
                        <li><a href="https://github.com/codeblack2301" target="_blank" rel="noopener" class="masthead-team-link"><span class="team-icon">&#8599;</span>Rafael Aimbere</a></li>
                    </ul>
                </div>
                <div class="masthead-logos">
                    <img src="../img/logo-bb.png" alt="Banco do Brasil" class="masthead-logo masthead-logo--bb">
                    <img src="../img/logo-cesar.png" alt="CESAR School" class="masthead-logo masthead-logo--cesar">
                </div>
            </div>
        </header>

        <nav class="rail">
            <a href="#panorama"><span class="sec">§00</span>Panorama</a>
            <a href="#emissores"><span class="sec">§01</span>Emissores</a>
            <a href="#escopos"><span class="sec">§02</span>Escopos</a>
            <a href="#geografia"><span class="sec">§03</span>Geografia</a>
            <a href="#compensacao"><span class="sec">§04</span>Compensação</a>
            <a href="#tabela"><span class="sec">§05</span>Registro</a>
        </nav>

        {_render_hero(df_recente)}
        {_render_kpi_row(df_recente)}
        {_render_note()}

        {''.join(capitulos)}
    </div>

<script>
(function () {{
    var t;
    function r() {{
        clearTimeout(t);
        t = setTimeout(function () {{
            document.querySelectorAll('.plotly-graph-div').forEach(function (d) {{
                if (d.data) Plotly.Plots.resize(d);
            }});
        }}, 80);
    }}
    window.addEventListener('load', r);
    if ('ResizeObserver' in window) {{
        var ro = new ResizeObserver(r);
        document.querySelectorAll('.chart-card').forEach(function (c) {{
            ro.observe(c);
        }});
    }}
}})();
</script>

<button id="theme-toggle" class="theme-toggle" type="button" aria-label="Alternar tema">
  <span class="theme-toggle-icon"></span>
  <span class="theme-toggle-label"></span>
</button>
</body>
</html>"""

    return html


def main():
    print("=" * 60)
    print("  BBCarbono — Gerando Dashboard de Emissoes")
    print("=" * 60)
    print()

    _registrar_tema_plotly()

    df = carregar_dados()

    if df.empty:
        logger.error("Nenhuma empresa com dados completos encontrada.")
        return

    logger.info("Gerando graficos...")
    html = montar_dashboard(df)

    ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_SAIDA.write_text(html, encoding="utf-8")
    logger.info(f"Dashboard salvo em: {ARQUIVO_SAIDA}")

    print(f"\nAbrindo no navegador...")
    webbrowser.open(ARQUIVO_SAIDA.resolve().as_uri())


if __name__ == "__main__":
    main()
