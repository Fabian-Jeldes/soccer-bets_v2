import asyncio
import random
import time
import json
from app.database.redis_client import redis_manager
from app.database.db import AsyncSessionLocal
from app.database.models import Match
from sqlalchemy import select
from app.config import settings

# Nombres alternativos que envían los distintos "bookies" (para probar el Fuzzy Matching)
BOOKIES_NAMES = {
    "Bookie_A_Soft": {
        "MC Alger": "MC Alger",
        "CR Belouizdad": "CR Belouizdad",
        "Gor Mahia": "Gor Mahia FC",
        "Tusker FC": "Tusker FC",
        "Al Ahly": "Al Ahly SC",
        "Zamalek SC": "Zamalek",
        "Al Hilal": "Al Hilal",
        "Al Nassr": "Al Nassr",
        "Mamelodi Sundowns": "Mamelodi Sundowns FC",
        "Orlando Pirates": "Orlando Pirates"
    },
    "Bookie_B_Sharp": {
        "MC Alger": "MC Algiers",
        "CR Belouizdad": "Belouizdad",
        "Gor Mahia": "Gor Mahia",
        "Tusker FC": "Tusker",
        "Al Ahly": "Al Ahly Cairo",
        "Zamalek SC": "Zamalek SC",
        "Al Hilal": "Al-Hilal Riyadh",
        "Al Nassr": "Al-Nassr FC",
        "Mamelodi Sundowns": "Sundowns",
        "Orlando Pirates": "Orlando Pirates FC"
    },
    "Bookie_C_Exchange": {
        "MC Alger": "MC Alger",
        "CR Belouizdad": "CR Belouizdad",
        "Gor Mahia": "Gor Mahia",
        "Tusker FC": "Tusker FC",
        "Al Ahly": "Al Ahly",
        "Zamalek SC": "Zamalek",
        "Al Hilal": "Al Hilal",
        "Al Nassr": "Al Nassr",
        "Mamelodi Sundowns": "Mamelodi Sundowns",
        "Orlando Pirates": "Orlando Pirates"
    }
}

class InPlaySimulator:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._simulation_loop())

    def stop(self):
        self.running = False

    async def _simulation_loop(self):
        client = redis_manager.client
        while not client:
            await asyncio.sleep(0.5)
            client = redis_manager.client
            
        print("Iniciando bucle de simulación de partidos y cuotas (base de datos)...")
        
        try:
            while self.running:
                now = time.time()
                async with AsyncSessionLocal() as db:
                    # 1. Obtener partidos que están actualmente en juego
                    stmt_active = select(Match).where(Match.status == "IN_PLAY")
                    res_active = await db.execute(stmt_active)
                    active_matches = list(res_active.scalars().all())
                    
                    # 2. Si hay menos de 3 partidos activos, activar los programados que ya deban empezar
                    if len(active_matches) < 3:
                        stmt_scheduled = select(Match).where(Match.status == "SCHEDULED").order_by(Match.start_time.asc())
                        res_scheduled = await db.execute(stmt_scheduled)
                        scheduled_matches = list(res_scheduled.scalars().all())
                        
                        for sm in scheduled_matches:
                            # Si es tiempo de iniciar el partido programado o si NO hay NINGÚN partido activo
                            if sm.start_time <= now or len(active_matches) == 0:
                                sm.status = "IN_PLAY"
                                sm.minute = 1
                                sm.score = "0-0"
                                sm.start_time = now  # Ajustar hora de inicio al momento actual
                                sm.updated_at = now
                                db.add(sm)
                                active_matches.append(sm)
                                print(f"[Simulador] Partido iniciado: {sm.home_team} vs {sm.away_team}")
                                if len(active_matches) >= 3:
                                    break
                                    
                    # 3. Procesar y actualizar cada partido activo
                    for match in active_matches:
                        try:
                            score_home, score_away = map(int, match.score.split("-"))
                        except Exception:
                            score_home, score_away = 0, 0
                            
                        # Avanzar el partido de manera probabilística
                        if random.random() < 0.3:
                            match.minute += 1
                            match.updated_at = now
                            
                            # Finalizar el partido si supera los 90 minutos
                            if match.minute > 90:
                                match.status = "FINISHED"
                                match.minute = 90
                                match.updated_at = now
                                
                                # Programar nuevo partido en el futuro para los mismos equipos
                                new_start = now + random.uniform(300, 1800)  # en 5 a 30 minutos
                                clean_home = match.home_team.replace(" ", "_").lower()
                                clean_away = match.away_team.replace(" ", "_").lower()
                                new_id = f"upcoming_{clean_home}_{clean_away}_{int(new_start)}"
                                
                                new_upcoming = Match(
                                    id=new_id,
                                    league=match.league,
                                    home_team=match.home_team,
                                    away_team=match.away_team,
                                    score="0-0",
                                    minute=0,
                                    status="SCHEDULED",
                                    start_time=new_start,
                                    created_at=now,
                                    updated_at=now
                                )
                                db.add(new_upcoming)
                                db.add(match)
                                print(f"[Simulador] Partido finalizado: {match.home_team} vs {match.away_team} ({match.score}). Nuevo partido programado.")
                                continue
                                
                        # Posibilidad de anotación de gol
                        if random.random() < 0.02:
                            if random.random() < 0.5:
                                score_home += 1
                            else:
                                score_away += 1
                            match.score = f"{score_home}-{score_away}"
                            match.updated_at = now
                            
                        db.add(match)
                        
                        # Generar cuotas para el partido (FULL_TIME, OVER_UNDER, DNB) y enviar a Redis
                        await self._generate_and_publish_odds(match, score_home, score_away, client)
                        
                    await db.commit()
                
                # Esperar el intervalo configurado
                await asyncio.sleep(settings.SIMULATION_SPEED_SEC)
        except Exception as e:
            print(f"ERROR EN EL BUCLE DE SIMULACIÓN BD: {e}")
            import traceback
            traceback.print_exc()

    async def _generate_and_publish_odds(self, match, score_home, score_away, client):
        diff = score_home - score_away
        time_left = 95 - match.minute

        # Probabilidades base crudas
        prob_home = 0.38 + (diff * 0.25) - (match.minute * 0.002 if diff < 0 else 0)
        prob_away = 0.32 - (diff * 0.25) - (match.minute * 0.002 if diff > 0 else 0)
        prob_draw = 1.0 - (prob_home + prob_away)

        # Mantener límites lógicos
        prob_home = max(0.05, min(0.90, prob_home))
        prob_away = max(0.05, min(0.90, prob_away))
        prob_draw = max(0.05, min(0.90, prob_draw))

        # Normalizar
        total = prob_home + prob_away + prob_draw
        prob_home /= total
        prob_away /= total
        prob_draw /= total

        # Cuota justa
        q_home = 1.0 / prob_home
        q_draw = 1.0 / prob_draw
        q_away = 1.0 / prob_away

        # Generar probabilidades de Over/Under (más o menos de 2.5 goles)
        g = score_home + score_away
        if g >= 3:
            prob_over = 0.98
        else:
            t_ratio = max(0.01, min(1.0, (95.0 - match.minute) / 95.0))
            if g == 0:
                prob_over = 0.35 * t_ratio
            elif g == 1:
                prob_over = 0.55 * t_ratio
            else:  # g == 2
                prob_over = 0.75 * t_ratio
        prob_under = 1.0 - prob_over
        prob_over = max(0.05, min(0.95, prob_over))
        prob_under = max(0.05, min(0.95, prob_under))
        q_over = 1.0 / prob_over
        q_under = 1.0 / prob_under

        # Generar probabilidades de Draw No Bet (DNB)
        total_home_away = prob_home + prob_away
        if total_home_away <= 0:
            total_home_away = 1.0
        prob_dnb_home = prob_home / total_home_away
        prob_dnb_away = prob_away / total_home_away
        prob_dnb_home = max(0.05, min(0.95, prob_dnb_home))
        prob_dnb_away = max(0.05, min(0.95, prob_dnb_away))
        q_dnb_home = 1.0 / prob_dnb_home
        q_dnb_away = 1.0 / prob_dnb_away

        for market_type in ["FULL_TIME", "OVER_UNDER", "DNB"]:
            odds_update = {
                "match_id": match.id,
                "league": match.league,
                "minute": match.minute,
                "score": f"{score_home}-{score_away}",
                "timestamp": time.time(),
                "market_type": market_type,
                "bookies": {}
            }

            # Bookie A (Soft) - lento en ajustar, margen 8%
            m_a = 1.08
            noise_a = random.uniform(-0.25, 0.25) if random.random() < 0.40 else 0.0

            # Bookie B (Sharp) - rápido, margen 2%
            m_b = 1.02

            # Bookie C (Exchange) - dinámico, margen 1.5%
            m_c = 1.015
            noise_c = random.uniform(-0.15, 0.15) if random.random() < 0.35 else 0.0

            if market_type == "FULL_TIME":
                odds_update["bookies"]["Bookie_A_Soft"] = {
                    "home_name": BOOKIES_NAMES["Bookie_A_Soft"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_A_Soft"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_home * (1 / m_a) + noise_a), 2),
                        round(max(1.01, q_draw * (1 / m_a) - noise_a / 2), 2),
                        round(max(1.01, q_away * (1 / m_a) - noise_a / 2), 2)
                    ]
                }
                odds_update["bookies"]["Bookie_B_Sharp"] = {
                    "home_name": BOOKIES_NAMES["Bookie_B_Sharp"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_B_Sharp"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_home * (1 / m_b)), 2),
                        round(max(1.01, q_draw * (1 / m_b)), 2),
                        round(max(1.01, q_away * (1 / m_b)), 2)
                    ]
                }
                odds_update["bookies"]["Bookie_C_Exchange"] = {
                    "home_name": BOOKIES_NAMES["Bookie_C_Exchange"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_C_Exchange"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_home * (1 / m_c) - noise_c / 2), 2),
                        round(max(1.01, q_draw * (1 / m_c) + noise_c), 2),
                        round(max(1.01, q_away * (1 / m_c) - noise_c / 2), 2)
                    ]
                }
            elif market_type == "OVER_UNDER":
                odds_update["bookies"]["Bookie_A_Soft"] = {
                    "home_name": BOOKIES_NAMES["Bookie_A_Soft"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_A_Soft"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_over * (1 / m_a) + noise_a), 2),
                        round(max(1.01, q_under * (1 / m_a) - noise_a), 2)
                    ]
                }
                odds_update["bookies"]["Bookie_B_Sharp"] = {
                    "home_name": BOOKIES_NAMES["Bookie_B_Sharp"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_B_Sharp"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_over * (1 / m_b)), 2),
                        round(max(1.01, q_under * (1 / m_b)), 2)
                    ]
                }
                odds_update["bookies"]["Bookie_C_Exchange"] = {
                    "home_name": BOOKIES_NAMES["Bookie_C_Exchange"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_C_Exchange"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_over * (1 / m_c) - noise_c), 2),
                        round(max(1.01, q_under * (1 / m_c) + noise_c), 2)
                    ]
                }
            elif market_type == "DNB":
                odds_update["bookies"]["Bookie_A_Soft"] = {
                    "home_name": BOOKIES_NAMES["Bookie_A_Soft"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_A_Soft"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_dnb_home * (1 / m_a) + noise_a), 2),
                        round(max(1.01, q_dnb_away * (1 / m_a) - noise_a), 2)
                    ]
                }
                odds_update["bookies"]["Bookie_B_Sharp"] = {
                    "home_name": BOOKIES_NAMES["Bookie_B_Sharp"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_B_Sharp"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_dnb_home * (1 / m_b)), 2),
                        round(max(1.01, q_dnb_away * (1 / m_b)), 2)
                    ]
                }
                odds_update["bookies"]["Bookie_C_Exchange"] = {
                    "home_name": BOOKIES_NAMES["Bookie_C_Exchange"].get(match.home_team, match.home_team),
                    "away_name": BOOKIES_NAMES["Bookie_C_Exchange"].get(match.away_team, match.away_team),
                    "odds": [
                        round(max(1.01, q_dnb_home * (1 / m_c) - noise_c), 2),
                        round(max(1.01, q_dnb_away * (1 / m_c) + noise_c), 2)
                    ]
                }

            payload = json.dumps(odds_update)
            await client.xadd("sport_feeds:odds", {"data": payload}, maxlen=1000)
