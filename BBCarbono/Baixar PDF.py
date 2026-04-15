import requests
import urllib3
import os
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# 1. Configurações de SSL e avisos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FGVAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        context.check_hostname = False
        kwargs['ssl_context'] = context
        return super(FGVAdapter, self).init_poolmanager(*args, **kwargs)

def execucao_final_completa():
    session = requests.Session()
    session.mount("https://", FGVAdapter())
    
    search_url = "https://registropublicodeemissoesapi.fgv.br/api/services/app/EstatisticaPublica/SearchAllOrganizations"
    
    # IMPORTANTE: Mude 'maxResultCount' para 1000 para baixar todos os 902 participantes
    payload = {
        "sectorId": None, "cycleYear": [], "quanlificationId": [],
        "name": "", "subSectorId": None, "maxResultCount": 30, "skipCount": 0
    }

    print("--- INICIANDO COLETA: METADADOS + ARQUIVOS + CHECKLIST ---")
    try:
        response = session.post(search_url, json=payload, verify=False, timeout=20)
        data_json = response.json()
        empresas = data_json.get('result', {}).get('organizations', [])
        print(f"Sucesso! {len(empresas)} empresas carregadas.\n")
    except Exception as e:
        print(f"Erro ao acessar API de busca: {e}")
        return

    pasta_raiz = "Base_Dados_FGV_Final"
    os.makedirs(pasta_raiz, exist_ok=True)
    
    log_path = os.path.join(pasta_raiz, "00_RELATORIO_GERAL.txt")
    
    with open(log_path, "w", encoding="utf-8") as log:
        log.write("RELATÓRIO CONSOLIDADO: API vs DOWNLOAD LOCAL\n")
        log.write("="*75 + "\n\n")

        for index, emp in enumerate(empresas, 1):
            emp_id = emp.get('id')
            nome_raw = emp.get('name', 'SemNome')
            nome_limpo = "".join([c for c in nome_raw if c.isalnum() or c in (' ', '_')]).strip()
            
            # Informações da API para o Checklist
            ids_na_api = emp.get('inventoriesId', [])
            qtd_na_api = len(ids_na_api)
            
            # Extração de anos das qualificações
            anos_portal = [str(q.get('year')) for q in emp.get('qualifications', []) if q.get('year')]
            anos_str = ", ".join(sorted(set(anos_portal)))

            print(f"[{index}/{len(empresas)}] Processando: {nome_limpo}...")
            
            # Criar estrutura de pastas
            pasta_empresa = os.path.join(pasta_raiz, f"{nome_limpo}_{emp_id}")
            os.makedirs(pasta_empresa, exist_ok=True)

            # --- AQUI: SALVANDO OS METADADOS (JSON) ---
            with open(os.path.join(pasta_empresa, "metadados_completos.json"), "w", encoding="utf-8") as fj:
                json.dump(emp, fj, indent=4, ensure_ascii=False)

            # --- VARREDURA DE DOWNLOAD ---
            ids_baixados_local = []
            for i in range(1, 36): # Testa de 1 a 35
                url_dl = f"https://sistema-registropublicodeemissoesapi.fgv.br/GenerateReport/GenerateInventoryReport/{emp_id}/{i}/true"
                try:
                    res = session.get(url_dl, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=8)
                    if res.status_code == 200 and len(res.content) > 2500:
                        # Define extensão
                        ext = "pdf"
                        if "spreadsheet" in res.headers.get('Content-Type', '').lower():
                            ext = "xlsx"
                        
                        file_name = f"relatorio_id_{i}.{ext}"
                        with open(os.path.join(pasta_empresa, file_name), 'wb') as f:
                            f.write(res.content)
                        ids_baixados_local.append(i)
                except:
                    continue
            
            # --- VALIDAÇÃO DE INTEGRIDADE ---
            qtd_baixada = len(ids_baixados_local)
            # Se baixou o mesmo tanto ou mais que o inventoriesId da API, está OK
            check_integridade = "TRUE (OK)" if qtd_baixada >= qtd_na_api else f"FALSE (Faltam {qtd_na_api - qtd_baixada})"
            
            # --- REGISTRO NO LOG GERAL ---
            log.write(f"EMPRESA: {nome_raw}\n")
            log.write(f"ID: {emp_id} | ESTADO: {emp.get('state', {}).get('acronym', '??')} | ANOS: {anos_str}\n")
            log.write(f"API INDICOU: {qtd_na_api} arquivos | REALIZADO: {qtd_baixada} downloads\n")
            log.write(f"INTEGRIDADE: {check_integridade}\n")
            log.write(f"IDs LOCAIS: {', '.join(map(str, ids_baixados_local))}\n")
            log.write("-" * 60 + "\n")
            log.flush() # Garante escrita imediata
            
            time.sleep(0.5)

    print(f"\n[FIM] Base de dados gerada na pasta: {pasta_raiz}")

if __name__ == "__main__":
    execucao_final_completa()