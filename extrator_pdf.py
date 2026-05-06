"""
extrator_pdf.py
===============
Extrai o texto de todos os PDFs baixados (Base_Dados_FGV_Final/) e salva
em lotes de 10 empresas na pasta JSON_Processados/.

Apos extração bem-sucedida, o PDF original e excluido para liberar espaco.

Uso:
    python extrator_pdf.py
"""

import json
import logging
from pathlib import Path

import pdfplumber
from tqdm import tqdm

PASTA_BASE = Path("Base_Dados_FGV_Final")
PASTA_SAIDA = Path("JSON_Processados")
TAMANHO_LOTE = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def carregar_metadados(pasta_empresa: Path) -> dict:
    """Carrega o JSON de metadados de uma empresa, se existir."""
    caminho = pasta_empresa / "metadados_completos.json"
    if not caminho.exists():
        return {}
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def extrair_texto_pdf(caminho_pdf: Path) -> str:
    """Extrai todo o texto de um PDF usando pdfplumber."""
    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                paginas.append(texto)
    return "\n".join(paginas)


def processar_empresa(pasta_empresa: Path) -> dict:
    """Processa uma empresa: extrai texto dos PDFs e monta o registro."""
    metadados = carregar_metadados(pasta_empresa)
    arquivos_pdf = sorted(pasta_empresa.glob("*.pdf"))
    textos_extraidos = {}

    for pdf_path in arquivos_pdf:
        try:
            textos_extraidos[pdf_path.name] = extrair_texto_pdf(pdf_path)
            pdf_path.unlink()
        except Exception as e:
            textos_extraidos[pdf_path.name] = f"ERRO NA EXTRAÇÃO: {e}"
            logger.warning(f"  Erro ao processar {pdf_path.name}: {e}")

    return {
        "empresa_pasta": pasta_empresa.name,
        "id_fgv": metadados.get("id"),
        "nome_oficial": metadados.get("name"),
        "estado": metadados.get("state", {}).get("acronym"),
        "conteudo_pdfs": textos_extraidos,
    }


def salvar_lote(dados: list, numero_lote: int) -> None:
    """Salva um lote de registros em arquivo JSON."""
    PASTA_SAIDA.mkdir(exist_ok=True)
    arquivo = PASTA_SAIDA / f"lote_{numero_lote:02d}.json"
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


def main():
    if not PASTA_BASE.exists():
        logger.error(f"Pasta '{PASTA_BASE}' nao encontrada.")
        return

    pastas_empresas = sorted(
        p for p in PASTA_BASE.iterdir() if p.is_dir()
    )
    total = len(pastas_empresas)
    logger.info(f"--- INICIANDO EXTRAÇÃO DE TEXTO ({total} empresas) ---")

    lote_atual = []
    numero_lote = 1

    with tqdm(total=total, desc="Processando Empresas") as pbar:
        for i, pasta in enumerate(pastas_empresas):
            lote_atual.append(processar_empresa(pasta))
            pbar.update(1)

            if len(lote_atual) >= TAMANHO_LOTE or (i + 1) == total:
                salvar_lote(lote_atual, numero_lote)
                lote_atual = []
                numero_lote += 1

    logger.info(f"[FIM] Extracao concluida! Arquivos gerados em '{PASTA_SAIDA}'")


if __name__ == "__main__":
    main()
