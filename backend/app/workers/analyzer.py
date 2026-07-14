import asyncio
import json
import time
from app.database.redis_client import redis_manager
from app.core.matcher import find_best_match
from app.core.calculations import calculate_stakes

# Lista canonical de equipos en el sistema
CANONICAL_TEAMS = [
    "MC Alger", "CR Belouizdad",
    "Gor Mahia", "Tusker FC",
    "Al Ahly", "Zamalek SC",
    "Al Hilal", "Al Nassr",
    "Mamelodi Sundowns", "Orlando Pirates"
]

class SurebetAnalyzer:
    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        print("SurebetAnalyzer: Worker iniciado en segundo plano.")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        print("SurebetAnalyzer: Worker detenido.")

    async def _run_loop(self):
        client = redis_manager.client
        while not client:
            await asyncio.sleep(0.5)
            client = redis_manager.client
            
        last_id = "0"  # Empezar leyendo desde el inicio del stream
        stream_name = "sport_feeds:odds"
        zset_key = "surebets:active"
        
        print("SurebetAnalyzer: Esperando y consumiendo cuotas de 'sport_feeds:odds'...")
        
        while self.running:
            try:
                # Leer del stream (bloquear por 1000ms si no hay mensajes nuevos)
                response = await client.xread(streams={stream_name: last_id}, count=10, block=1000)
                if not response:
                    continue
                    
                for stream, messages in response:
                    for message_id, data in messages:
                        last_id = message_id  # Actualizar last_id para evitar re-lecturas
                        
                        raw_payload = data.get("data")
                        if not raw_payload:
                            continue
                            
                        odds_update = json.loads(raw_payload)
                        await self._process_odds_update(odds_update, client)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error en SurebetAnalyzer loop: {e}")
                await asyncio.sleep(2.0)

    async def _process_odds_update(self, odds_update, client):
        match_id = odds_update["match_id"]
        league = odds_update["league"]
        minute = odds_update["minute"]
        score = odds_update["score"]
        market_type = odds_update.get("market_type", "FULL_TIME")
        
        resolved_bookies = {}
        canonical_match_home = None
        canonical_match_away = None
        
        # Unificar nombres de equipos usando matcher.py para cada casa de apuestas
        for bookie_name, bookie_data in odds_update["bookies"].items():
            home_raw = bookie_data["home_name"]
            away_raw = bookie_data["away_name"]
            
            # Fuzzy match para Home y Away
            match_home = find_best_match(home_raw, CANONICAL_TEAMS, threshold=70.0)
            match_away = find_best_match(away_raw, CANONICAL_TEAMS, threshold=70.0)
            
            if match_home and match_away:
                home_canon = match_home[0]
                away_canon = match_away[0]
                
                # Guardar el primer match canonical que resolvamos para usarlo como referencia
                if not canonical_match_home:
                    canonical_match_home = home_canon
                    canonical_match_away = away_canon
                    
                # Si coincide con la referencia canonical, consideramos esta cuota válida
                if home_canon == canonical_match_home and away_canon == canonical_match_away:
                    resolved_bookies[bookie_name] = {
                        "odds": bookie_data["odds"],
                        "home_name": home_canon,
                        "away_name": away_canon
                    }
            else:
                print(f"[FuzzyMatch Warning] No se pudo unificar equipos para {bookie_name}: '{home_raw}' o '{away_raw}'")

        if len(resolved_bookies) < 2:
            # Necesitamos al menos 2 casas de apuestas que coincidan para realizar arbitraje
            return

        # Calcular surebets cruzando las cuotas de los bookies unificados
        best_roi = -99.0
        best_combination = None
        bookie_names = list(resolved_bookies.keys())
        
        if market_type == "FULL_TIME":
            # Probar todas las combinaciones 1X2 entre las casas de apuestas resueltas
            for b_home in bookie_names:
                for b_draw in bookie_names:
                    for b_away in bookie_names:
                        # Asegurarse de tener 3 cuotas antes de indexar
                        if len(resolved_bookies[b_home]["odds"]) < 3 or len(resolved_bookies[b_draw]["odds"]) < 3 or len(resolved_bookies[b_away]["odds"]) < 3:
                            continue
                        o_home = resolved_bookies[b_home]["odds"][0]
                        o_draw = resolved_bookies[b_draw]["odds"][1]
                        o_away = resolved_bookies[b_away]["odds"][2]
                        
                        res = calculate_stakes(1000, [o_home, o_draw, o_away], round_to_int=True)
                        if res["has_arbitrage"] and res["roi"] > best_roi:
                            best_roi = res["roi"]
                            best_combination = {
                                "match_id": match_id,
                                "league": league,
                                "market_type": market_type,
                                "teams": f"{canonical_match_home} vs {canonical_match_away}",
                                "score": score,
                                "minute": minute,
                                "outcomes": [
                                    {"outcome": "1 (Local)", "bookie": b_home, "odds": o_home, "stake": res["stakes"][0]},
                                    {"outcome": "X (Empate)", "bookie": b_draw, "odds": o_draw, "stake": res["stakes"][1]},
                                    {"outcome": "2 (Visitante)", "bookie": b_away, "odds": o_away, "stake": res["stakes"][2]}
                                ],
                                "total_spent": res["total_spent"],
                                "profit": res["profit"],
                                "roi": res["roi"],
                                "timestamp": time.time()
                            }
        elif market_type == "OVER_UNDER":
            # Probar combinaciones Over 2.5 y Under 2.5
            for b_over in bookie_names:
                for b_under in bookie_names:
                    if len(resolved_bookies[b_over]["odds"]) < 2 or len(resolved_bookies[b_under]["odds"]) < 2:
                        continue
                    o_over = resolved_bookies[b_over]["odds"][0]
                    o_under = resolved_bookies[b_under]["odds"][1]
                    
                    res = calculate_stakes(1000, [o_over, o_under], round_to_int=True)
                    if res["has_arbitrage"] and res["roi"] > best_roi:
                        best_roi = res["roi"]
                        best_combination = {
                            "match_id": match_id,
                            "league": league,
                            "market_type": market_type,
                            "teams": f"{canonical_match_home} vs {canonical_match_away}",
                            "score": score,
                            "minute": minute,
                            "outcomes": [
                                {"outcome": "Over 2.5 Goles", "bookie": b_over, "odds": o_over, "stake": res["stakes"][0]},
                                {"outcome": "Under 2.5 Goles", "bookie": b_under, "odds": o_under, "stake": res["stakes"][1]}
                            ],
                            "total_spent": res["total_spent"],
                            "profit": res["profit"],
                            "roi": res["roi"],
                            "timestamp": time.time()
                        }
        elif market_type == "DNB":
            # Probar combinaciones Home DNB y Away DNB
            for b_home in bookie_names:
                for b_away in bookie_names:
                    if len(resolved_bookies[b_home]["odds"]) < 2 or len(resolved_bookies[b_away]["odds"]) < 2:
                        continue
                    o_home = resolved_bookies[b_home]["odds"][0]
                    o_away = resolved_bookies[b_away]["odds"][1]
                    
                    res = calculate_stakes(1000, [o_home, o_away], round_to_int=True)
                    if res["has_arbitrage"] and res["roi"] > best_roi:
                        best_roi = res["roi"]
                        best_combination = {
                            "match_id": match_id,
                            "league": league,
                            "market_type": market_type,
                            "teams": f"{canonical_match_home} vs {canonical_match_away}",
                            "score": score,
                            "minute": minute,
                            "outcomes": [
                                {"outcome": f"1 DNB ({canonical_match_home})", "bookie": b_home, "odds": o_home, "stake": res["stakes"][0]},
                                {"outcome": f"2 DNB ({canonical_match_away})", "bookie": b_away, "odds": o_away, "stake": res["stakes"][1]}
                            ],
                            "total_spent": res["total_spent"],
                            "profit": res["profit"],
                            "roi": res["roi"],
                            "timestamp": time.time()
                        }

        zset_key = "surebets:active"
        
        # Siempre limpiar cualquier versión anterior de este partido/mercado en el ZSet para evitar duplicados
        members = await client.zrange(zset_key, 0, -1)
        for m in members:
            try:
                sb_data = json.loads(m)
                if sb_data["match_id"] == match_id and sb_data.get("market_type", "FULL_TIME") == market_type:
                    await client.zrem(zset_key, m)
            except Exception:
                pass

        if best_combination and best_roi > 0:
            # Se ha detectado una oportunidad de arbitraje real
            print(f"[Surebet Worker] Surebet detectada: {canonical_match_home} vs {canonical_match_away} | Mercado: {market_type} | ROI: +{best_roi}%")
            
            # Almacenar en Redis Sorted Set ordenado por ROI
            await client.zadd(zset_key, {json.dumps(best_combination): best_roi})
            # Publicar en el canal PubSub
            await client.publish("surebets:stream", json.dumps(best_combination))

