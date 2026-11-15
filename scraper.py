import requests
import json
import os
from ftplib import FTP

API_TOKEN = os.getenv("BARRAGENS_API_TOKEN")
API_BASE = "https://barragens.pt/api/dams"

# IDs das barragens do Cávado
DAMS = {
    "vilarinho": "1627759560",
    "canicada": "1627743674",
    "salamonde": "1627759378",
    "paradela": "1627758928",
    "vendanova": "1627759522",
    "rabagao": "1627743430"
}

def obter_dados():
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    resultado = {}
    
    print("A obter dados da API...")
    for nome, id_barragem in DAMS.items():
        try:
            url = f"{API_BASE}/{id_barragem}/realtime"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                dados = resp.json()
                if dados.get("data") and len(dados["data"]) > 0:
                    # Pega no último registo (o mais recente)
                    ultimo = dados["data"][-1]
                    resultado[nome] = {
                        "storage_percent": ultimo.get("storage_percent"),
                        "inflow": ultimo.get("inflow"),
                        "outflow": ultimo.get("outflow"),
                        "level": ultimo.get("level"),
                        "label": ultimo.get("label")
                    }
                    print(f"OK: {nome}")
            else:
                print(f"Falha em {nome}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"Erro de rede em {nome}: {e}")
            
    # Cria o ficheiro JavaScript
    with open("dados_cavado.js", "w", encoding="utf-8") as f:
        f.write(f"var dadosReaisBarragens = {json.dumps(resultado, ensure_ascii=False)};")
    print("Ficheiro dados_cavado.js gerado.")
    
    # Enviar para o FTP
    ftp_host = os.getenv("FTP_HOST")
    if ftp_host:
        print("A enviar para o qsl.net...")
        try:
            ftp = FTP(ftp_host)
            ftp.login(os.getenv("FTP_USER"), os.getenv("FTP_PASS"))
            ftp.cwd('/apoio_operador/') # Ajuste para a sua pasta
            with open("dados_cavado.js", "rb") as f:
                ftp.storbinary("STOR dados_cavado.js", f)
            ftp.quit()
            print("Upload concluído com sucesso!")
        except Exception as e:
            print(f"Erro no FTP: {e}")

if __name__ == "__main__":
    obter_dados()
