"""
filtro_carbono_ia.py
====================
Pipeline local para filtrar e estruturar dados de emissoes de carbono
extraidos dos inventarios de GEE (Registro Publico de Emissoes da FGV).

Le os JSONs brutos (JSON_Processados/), extrai dados de emissoes via
regex (sem depender de API externa) e salva em lotes de 10 empresas
na pasta JSON_Filtrados_Carbono/.

Uso:
    python filtro_carbono_ia.py
"""

import sys
import json
import re
import logging
from pathlib import Path

PASTA_ENTRADA = "JSON_Processados"
PASTA_SAIDA = "JSON_Filtrados_Carbono"
TAMANHO_LOTE = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def carregar_lotes_entrada():
    """Carrega todos os arquivos de lote da pasta de entrada."""
    pasta = Path(PASTA_ENTRADA)
    if not pasta.exists():
        logger.error(f"Pasta '{PASTA_ENTRADA}' nao encontrada!")
        sys.exit(1)

    arquivos = sorted(pasta.glob("lote_*.json"))
    if not arquivos:
        logger.error(f"Nenhum arquivo lote_*.json encontrado em '{PASTA_ENTRADA}'!")
        sys.exit(1)

    todas_empresas = []
    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                dados = json.load(f)
            todas_empresas.extend(dados)
            logger.info(f"  Carregado: {arq.name} ({len(dados)} empresas)")
        except Exception as e:
            
            logger.warning(f"  Erro ao carregar {arq.name}: {e}")

    logger.info(f"Total de empresas carregadas: {len(todas_empresas)}")
    return todas_empresas


def parse_numero_br(texto):
    """Converte numero no formato brasileiro (1.234,56) para float."""
    if not texto:
        return None
    texto = texto.strip()
    # Remove pontos de milhar e troca virgula por ponto
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _sort_key_pdf(nome):
    """Extrai o ID numerico do nome do PDF para ordenacao correta."""
    match = re.search(r"_id_(\d+)", nome)
    return int(match.group(1)) if match else 0


def listar_textos_pdfs(empresa):
    """Retorna lista de (pdf_nome, texto) ordenada por ID numerico crescente."""
    conteudo = empresa.get("conteudo_pdfs", {})
    if not conteudo:
        return []

    textos = []
    for pdf_nome in sorted(conteudo.keys(), key=_sort_key_pdf):
        texto = conteudo[pdf_nome]
        if texto and not texto.startswith("ERRO NA EXTRA"):
            textos.append((pdf_nome, texto))

    return textos


def extrair_ano_inventario(texto):
    """Extrai o ano do inventario mais recente do texto."""
    # Padrao: "Ano inventariado: 2023" ou "Inventario 2023"
    padroes = [
        r"Ano\s+inventariado[:\s]+(\d{4})",
        r"Ano\s+do\s+invent[aá]rio[:\s]+(\d{4})",
        r"Invent[aá]rio\s+(\d{4})\s*[-–]",
    ]
    anos = []
    for padrao in padroes:
        matches = re.findall(padrao, texto, re.IGNORECASE)
        anos.extend(int(a) for a in matches if 2000 <= int(a) <= 2030)

    return max(anos) if anos else None


def extrair_setor_economico(texto):
    """Extrai o setor economico declarado."""
    match = re.search(
        r"Setor\s+econ[oô]mico[:\s]+([^\n]+)",
        texto,
        re.IGNORECASE,
    )
    if match:
        setor = match.group(1).strip()
        # Remove lixo de PDF
        setor = re.sub(r"\s{2,}", " ", setor)
        if len(setor) > 3:
            return setor
    return None


def extrair_emissoes_resumo(texto):
    """Extrai emissoes dos escopos da tabela 'Resumo das emissoes totais'.

    A linha Total na tabela de tCO2e tem o formato:
    Total <escopo1> <escopo2_loc> <escopo2_escolha> <escopo3>
    """
    escopo1 = None
    escopo2 = None
    escopo3 = None

    # Busca a secao "Resumo das emissoes totais"
    idx = re.search(r"Resumo\s+das\s+emiss[oõ]es\s+totais", texto, re.IGNORECASE)
    if not idx:
        return escopo1, escopo2, escopo3

    # Pega o trecho apos o titulo da secao
    trecho = texto[idx.start():idx.start() + 3000]

    # Numero BR com parte decimal obrigatoria (ex: 1.507,705) para evitar
    # capturar numeros de secao como "2.4" ou datas como "02"
    NUM = r"[\d]+(?:\.[\d]{3})*,[\d]+"

    # Formato 1: 4 colunas (E1, E2_loc, E2_escolha, E3)
    padrao_4col = (
        r"Total\s+"
        rf"({NUM})\s+"
        rf"({NUM})\s+"
        rf"({NUM})\s+"
        rf"({NUM})"
    )
    # Formato 2: 3 colunas (E1, E2, E3) - sem "escolha de compra"
    padrao_3col = (
        r"Total\s+"
        rf"({NUM})\s+"
        rf"({NUM})\s+"
        rf"({NUM})"
    )

    match = re.search(padrao_4col, trecho)
    if match:
        escopo1 = parse_numero_br(match.group(1))
        escopo2 = parse_numero_br(match.group(2))
        escopo3 = parse_numero_br(match.group(4))
    else:
        match = re.search(padrao_3col, trecho)
        if match:
            escopo1 = parse_numero_br(match.group(1))
            escopo2 = parse_numero_br(match.group(2))
            escopo3 = parse_numero_br(match.group(3))

    return escopo1, escopo2, escopo3


def extrair_projetos_compensacao(texto):
    """Extrai nomes de projetos de compensacao de carbono."""
    projetos = []

    # Busca secao de compensacao
    idx = re.search(
        r"Compensa[çc][aã]o\s+de\s+emiss[oõ]es",
        texto,
        re.IGNORECASE,
    )
    if not idx:
        return projetos

    trecho = texto[idx.start():idx.start() + 2000]

    # Busca linhas que parecem nomes de projetos (apos a tabela header)
    # Formato tipico: NomeProjeto <numero> Sim/Nao
    linhas = trecho.split("\n")
    capturando = False
    for linha in linhas:
        linha = linha.strip()
        if re.search(r"Projeto\s+de\s+compensa", linha, re.IGNORECASE):
            capturando = True
            continue
        if capturando and linha:
            # Ignora linhas que sao claramente nao-projetos
            if re.match(r"^(Total|N[aã]o|Sim|\d|$)", linha):
                continue
            if re.search(r"organiza[çc][aã]o", linha, re.IGNORECASE):
                continue
            if re.search(r"possui\s+projetos", linha, re.IGNORECASE):
                break
            # Extrai nome do projeto (ate o primeiro numero grande ou Sim/Nao)
            nome_match = re.match(r"^(.+?)(?:\s+[\d.,]+\s+(?:Sim|N[aã]o|sim|n[aã]o))", linha)
            if nome_match:
                nome = nome_match.group(1).strip()
                if len(nome) > 3:
                    projetos.append(nome)
            elif len(linha) > 3 and not re.match(r"^[\d.,\s]+$", linha):
                # Se a linha tem conteudo textual, pode ser um nome
                if len(linha) < 150:
                    projetos.append(linha)
            if len(projetos) >= 10:
                break

    return projetos


def extrair_metas_net_zero(texto):
    """Extrai metas de net zero ou neutralidade de carbono."""
    padroes = [
        r"(?:meta|compromisso|objetivo)\s+(?:de\s+)?(?:net\s*zero|neutralidade|carbono\s+neutro)[^.]*?(\d{4})",
        r"(?:net\s*zero|neutralidade|carbono\s+neutro)[^.]*?(?:at[eé]|em|para)\s+(\d{4})",
        r"(\d{4})[^.]*?(?:net\s*zero|neutralidade|carbono\s+neutro)",
    ]

    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            ano = int(match.group(1))
            if 2025 <= ano <= 2070:
                # Captura contexto ao redor
                start = max(0, match.start() - 30)
                end = min(len(texto), match.end() + 80)
                descricao = texto[start:end].strip()
                descricao = re.sub(r"\s+", " ", descricao)
                return {"ano": ano, "descricao": descricao[:150]}

    return None


def processar_inventario(pdf_nome, texto):
    """Extrai dados de emissoes de um unico PDF/inventario."""
    ano = extrair_ano_inventario(texto)
    setor = extrair_setor_economico(texto)
    escopo1, escopo2, escopo3 = extrair_emissoes_resumo(texto)

    valores = [v for v in [escopo1, escopo2, escopo3] if v is not None]
    total = round(sum(valores), 3) if valores else None

    status = "sucesso" if valores else "sem_dados"

    return {
        "pdf_origem": pdf_nome,
        "ano_inventario": ano,
        "setor_economico": setor,
        "emissoes_escopo_1": escopo1,
        "emissoes_escopo_2": escopo2,
        "emissoes_escopo_3": escopo3,
        "total_emissoes": total,
        "status": status,
    }


def processar_empresa(empresa):
    """Processa todos os PDFs de uma empresa, extraindo dados de cada ano."""
    textos = listar_textos_pdfs(empresa)

    if not textos:
        return {
            "inventarios": [],
            "projetos_carbono": [],
            "metas_net_zero": None,
            "status": "sem_dados",
        }

    inventarios = []
    for pdf_nome, texto in textos:
        inv = processar_inventario(pdf_nome, texto)
        inventarios.append(inv)

    # Projetos e metas sao buscados no texto completo (nivel empresa).
    texto_completo = "\n\n".join(t for _, t in textos)
    projetos = extrair_projetos_compensacao(texto_completo)
    metas = extrair_metas_net_zero(texto_completo)

    n_sucesso = sum(1 for inv in inventarios if inv["status"] == "sucesso")
    if n_sucesso > 0:
        status = "sucesso"
    elif any(inv["total_emissoes"] is not None for inv in inventarios):
        status = "parcial"
    else:
        status = "sem_dados"

    return {
        "inventarios": inventarios,
        "projetos_carbono": projetos,
        "metas_net_zero": metas,
        "status": status,
    }


def salvar_lote(lote_dados, numero_lote):
    """Salva um lote de dados filtrados em arquivo JSON."""
    pasta = Path(PASTA_SAIDA)
    pasta.mkdir(exist_ok=True)

    nome_arquivo = pasta / f"lote_filtrado_{numero_lote:02d}.json"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(lote_dados, f, indent=4, ensure_ascii=False)

    logger.info(f"  Salvo: {nome_arquivo.name} ({len(lote_dados)} empresas)")


def main():
    print("=" * 60)
    print("  BBCarbono - Filtro de Emissoes (Regex local)")
    print("=" * 60)
    print()

    logger.info("Carregando lotes de entrada...")
    empresas = carregar_lotes_entrada()
    total = len(empresas)

    if total == 0:
        logger.error("Nenhuma empresa encontrada. Encerrando.")
        return

    logger.info(f"Processando {total} empresas...")
    print()

    lote_atual = []
    numero_lote = 1
    contadores = {"sucesso": 0, "parcial": 0, "sem_dados": 0}
    total_inventarios = 0

    for i, empresa in enumerate(empresas):
        nome = empresa.get("nome_oficial", empresa.get("empresa_pasta", "?"))
        resultado = processar_empresa(empresa)

        registro = {
            "empresa_pasta": empresa.get("empresa_pasta"),
            "id_fgv": empresa.get("id_fgv"),
            "nome_oficial": empresa.get("nome_oficial"),
            "estado": empresa.get("estado"),
            "dados_carbono": resultado,
        }

        contadores[resultado.get("status", "sem_dados")] += 1
        n_inv = len(resultado.get("inventarios", []))
        n_ok = sum(1 for inv in resultado.get("inventarios", []) if inv["status"] == "sucesso")
        total_inventarios += n_inv
        lote_atual.append(registro)

        logger.info(
            f"  [{i+1}/{total}] {nome[:40]} -> {resultado['status']}"
            f" | {n_ok}/{n_inv} inventarios com dados"
        )

        if len(lote_atual) >= TAMANHO_LOTE or (i + 1) == total:
            salvar_lote(lote_atual, numero_lote)
            lote_atual = []
            numero_lote += 1

    print()
    print("=" * 60)
    print("  RELATORIO FINAL")
    print("=" * 60)
    print(f"  Total de empresas:      {total}")
    print(f"  Total de inventarios:   {total_inventarios}")
    print(f"  Sucesso:                {contadores['sucesso']}")
    print(f"  Parcial (sem totais):   {contadores['parcial']}")
    print(f"  Sem dados:              {contadores['sem_dados']}")
    print(f"  Lotes gerados:          {numero_lote - 1}")
    print(f"  Pasta de saida:         {PASTA_SAIDA}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
