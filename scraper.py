import requests
import json
import os
from ftplib import FTP

API_TOKEN = os.getenv("BARRAGENS_API_TOKEN", "").strip()
API_BASE = "https://barragens.pt/api/dams"

DAMS = {
    "vilarinho": "1627759560",
    "canicada": "1627743674",
    "salamonde": "1627759378",
    "paradela": "1627758928",
    "vendanova": "1627759522",
    "rabagao": "1627743430"
}

def obter_dados():
    # MÁGICA AQUI: Adicionamos o User-Agent para parecer um browser normal
    headers = {
        "Authorization": f"Bearer {API_TOKEN}", 
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resultado = {}
    
    print("A obter dados da API...")
    for nome, id_barragem in DAMS.items():
        try:
            url = f"{API_BASE}/{id_barragem}/realtime"
            resp = requests.get(url, headers=headers, timeout=15)
            
            # Se a resposta não for 200, avisa no log do GitHub
            if resp.status_code != 200:
                print(f"❌ Falha em {nome}: HTTP {resp.status_code} - {resp.text[:100]}")
                continue

            dados = resp.json()
            if dados.get("data") and len(dados["data"]) > 0:
                ultimo = dados["data"][-1]
                resultado[nome] = {
                    "storage_percent": ultimo.get("storage_percent"),
                    "inflow": ultimo.get("inflow"),
                    "outflow": ultimo.get("outflow"),
                    "level": ultimo.get("level"),
                    "label": ultimo.get("label")
                }
                print(f"✅ OK: {nome}")
            else:
                print(f"⚠️ Sem dados para {nome}")
                
        except Exception as e:
            print(f"❌ Erro de rede em {nome}: {e}")
            
    # Cria o ficheiro JavaScript
    with open("dados_cavado.js", "w", encoding="utf-8") as f:
        f.write(f"var dadosReaisBarragens = {json.dumps(resultado, ensure_ascii=False)};")
    print(f"Ficheiro dados_cavado.js gerado com {len(resultado)} barragens.")
    
    # Enviar para o FTP
    ftp_host = os.getenv("FTP_HOST")
    if ftp_host and len(resultado) > 0:
        print("A enviar para o qsl.net...")
        try:
            ftp = FTP(ftp_host)
            ftp.login(os.getenv("FTP_USER"), os.getenv("FTP_PASS"))
            ftp.cwd('/apoio_operador/')
            with open("dados_cavado.js", "rb") as f:
                ftp.storbinary("STOR dados_cavado.js", f)
            ftp.quit()
            print("🚀 Upload concluído com sucesso!")
        except Exception as e:
            print(f"❌ Erro no FTP: {e}")
    elif len(resultado) == 0:
        print("⚠️ O ficheiro está vazio. Não foi enviado para o FTP para não apagar os dados antigos.")

if __name__ == "__main__":
    obter_dados()
