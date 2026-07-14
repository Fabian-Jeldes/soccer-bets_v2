import asyncio
import json
import time
import urllib.request
import urllib.parse
from app.database.redis_client import redis_manager
from app.core.matcher import find_best_match
from app.core.calculations import calculate_stakes
from app.database.db import AsyncSessionLocal
from app.database.models import PredictionMarketOpportunity, CrossMarketOpportunity, SurebetOpportunity
from sqlalchemy import select
from app.config import settings

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
            
            # Guardar en base de datos la oportunidad de surebet para el historial persistente
            try:
                async with AsyncSessionLocal() as db:
                    new_db_opp = SurebetOpportunity(
                        match_id=match_id,
                        market_type=market_type,
                        roi=best_roi,
                        profit=best_combination["profit"],
                        total_spent=best_combination["total_spent"],
                        outcomes=json.dumps(best_combination["outcomes"]),
                        timestamp=time.time()
                    )
                    db.add(new_db_opp)
                    await db.commit()
            except Exception as e:
                print(f"Error escribiendo SurebetOpportunity en DB: {e}")
            
            # Alerta de Telegram si supera el ROI configurado
            if best_roi >= settings.TELEGRAM_MIN_ROI:
                await self._trigger_sports_telegram_alert(best_combination)

        # Realizar chequeo de arbitraje cruzado (Cross-Market) si aplica
        if market_type == "FULL_TIME" and canonical_match_home and canonical_match_away:
            await self._check_cross_market_arbitrage(
                match_id, league, score, minute, canonical_match_home, canonical_match_away, resolved_bookies, client
            )

    async def _check_cross_market_arbitrage(self, match_id, league, score, minute, home_team, away_team, resolved_bookies, client):
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(PredictionMarketOpportunity))
                pred_opps = result.scalars().all()
        except Exception as e:
            print(f"Error consultando PredictionMarketOpportunity en DB: {e}")
            return
            
        if not pred_opps:
            return
            
        bookie_names = list(resolved_bookies.keys())
        
        for opp in pred_opps:
            q_lower = opp.question.lower()
            h_lower = home_team.lower()
            a_lower = away_team.lower()
            
            # Buscar coincidencia difusa o substring directa de los nombres canonicales en la pregunta
            matches_home = h_lower in q_lower
            matches_away = a_lower in q_lower
            
            if not matches_home and not matches_away:
                continue
                
            odds_a = opp.odds_a  # YES
            odds_b = opp.odds_b  # NO
            
            # Encontrar las mejores cuotas tradicionales de FULL_TIME (1, X, 2)
            best_o1 = 0.0
            best_b1 = None
            best_ox = 0.0
            best_bx = None
            best_o2 = 0.0
            best_b2 = None
            
            for b_name in bookie_names:
                b_odds = resolved_bookies[b_name]["odds"]
                if len(b_odds) < 3:
                    continue
                if b_odds[0] > best_o1:
                    best_o1 = b_odds[0]
                    best_b1 = b_name
                if b_odds[1] > best_ox:
                    best_ox = b_odds[1]
                    best_bx = b_name
                if b_odds[2] > best_o2:
                    best_o2 = b_odds[2]
                    best_b2 = b_name
                    
            if not best_b1 or not best_bx or not best_b2:
                continue
                
            best_roi = -99.0
            best_combo = None
            
            if matches_home:
                # Caso A: YES (Al Hilal Gana en PM) + DRAW (Bookie) + AWAY (Bookie)
                r_a = (1.0 / odds_a) + (1.0 / best_ox) + (1.0 / best_o2)
                if r_a < 1.0:
                    roi_a = round(((1.0 - r_a) / r_a) * 100, 2)
                    res_a = calculate_stakes(1000, [odds_a, best_ox, best_o2], round_to_int=True)
                    if roi_a > best_roi:
                        best_roi = roi_a
                        best_combo = {
                            "combination_type": "YES_AND_DRAW_AWAY",
                            "sport_bookmaker": f"Draw: {best_bx}, Away: {best_b2}",
                            "outcomes": [
                                {"outcome": f"PM YES ({home_team})", "bookie": "Polymarket", "odds": odds_a, "stake": res_a["stakes"][0]},
                                {"outcome": "X (Empate)", "bookie": best_bx, "odds": best_ox, "stake": res_a["stakes"][1]},
                                {"outcome": f"2 ({away_team})", "bookie": best_b2, "odds": best_o2, "stake": res_a["stakes"][2]}
                            ]
                        }
                # Caso B: NO (Al Hilal NO Gana en PM) + HOME (Bookie)
                r_b = (1.0 / odds_b) + (1.0 / best_o1)
                if r_b < 1.0:
                    roi_b = round(((1.0 - r_b) / r_b) * 100, 2)
                    res_b = calculate_stakes(1000, [odds_b, best_o1], round_to_int=True)
                    if roi_b > best_roi:
                        best_roi = roi_b
                        best_combo = {
                            "combination_type": "NO_AND_HOME",
                            "sport_bookmaker": f"Home: {best_b1}",
                            "outcomes": [
                                {"outcome": f"PM NO ({home_team} NO Gana)", "bookie": "Polymarket", "odds": odds_b, "stake": res_b["stakes"][0]},
                                {"outcome": f"1 ({home_team})", "bookie": best_b1, "odds": best_o1, "stake": res_b["stakes"][1]}
                            ]
                        }
            elif matches_away:
                # Caso A: YES (Away team Gana en PM) + HOME (Bookie) + DRAW (Bookie)
                r_a = (1.0 / odds_a) + (1.0 / best_o1) + (1.0 / best_ox)
                if r_a < 1.0:
                    roi_a = round(((1.0 - r_a) / r_a) * 100, 2)
                    res_a = calculate_stakes(1000, [odds_a, best_o1, best_ox], round_to_int=True)
                    if roi_a > best_roi:
                        best_roi = roi_a
                        best_combo = {
                            "combination_type": "YES_AND_HOME_DRAW",
                            "sport_bookmaker": f"Home: {best_b1}, Draw: {best_bx}",
                            "outcomes": [
                                {"outcome": f"PM YES ({away_team})", "bookie": "Polymarket", "odds": odds_a, "stake": res_a["stakes"][0]},
                                {"outcome": f"1 ({home_team})", "bookie": best_b1, "odds": best_o1, "stake": res_a["stakes"][1]},
                                {"outcome": "X (Empate)", "bookie": best_bx, "odds": best_ox, "stake": res_a["stakes"][2]}
                            ]
                        }
                # Caso B: NO (Away team NO Gana en PM) + AWAY (Bookie)
                r_b = (1.0 / odds_b) + (1.0 / best_o2)
                if r_b < 1.0:
                    roi_b = round(((1.0 - r_b) / r_b) * 100, 2)
                    res_b = calculate_stakes(1000, [odds_b, best_o2], round_to_int=True)
                    if roi_b > best_roi:
                        best_roi = roi_b
                        best_combo = {
                            "combination_type": "NO_AND_AWAY",
                            "sport_bookmaker": f"Away: {best_b2}",
                            "outcomes": [
                                {"outcome": f"PM NO ({away_team} NO Gana)", "bookie": "Polymarket", "odds": odds_b, "stake": res_b["stakes"][0]},
                                {"outcome": f"2 ({away_team})", "bookie": best_b2, "odds": best_o2, "stake": res_b["stakes"][1]}
                            ]
                        }

            if best_combo and best_roi > 0:
                cross_opt = {
                    "sport_match_id": match_id,
                    "prediction_market_id": opp.event_id,
                    "teams": f"{home_team} vs {away_team}",
                    "sport_bookmaker": best_combo["sport_bookmaker"],
                    "prediction_question": opp.question,
                    "combination_type": best_combo["combination_type"],
                    "roi": best_roi,
                    "outcomes": best_combo["outcomes"],
                    "timestamp": time.time()
                }
                
                try:
                    async with AsyncSessionLocal() as db:
                        # Limpiar anteriores de este match/pregunta
                        await db.execute(
                            CrossMarketOpportunity.__table__.delete().where(
                                (CrossMarketOpportunity.sport_match_id == match_id) & 
                                (CrossMarketOpportunity.prediction_market_id == opp.event_id)
                            )
                        )
                        new_db_opp = CrossMarketOpportunity(
                            sport_match_id=match_id,
                            prediction_market_id=opp.event_id,
                            teams=cross_opt["teams"],
                            sport_bookmaker=cross_opt["sport_bookmaker"],
                            prediction_question=cross_opt["prediction_question"],
                            combination_type=cross_opt["combination_type"],
                            roi=cross_opt["roi"],
                            outcomes=json.dumps(cross_opt["outcomes"]),
                            timestamp=cross_opt["timestamp"]
                        )
                        db.add(new_db_opp)
                        await db.commit()
                except Exception as e:
                    print(f"Error escribiendo CrossMarketOpportunity en DB: {e}")
                    
                zset_key = "cross_surebets:active"
                members = await client.zrange(zset_key, 0, -1)
                for m in members:
                    try:
                        m_data = json.loads(m)
                        if m_data["sport_match_id"] == match_id and m_data["prediction_market_id"] == opp.event_id:
                            await client.zrem(zset_key, m)
                    except Exception:
                        pass
                
                await client.zadd(zset_key, {json.dumps(cross_opt): best_roi})
                
                # Publicar por PubSub
                await client.publish("surebets:stream", json.dumps({
                    "market_type": "CROSS_MARKET",
                    **cross_opt
                }))
                
                print(f"[Cross-Arb Worker] Surebet Cruzada detectada: {home_team} vs {away_team} | Combo: {best_combo['combination_type']} | ROI: +{best_roi}%")
                
                if best_roi >= settings.TELEGRAM_MIN_ROI:
                    await self._trigger_cross_telegram_alert(cross_opt)

    async def _trigger_sports_telegram_alert(self, combo):
        msg = (
            f"🔔 *SUREBET DEPORTIVA DETECTADA!*\n\n"
            f"⚽ *Partido*: {combo['teams']}\n"
            f"🏆 *Liga*: {combo['league']}\n"
            f"📈 *Mercado*: {combo['market_type']}\n"
            f"📊 *ROI*: +{combo['roi']}%\n\n"
            f"💰 *Outcomes sugeridos*:\n"
        )
        for out in combo["outcomes"]:
            msg += f"  • {out['outcome']} | Bookie: {out['bookie']} | Odds: {out['odds']} | Stake: ${out['stake']}\n"
            
        await self._send_telegram_msg(msg)

    async def _trigger_cross_telegram_alert(self, cross_opt):
        msg = (
            f"🔔 *SUREBET CRUZADA DETECTADA!*\n\n"
            f"⚽ *Partido*: {cross_opt['teams']}\n"
            f"🔮 *Pregunta PM*: {cross_opt['prediction_question']}\n"
            f"📈 *Combo*: {cross_opt['combination_type']}\n"
            f"📊 *ROI*: +{cross_opt['roi']}%\n\n"
            f"💰 *Outcomes sugeridos*:\n"
        )
        for out in cross_opt["outcomes"]:
            msg += f"  • {out['outcome']} | Bookie: {out['bookie']} | Odds: {out['odds']} | Stake: ${out['stake']}\n"
            
        await self._send_telegram_msg(msg)

    async def _send_telegram_msg(self, text: str):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            try:
                print(f"[Telegram Notifier Simulator] Mensaje que se enviaría a Telegram:\n{text}")
            except UnicodeEncodeError:
                import sys
                encoding = sys.stdout.encoding or 'ascii'
                safe_text = text.encode(encoding, errors='replace').decode(encoding)
                print(f"[Telegram Notifier Simulator] Mensaje que se enviaría a Telegram (Safe):\n{safe_text}")
            return
            
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        
        def do_request():
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = urllib.parse.urlencode({
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }).encode("utf-8")
                req = urllib.request.Request(url, data=data)
                with urllib.request.urlopen(req, timeout=5) as response:
                    response.read()
            except Exception as ex:
                print(f"Error al enviar mensaje a Telegram: {ex}")
                
        await asyncio.to_thread(do_request)


