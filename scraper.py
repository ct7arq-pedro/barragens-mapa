import requests
import json
import os
import time
from ftplib import FTP

API_TOKEN = os.getenv("BARRAGENS_API_TOKEN", "").strip()
API_BASE = "https://barragens.pt/api"

# Nomes exatos das bacias que queremos
BACIA_ALVO = ["Cávado/ribeiras Costeiras", "Ave", "Lima"]

def obter_dados():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}", 
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("1. A obter a lista de bacias...")
    try:
        resp = requests.get(f"{API_BASE}/basins", headers=headers, timeout=20)
        resp.raise_for_status()
        todas_bacias = resp.json().get("data", [])
    except Exception as e:
        print(f"Erro ao obter bacias: {e}")
        return

    dados_barragens = {}
    resumos_bacias = {}

    for bacia in todas_bacias:
        nome_bacia = bacia.get("name")
        if nome_bacia not in BACIA_ALVO:
            continue
            
        id_bacia = bacia.get("id")
        print(f"\n2. A processar a bacia: {nome_bacia} (ID: {id_bacia})")
        
        # Obter Resumo da Bacia (Volume, Capacidade, %)
        try:
            resp_detalhe = requests.get(f"{API_BASE}/basins/{id_bacia}", headers=headers, timeout=15)
            if resp_detalhe.status_code == 200:
                resumos_bacias[nome_bacia] = resp_detalhe.json().get("data", {})
                print(f"   ✓ Resumo da bacia obtido.")
        except Exception as e:
            print(f"   ❌ Erro no resumo da bacia: {e}")

        time.sleep(0.5) # Pausa de segurança

        # Obter lista de barragens desta bacia
        try:
            resp_dams = requests.get(f"{API_BASE}/basins/{id_bacia}/dams", headers=headers, timeout=20)
            resp_dams.raise_for_status()
            barragens = resp_dams.json().get("data", [])
            print(f"   ✓ Encontradas {len(barragens)} barragens.")
        except Exception as e:
            print(f"   ❌ Erro ao obter barragens: {e}")
            continue

        estacoes = []
        for dam in barragens:
            id_dam = dam.get("id")
            time.sleep(0.4) # Pausa entre cada barragem
            
            try:
                # O endpoint realtime aceita 'limit' para trazer só as últimas X horas
                resp_rt = requests.get(f"{API_BASE}/dams/{id_dam}/realtime?limit=24", headers=headers, timeout=15)
                if resp_rt.status_code == 200:
                    rt_data = resp_rt.json().get("data", [])
                    atual = rt_data[-1] if rt_data else {}
                    
                    estacoes.append({
                        "id": id_dam,
                        "nome": dam.get("name"),
                        "lat": dam.get("coordinates", {}).get("lat", 0),
                        "lon": dam.get("coordinates", {}).get("lon", 0),
                        "rio": dam.get("river", ""),
                        "atual": atual,
                        "historico": rt_data
                    })
                    print(f"      -> ✅ {dam.get('name')}")
                else:
                    print(f"      -> ⚠️ Sem dados em tempo real para {dam.get('name')}")
            except Exception as e:
                print(f"      -> ❌ Erro em {dam.get('name')}: {e}")
        
        dados_barragens[nome_bacia] = estacoes

    # Criar o ficheiro JavaScript final
    with open("dados_nacional.js", "w", encoding="utf-8") as f:
        f.write(f"var dadosNacionais = {json.dumps(dados_barragens, ensure_ascii=False)};\n")
        f.write(f"var resumosBacias = {json.dumps(resumos_bacias, ensure_ascii=False)};")
        
    print("\n✅ Ficheiro dados_nacional.js gerado com sucesso.")
    
    # Enviar para o FTP
    ftp_host = os.getenv("FTP_HOST")
    if ftp_host and len(dados_barragens) > 0:
        print("A enviar para o qsl.net...")
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
    obter_dados()
