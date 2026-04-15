import os
import json
import pdfplumber
from tqdm import tqdm

def extrair_texto_de_pdfs(pasta_raiz):
    dados_consolidados = []
    
    # Lista todas as pastas de empresas
    pastas_empresas = [f for f in os.listdir(pasta_raiz) if os.path.isdir(os.path.join(pasta_raiz, f))]
    
    print(f"--- INICIANDO EXTRAÇÃO DE TEXTO ({len(pastas_empresas)} empresas) ---")

    for nome_pasta in tqdm(pastas_empresas, desc="Processando Empresas"):
        caminho_empresa = os.path.join(pasta_raiz, nome_pasta)
        
        # 1. Tenta carregar os metadados que você já baixou
        metadados = {}
        caminho_meta = os.path.join(caminho_empresa, "metadados_completos.json")
        if os.path.exists(caminho_meta):
            with open(caminho_meta, 'r', encoding='utf-8') as f:
                metadados = json.load(f)

        # 2. Busca todos os PDFs na pasta da empresa
        arquivos_pdf = [f for f in os.listdir(caminho_empresa) if f.endswith('.pdf')]
        
        textos_extraidos = {}
        
        for pdf_nome in arquivos_pdf:
            caminho_pdf = os.path.join(caminho_empresa, pdf_nome)
            texto_completo_pdf = ""
            
            try:
                with pdfplumber.open(caminho_pdf) as pdf:
                    # Extrai o texto de cada página
                    for pagina in pdf.pages:
                        texto_pag = pagina.extract_text()
                        if texto_pag:
                            texto_completo_pdf += texto_pag + "\n"
                
                textos_extraidos[pdf_nome] = texto_completo_pdf
            except Exception as e:
                textos_extraidos[pdf_nome] = f"ERRO NA EXTRAÇÃO: {str(e)}"

        # 3. Monta o objeto da empresa com metadados + texto dos PDFs
        registro = {
            "empresa_pasta": nome_pasta,
            "id_fgv": metadados.get("id"),
            "nome_oficial": metadados.get("name"),
            "estado": metadados.get("state", {}).get("acronym"),
            "conteudo_pdfs": textos_extraidos # Dicionário: {"relatorio_1.pdf": "texto...", ...}
        }
        
        dados_consolidados.append(registro)

    # 4. Salva o resultado final em um JSON gigante organizado
    with open("dados_fgv_processados.json", "w", encoding="utf-8") as f:
        json.dump(dados_consolidados, f, indent=4, ensure_ascii=False)

    print(f"\n[FIM] Extração concluída! Arquivo gerado: dados_fgv_processados.json")

if __name__ == "__main__":
    # Ajuste o caminho abaixo se sua pasta tiver outro nome ou local
    PASTA_BASE = "Base_Dados_FGV_Final"
    extrair_texto_de_pdfs(PASTA_BASE)