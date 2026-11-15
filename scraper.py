<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mapa de Apoio - Cávado, Ave e Lima</title>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <!-- O Ficheiro gerado pelo GitHub -->
    <script src="dados_nacional.js" charset="UTF-8"></script>

    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; }
        #map { height: 100vh; width: 100%; background-color: #e5f0f9; }

        .popup-card { width: 320px; }
        .popup-header { background: #1a5276; color: white; padding: 10px; margin: -14px -20px 10px -20px; border-radius: 5px 5px 0 0;}
        .popup-header h3 { margin: 0; font-size: 16px; }
        .popup-header p { margin: 2px 0 0 0; font-size: 11px; color: #aed6f1;}
        .popup-data { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .popup-data div { text-align: center; }
        .popup-data strong { display: block; font-size: 18px; color: #c0392b; }
        .popup-data span { font-size: 11px; color: #666; }
        
        .leaflet-control-layers { font-size: 14px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        .leaflet-control-layers-expanded { padding: 15px; min-width: 220px; max-height: 80vh; overflow-y: auto;}
        .leaflet-control-layers label { margin-bottom: 5px; cursor: pointer; }

        #basin-panel {
            position: absolute; top: 10px; right: 10px; width: 350px; max-height: 90vh;
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(5px);
            border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1000; display: none; flex-direction: column; overflow: hidden;
            border: 1px solid #ccc;
        }
        .panel-header { background: #2c3e50; color: white; padding: 15px; position: relative; }
        .panel-header h2 { margin: 0; font-size: 18px; }
        .panel-header p { margin: 5px 0 0 0; font-size: 12px; color: #bdc3c7; }
        .close-panel { position: absolute; top: 15px; right: 15px; cursor: pointer; color: #ecf0f1; font-weight: bold; font-size: 18px; }
        
        .alert-box { padding: 15px; text-align: center; border-bottom: 1px solid #ddd; }
        .alert-title { font-weight: bold; font-size: 14px; margin-bottom: 5px; text-transform: uppercase; }
        .alert-level { font-size: 22px; font-weight: 900; color: white; padding: 10px; border-radius: 5px; text-transform: uppercase; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .alert-desc { font-size: 12px; margin-top: 5px; font-weight: bold; color: #333; }

        .dam-list { padding: 10px; overflow-y: auto; flex-grow: 1; max-height: 50vh; }
        .dam-item { display: flex; justify-content: space-between; padding: 8px; border-bottom: 1px solid #eee; font-size: 13px; }
        .dam-item:hover { background: #f9f9f9; }
        .dam-name { font-weight: bold; color: #34495e; }
        .dam-values { text-align: right; }
        .pct-high { color: #27ae60; font-weight: bold; }
        .pct-low { color: #c0392b; font-weight: bold; }
    </style>
</head>
<body>
    <div id="map"></div>

    <div id="basin-panel">
        <div class="panel-header">
            <h2 id="panel-title">Nome da Bacia</h2>
            <p id="panel-subtitle">Resumo Operacional</p>
            <span class="close-panel" onclick="fecharPainel()">✖</span>
        </div>
        
        <div id="alert-container" style="display: none;" class="alert-box">
            <div class="alert-title">Nível de Alerta (Descargas)</div>
            <div id="alert-level" class="alert-level">-</div>
            <div id="alert-desc" class="alert-desc">-</div>
        </div>

        <div class="dam-list" id="dam-list-container"></div>
    </div>

    <script>
        // 1. Mapa Base
        const map = L.map('map').setView([41.5, -8.3], 9); // Centrado no Minho/Lima/Cávado
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri'
        }).addTo(map);

        let graficoAtual = null;
        let camadaGeoJSONAtual = null; 

        // 2. Limiares de Alerta
        const limitesCavado = [
            { nivel: 'VERMELHO', min: 2000, cor: '#d32f2f', desc: 'Superior a 2000 m³/s' },
            { nivel: 'LARANJA', min: 1500, cor: '#f57c00', desc: '1500 a 2000 m³/s' },
            { nivel: 'AMARELO', min: 800, cor: '#fbc02d', desc: '800 a 1500 m³/s' },
            { nivel: 'AZUL', min: 300, cor: '#1976d2', desc: '300 a 800 m³/s' }
        ];

        const limitesAve = [
            { nivel: 'VERMELHO', min: 400, cor: '#d32f2f', desc: 'Superior a 400 m³/s' },
            { nivel: 'LARANJA', min: 300, cor: '#f57c00', desc: '300 a 400 m³/s' },
            { nivel: 'AMARELO', min: 150, cor: '#fbc02d', desc: '150 a 300 m³/s' },
            { nivel: 'AZUL', min: 75, cor: '#1976d2', desc: '75 a 150 m³/s' }
        ];

        // Mapeamento exato dos nomes das bacias para os links do GitHub
        const URLsGeoJSON = {
            "Cávado/ribeiras Costeiras": "https://raw.githubusercontent.com/ricardoccpaiva/barragenspt/master/priv/static/geojson/c%C3%A1vado/ribeiras%20costeiras.geojson",
            "Ave": "https://raw.githubusercontent.com/ricardoccpaiva/barragenspt/master/priv/static/geojson/ave.geojson",
            "Lima": "https://raw.githubusercontent.com/ricardoccpaiva/barragenspt/master/priv/static/geojson/lima.geojson"
        };

        // 3. Ícones
        function getColorIcon(pct) {
            let color = '#7f8c8d'; // Cinza para "Sem Dados"
            if (pct !== null && pct !== undefined) {
                if (pct >= 80) color = '#2980b9';
                else if (pct >= 60) color = '#3498db';
                else if (pct >= 40) color = '#f1c40f';
                else if (pct >= 20) color = '#e67e22';
                else if (pct >= 0) color = '#e74c3c';
            }
            return L.divIcon({
                className: 'custom-icon',
                html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
                iconSize: [18, 18], iconAnchor: [9, 9]
            });
        }

        // 4. Criar Marcadores
        const camadasBacias = {};
        if (typeof dadosNacionais !== 'undefined') {
            for (const [nomeBacia, estacoes] of Object.entries(dadosNacionais)) {
                // Ignorar bacias que não sejam as 3 escolhidas
                if (!URLsGeoJSON[nomeBacia]) continue; 

                camadasBacias[nomeBacia] = L.layerGroup();

                estacoes.forEach(est => {
                    const temDados = est.atual && Object.keys(est.atual).length > 0;
                    const pct = temDados && est.atual.storage_percent !== null ? est.atual.storage_percent : null;
                    const icon = getColorIcon(pct);
                    const marker = L.marker([est.lat, est.lon], { icon: icon });

                    const labels = est.historico.map(h => h.label ? h.label.split(' ')[1] : '');
                    const dataInflow = est.historico.map(h => h.inflow || 0);
                    const dataOutflow = est.historico.map(h => h.outflow || 0);

                    const txtPct = pct !== null ? pct.toFixed(1) + '%' : 'Sem Dados';
                    const txtCota = temDados && est.atual.level ? est.atual.level.toFixed(1) : '--';
                    const txtCaudal = temDados && est.atual.inflow ? est.atual.inflow.toFixed(1) : '--';
                    const txtLabel = temDados ? est.atual.label : 'Sem ligação à API';

                    const popupHTML = `
                        <div class="popup-card">
                            <div class="popup-header">
                                <h3>${est.nome}</h3>
                                <p>${nomeBacia} ${est.rio ? '| Rio ' + est.rio : ''}</p>
                            </div>
                            <div class="popup-data">
                                <div><strong>${txtPct}</strong><span>Armazenamento</span></div>
                                <div><strong>${txtCota}</strong><span>Cota (m)</span></div>
                                <div><strong>${txtCaudal}</strong><span>Caudal (m³/s)</span></div>
                            </div>
                            <div style="font-size: 10px; text-align: right; color: #888; margin-bottom: 5px;">Atualizado: ${txtLabel}</div>
                            <div style="height: 150px; width: 100%;"><canvas id="chart-${est.id}"></canvas></div>
                        </div>
                    `;

                    marker.bindPopup(popupHTML, { maxWidth: 350 });
                    
                    marker.on('popupopen', function() {
                        if (graficoAtual) { graficoAtual.destroy(); }
                        const ctx = document.getElementById(`chart-${est.id}`).getContext('2d');
                        graficoAtual = new Chart(ctx, {
                            type: 'line',
                            data: { labels: labels, datasets: [
                                { label: 'Afluente', data: dataInflow, borderColor: '#8b5cf6', borderWidth: 1, pointRadius: 0, tension: 0.1 },
                                { label: 'Efluente', data: dataOutflow, borderColor: '#10b981', borderWidth: 1, pointRadius: 0, tension: 0.1 }
                            ]},
                            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { beginAtZero: true, ticks: { font: { size: 9 } } } } }
                        });
                    });

                    marker.addTo(camadasBacias[nomeBacia]);
                });
            }
        }

        // 5. Menu Lateral
        L.control.layers(null, camadasBacias, { collapsed: false, position: 'topleft' }).addTo(map);

        // 6. Eventos de Camada (GeoJSON e Painel)
        map.on('overlayadd', function(e) {
            const baciaSelecionada = e.name;
            abrirPainelBacia(baciaSelecionada, dadosNacionais[baciaSelecionada]);

            if (camadaGeoJSONAtual) { map.removeLayer(camadaGeoJSONAtual); }
            
            const urlGeoJSON = URLsGeoJSON[baciaSelecionada];
            if (!urlGeoJSON) return;

            // Desenhar o GeoJSON do GitHub
            fetch(urlGeoJSON)
                .then(res => res.json())
                .then(geoData => {
                    camadaGeoJSONAtual = L.geoJSON(geoData, {
                        style: { color: '#2980b9', weight: 2, fillColor: '#3498db', fillOpacity: 0.15 }
                    }).addTo(map);
                })
                .catch(err => console.error("Erro ao carregar GeoJSON:", err));
        });

        map.on('overlayremove', function(e) {
            fecharPainel();
            if (camadaGeoJSONAtual) { 
                map.removeLayer(camadaGeoJSONAtual); 
                camadaGeoJSONAtual = null;
            }
        });

        // 7. Painel Lateral (Resumo e Alertas)
        function abrirPainelBacia(nomeBacia, estacoes) {
            document.getElementById('basin-panel').style.display = 'flex';
            document.getElementById('panel-title').innerText = nomeBacia;
            document.getElementById('panel-subtitle').innerText = `${estacoes.length} estações monitorizadas`;

            const alertContainer = document.getElementById('alert-container');
            alertContainer.style.display = 'none'; 

            let somaCaudal = 0;
            let tipoAlerta = null;

            if (nomeBacia.includes("Cávado")) {
                estacoes.forEach(est => {
                    if (est.nome.includes("Caniçada") || est.nome.includes("Vilarinho das Furnas")) {
                        somaCaudal += (est.atual.outflow || 0);
                    }
                });
                tipoAlerta = limitesCavado;
                document.getElementById('panel-subtitle').innerText += " | Cálculo: Caniçada + Vilarinho";
            } 
            else if (nomeBacia.includes("Ave")) {
                estacoes.forEach(est => {
                    if (est.nome.includes("Guilhofrei")) {
                        somaCaudal += (est.atual.outflow || 0);
                    }
                });
                tipoAlerta = limitesAve;
                document.getElementById('panel-subtitle').innerText += " | Cálculo: Guilhofrei";
            }

            if (tipoAlerta) {
                alertContainer.style.display = 'block';
                let alertaAtivo = null;
                for (let limite of tipoAlerta) {
                    if (somaCaudal >= limite.min) { alertaAtivo = limite; break; }
                }

                const alertLevelDiv = document.getElementById('alert-level');
                const alertDescDiv = document.getElementById('alert-desc');

                if (alertaAtivo) {
                    alertLevelDiv.innerText = alertaAtivo.nivel;
                    alertLevelDiv.style.backgroundColor = alertaAtivo.cor;
                    alertDescDiv.innerText = `${alertaAtivo.desc} (Atual: ${somaCaudal.toFixed(1)} m³/s)`;
                } else {
                    alertLevelDiv.innerText = "NORMAL";
                    alertLevelDiv.style.backgroundColor = '#27ae60';
                    alertDescDiv.innerText = `Abaixo dos limites de alerta (Atual: ${somaCaudal.toFixed(1)} m³/s)`;
                }
            }

            const listContainer = document.getElementById('dam-list-container');
            listContainer.innerHTML = '';
            const estacoesOrdenadas = [...estacoes].sort((a, b) => a.nome.localeCompare(b.nome));

            estacoesOrdenadas.forEach(est => {
                const pct = est.atual.storage_percent;
                const inflow = est.atual.inflow;
                const outflow = est.atual.outflow;

                const txtPct = (pct !== null && pct !== undefined) ? pct.toFixed(1) + '%' : '--';
                const txtCaudal = (inflow !== null && inflow !== undefined) ? inflow.toFixed(1) : '--';
                const txtOutflow = (outflow !== null && outflow !== undefined) ? outflow.toFixed(1) : '--';
                
                let pctClass = '';
                if (pct !== null && pct !== undefined) {
                    if (pct >= 80) pctClass = 'pct-high';
                    if (pct <= 20) pctClass = 'pct-low';
                }

                listContainer.innerHTML += `
                    <div class="dam-item">
                        <div>
                            <div class="dam-name">${est.nome}</div>
                            <div style="font-size: 10px; color: #7f8c8d;">${est.rio ? 'Rio ' + est.rio : 'Albufeira'}</div>
                        </div>
                        <div class="dam-values">
                            <div class="${pctClass}">${txtPct}</div>
                            <div style="font-size: 10px; color: #555;">Aflu: ${txtCaudal} | Eflu: ${txtOutflow}</div>
                        </div>
                    </div>
                `;
            });
        }

        function fecharPainel() {
            document.getElementById('basin-panel').style.display = 'none';
        }
    </script>
</body>
</html>
