import requests
import json
import os
from ftplib import FTP
from collections import defaultdict

API_TOKEN = os.getenv("BARRAGENS_API_TOKEN", "").strip()
API_BASE = "https://barragens.pt/api/dams"

def obter_dados_nacionais():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}", 
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("A obter a lista de todas as estações...")
    try:
        resp = requests.get(API_BASE, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"Erro ao obter lista: HTTP {resp.status_code}")
            return
            
        todas_estacoes = resp.json().get("data", [])
    except Exception as e:
        print(f"Erro de rede na lista: {e}")
        return

    print(f"Encontradas {len(todas_estacoes)} estações. A obter dados (isto pode demorar alguns minutos)...")
    
    dados_por_bacia = defaultdict(list)
    
    for b in todas_estacoes:
        id_b = b["id"]
        nome = b["name"]
        # Pega o nome da bacia. Se não tiver, coloca "Outras"
        bacia = b.get("basin_name") or "Outras"
        
        try:
            url_rt = f"{API_BASE}/{id_b}/realtime"
            resp_rt = requests.get(url_rt, headers=headers, timeout=10)
            
            historico = []
            if resp_rt.status_code == 200:
                dados_rt = resp_rt.json().get("data", [])
                # Guardar as últimas 24 leituras para o gráfico
                historico = dados_rt[-24:] if len(dados_rt) > 24 else dados_rt
            
            atual = historico[-1] if historico else {}
            
            dados_estacao = {
                "id": id_b,
                "nome": nome,
                "lat": b["coordinates"]["lat"],
                "lon": b["coordinates"]["lon"],
                "rio": b.get("river", ""),
                "atual": atual,
                "historico": historico
            }
            
            dados_por_bacia[bacia].append(dados_estacao)
            print(f"✅ {nome} ({bacia})")
            
        except Exception as e:
            print(f"❌ Erro em {nome}: {e}")

    with open("dados_nacional.js", "w", encoding="utf-8") as f:
        f.write(f"var dadosNacionais = {json.dumps(dados_por_bacia, ensure_ascii=False)};")
    print("Ficheiro dados_nacional.js gerado.")
    
    ftp_host = os.getenv("FTP_HOST")
    if ftp_host:
        try:
            ftp = FTP(ftp_host)
            ftp.login(os.getenv("FTP_USER"), os.getenv("FTP_PASS"))
            ftp.cwd('/apoio_operador/') 
            with open("dados_nacional.js", "rb") as f:
                ftp.storbinary("STOR dados_nacional.js", f)
            ftp.quit()
            print("🚀 Upload para o qsl.net concluído!")
        except Exception as e:
            print(f"❌ Erro no FTP: {e}")

if __name__ == "__main__":
    obter_dados_nacionais()
