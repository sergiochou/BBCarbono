"""
Baixar PDF.py
=============
Coleta metadados e inventarios (PDF/XLSX) do Registro Publico de Emissoes
da FGV para todas as organizacoes retornadas pela API de busca.

Uso:
    python "Baixar PDF.py"
"""

import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context

PASTA_RAIZ = Path("Base_Dados_FGV_Final")
LOTE_EMPRESAS = 100         # Empresas por pagina na busca
MAX_EMPRESAS = 902          # Limite total de empresas a processar
MAX_INVENTORY_ID = 35       # IDs de relatorio testados (1..35)
MIN_FILE_SIZE = 2500        # Bytes minimos para considerar download valido
MAX_WORKERS = 8             # Downloads paralelos de empresas

SEARCH_URL = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EstatisticaPublica/SearchAllOrganizations"
REPORT_URL = "https://sistema-registropublicodeemissoesapi.fgv.br/GenerateReport/GenerateInventoryReport"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_log_lock = threading.Lock()


class FGVAdapter(HTTPAdapter):
    """Adapter que reduz o nivel de seguranca SSL para compatibilidade com a API da FGV."""

    def __init__(self, *args, **kwargs):
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        kwargs.setdefault("max_retries", retry)
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        context.check_hostname = False
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def criar_session() -> requests.Session:
    """Cria uma session HTTP com o adapter SSL da FGV."""
    session = requests.Session()
    session.mount("https://", FGVAdapter())
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def sanitizar_nome(nome_raw: str) -> str:
    """Remove caracteres especiais do nome, mantendo alfanumericos, espacos e underscores."""
    return re.sub(r"[^\w\s]", "", nome_raw, flags=re.UNICODE).strip()


def buscar_empresas(session: requests.Session) -> list:
    """Busca todas as organizacoes em lotes para evitar erro 500 no servidor."""
    todas = []
    skip = 0

    while True:
        payload = {
            "sectorId": None,
            "cycleYear": [],
            "quanlificationId": [],
            "name": "",
            "subSectorId": None,
            "maxResultCount": LOTE_EMPRESAS,
            "skipCount": skip,
        }
        response = session.post(SEARCH_URL, json=payload, verify=False, timeout=60)
        response.raise_for_status()
        resultado = response.json().get("result", {})
        lote = resultado.get("organizations", [])
        todas.extend(lote)
        todas = todas[:MAX_EMPRESAS]

        total = resultado.get("total", 0)
        skip += len(lote)
        logger.info(f"Carregadas {min(skip, MAX_EMPRESAS)}/{min(total, MAX_EMPRESAS)} empresas...")

        if skip >= total or not lote or skip >= MAX_EMPRESAS:
            break

        time.sleep(0.3)

    return todas


def baixar_relatorios(session: requests.Session, emp_id: int, pasta_empresa: Path, qtd_esperada: int) -> list[int]:
    """Tenta baixar relatorios de IDs 1..MAX_INVENTORY_ID para uma empresa.

    Para quando ja encontrou todos os arquivos esperados (qtd_esperada).
    Pula arquivos que ja existem localmente.
    """
    ids_baixados = []

    for i in range(1, MAX_INVENTORY_ID + 1):
        # Pula se ja foi baixado antes (resumibilidade)
        existente = list(pasta_empresa.glob(f"relatorio_id_{i}.*"))
        if existente and any(f.stat().st_size > MIN_FILE_SIZE for f in existente):
            ids_baixados.append(i)
            if qtd_esperada and len(ids_baixados) >= qtd_esperada:
                break
            continue

        url = f"{REPORT_URL}/{emp_id}/{i}/true"
        try:
            res = session.get(url, verify=False, timeout=15)
            if res.status_code != 200 or len(res.content) <= MIN_FILE_SIZE:
                continue

            ext = "xlsx" if "spreadsheet" in res.headers.get("Content-Type", "").lower() else "pdf"
            arquivo = pasta_empresa / f"relatorio_id_{i}.{ext}"
            arquivo.write_bytes(res.content)
            ids_baixados.append(i)

            if qtd_esperada and len(ids_baixados) >= qtd_esperada:
                break

        except requests.RequestException:
            continue

    return ids_baixados


def processar_empresa(emp: dict, index: int, total: int) -> dict:
    """Processa uma empresa: salva metadados e baixa relatorios. Thread-safe."""
    session = criar_session()

    emp_id = emp.get("id")
    nome_raw = emp.get("name", "SemNome")
    nome_limpo = sanitizar_nome(nome_raw)

    ids_na_api = emp.get("inventoriesId", [])
    qtd_na_api = len(ids_na_api)

    anos_portal = {str(q["year"]) for q in emp.get("qualifications", []) if q.get("year")}
    anos_str = ", ".join(sorted(anos_portal))

    pasta_empresa = PASTA_RAIZ / f"{nome_limpo}_{emp_id}"
    pasta_empresa.mkdir(exist_ok=True)

    meta_path = pasta_empresa / "metadados_completos.json"
    meta_path.write_text(json.dumps(emp, indent=4, ensure_ascii=False), encoding="utf-8")

    ids_baixados = baixar_relatorios(session, emp_id, pasta_empresa, qtd_na_api)
    qtd_baixada = len(ids_baixados)

    if qtd_baixada >= qtd_na_api:
        check = "TRUE (OK)"
    else:
        check = f"FALSE (Faltam {qtd_na_api - qtd_baixada})"

    with _log_lock:
        logger.info(f"[{index}/{total}] {nome_limpo[:40]} -> {qtd_baixada}/{qtd_na_api} arquivos | {check}")

    return {
        "nome_raw": nome_raw,
        "emp_id": emp_id,
        "estado": emp.get("state", {}).get("acronym", "??"),
        "anos_str": anos_str,
        "qtd_na_api": qtd_na_api,
        "qtd_baixada": qtd_baixada,
        "check": check,
        "ids_baixados": ids_baixados,
    }


def main():
    session = criar_session()

    print("--- INICIANDO COLETA: METADADOS + ARQUIVOS + CHECKLIST ---")
    print(f"    Workers paralelos: {MAX_WORKERS}")

    try:
        empresas = buscar_empresas(session)
        logger.info(f"Sucesso! {len(empresas)} empresas carregadas.")
    except requests.RequestException as e:
        logger.error(f"Erro ao acessar API de busca: {e}")
        return

    PASTA_RAIZ.mkdir(exist_ok=True)
    total = len(empresas)

    resultados = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(processar_empresa, emp, i, total): i
            for i, emp in enumerate(empresas, 1)
        }
        for future in as_completed(futures):
            try:
                resultados.append(future.result())
            except Exception as e:
                idx = futures[future]
                logger.error(f"[{idx}/{total}] Erro inesperado: {e}")

    resultados.sort(key=lambda r: r["emp_id"])

    log_path = PASTA_RAIZ / "00_RELATORIO_GERAL.txt"
    with open(log_path, "w", encoding="utf-8") as log:
        log.write("RELATÓRIO CONSOLIDADO: API vs DOWNLOAD LOCAL\n")
        log.write("=" * 75 + "\n\n")

        for r in resultados:
            log.write(f"EMPRESA: {r['nome_raw']}\n")
            log.write(f"ID: {r['emp_id']} | ESTADO: {r['estado']} | ANOS: {r['anos_str']}\n")
            log.write(f"API INDICOU: {r['qtd_na_api']} arquivos | REALIZADO: {r['qtd_baixada']} downloads\n")
            log.write(f"INTEGRIDADE: {r['check']}\n")
            log.write(f"IDs LOCAIS: {', '.join(map(str, r['ids_baixados']))}\n")
            log.write("-" * 60 + "\n")

    print(f"\n[FIM] Base de dados gerada na pasta: {PASTA_RAIZ}")


if __name__ == "__main__":
    main()
