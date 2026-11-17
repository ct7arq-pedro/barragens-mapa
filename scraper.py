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
    
    # 1. Obter a lista de bacias (para o resumo)
    print("1. A obter a lista de bacias...")
    try:
        resp = requests.get(f"{API_BASE}/basins", headers=headers, timeout=20)
        resp.raise_for_status()
        todas_bacias = resp.json().get("data", [])
    except Exception as e:
        print(f"Erro ao obter bacias: {e}")
        return

    # 2. Obter a lista GLOBAL de barragens (AQUI ESTÃO AS COORDENADAS!)
    print("\n2. A obter a lista global de barragens (com coordenadas)...")
    try:
        resp_dams = requests.get(f"{API_BASE}/dams", headers=headers, timeout=20)
        resp_dams.raise_for_status()
        todas_barragens_globais = resp_dams.json().get("data", [])
        print(f"   ✓ {len(todas_barragens_globais)} barragens encontradas no país.")
    except Exception as e:
        print(f"   ❌ Erro ao obter lista global de barragens: {e}")
        return

    dados_barragens = {}
    resumos_bacias = {}

    # 3. Filtrar as bacias alvo e cruzar os dados
    for bacia in todas_bacias:
        nome_bacia = bacia.get("name")
        if nome_bacia not in BACIA_ALVO:
            continue
            
        id_bacia = str(bacia.get("id"))
        print(f"\n3. A processar a bacia: {nome_bacia} (ID: {id_bacia})")
        
        # Obter Resumo da Bacia (Volume, Capacidade, %)
        try:
            resp_detalhe = requests.get(f"{API_BASE}/basins/{id_bacia}", headers=headers, timeout=15)
            if resp_detalhe.status_code == 200:
                resumos_bacias[nome_bacia] = resp_detalhe.json().get("data", {})
                print(f"   ✓ Resumo da bacia obtido.")
        except Exception as e:
            print(f"   ❌ Erro no resumo da bacia: {e}")

        time.sleep(0.5)

        # Filtrar a lista global pelas barragens que pertencem a esta bacia
        barragens_da_bacia = [d for d in todas_barragens_globais if str(d.get("basin_id")) == id_bacia]
        print(f"   ✓ Encontradas {len(barragens_da_bacia)} barragens nesta bacia.")

        estacoes = []
        for dam in barragens_da_bacia:
            id_dam = dam.get("id")
            nome_dam = dam.get("name")
            
            # Extrair coordenadas do objeto global (que sabemos que as tem)
            coords = dam.get("coordinates")
            lat, lon = 0, 0
            if coords and isinstance(coords, dict):
                lat = coords.get("lat", 0)
                lon = coords.get("lon", 0)
            
            time.sleep(0.4) # Pausa entre cada barragem
            
            try:
                # O endpoint realtime aceita 'limit' para trazer só as últimas X horas
                resp_rt = requests.get(f"{API_BASE}/dams/{id_dam}/realtime?limit=24", headers=headers, timeout=15)
                if resp_rt.status_code == 200:
                    rt_data = resp_rt.json().get("data", [])
                    atual = rt_data[-1] if rt_data else {}
                    
                    estacoes.append({
                        "id": id_dam,
                        "nome": nome_dam,
                        "lat": lat,
                        "lon": lon,
                        "rio": dam.get("river", ""),
                        "atual": atual,
                        "historico": rt_data
                    })
                    print(f"      -> ✅ {nome_dam} (lat: {lat}, lon: {lon})")
                else:
                    print(f"      -> ⚠️ Sem dados em tempo real para {nome_dam}")
            except Exception as e:
                print(f"      -> ❌ Erro em {nome_dam}: {e}")
        
        dados_barragens[nome_bacia] = estacoes

    # 4. Criar o ficheiro JavaScript final
    with open("dados_nacional.js", "w", encoding="utf-8") as f:
        f.write(f"var dadosNacionais = {json.dumps(dados_barragens, ensure_ascii=False)};\n")
        f.write(f"var resumosBacias = {json.dumps(resumos_bacias, ensure_ascii=False)};")
        
    print("\n✅ Ficheiro dados_nacional.js gerado com sucesso.")
    
    # 5. Enviar para o FTP
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
            raise e # Faz o GitHub Actions falhar e ficar vermelho (evita falhas silenciosas)

if __name__ == "__main__":
    obter_dados()
