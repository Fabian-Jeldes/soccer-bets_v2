import asyncio
import random
import time
import json
from app.database.redis_client import redis_manager


# Equipos de ligas emergentes africanas y asiáticas para simular
MATCHES_TEMPLATE = [
    {
        "id": "match_1",
        "league": "Algerian Ligue 1",
        "home": "MC Alger",
        "away": "CR Belouizdad",
        "home_db_name": "MC Alger",            # Nombre canónico en base de datos
        "away_db_name": "CR Belouizdad",
        "minute": 10,
        "score_home": 0,
        "score_away": 0,
    },
    {
        "id": "match_2",
        "league": "Kenyan Premier League",
        "home": "Gor Mahia",
        "away": "Tusker FC",
        "home_db_name": "Gor Mahia",
        "away_db_name": "Tusker",
        "minute": 25,
        "score_home": 1,
        "score_away": 0,
    },
    {
        "id": "match_3",
        "league": "Egyptian Premier League",
        "home": "Al Ahly",
        "away": "Zamalek SC",
        "home_db_name": "Al Ahly Cairo",
        "away_db_name": "Zamalek",
        "minute": 55,
        "score_home": 1,
        "score_away": 1,
    },
    {
        "id": "match_4",
        "league": "Saudi Pro League",
        "home": "Al Hilal",
        "away": "Al Nassr",
        "home_db_name": "Al Hilal Riyadh",
        "away_db_name": "Al Nassr FC",
        "minute": 70,
        "score_home": 2,
        "score_away": 1,
    },
    {
        "id": "match_5",
        "league": "South African Premiership",
        "home": "Mamelodi Sundowns",
        "away": "Orlando Pirates",
        "home_db_name": "Mamelodi Sundowns",
        "away_db_name": "Orlando Pirates FC",
        "minute": 40,
        "score_home": 0,
        "score_away": 0,
    }
]

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
        self.matches = [dict(m) for m in MATCHES_TEMPLATE]
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._simulation_loop())

    def stop(self):
        self.running = False

    async def _simulation_loop(self):
        client = redis_manager.client
        print("Iniciando bucle de simulación de partidos y cuotas...")
        
        try:
            while self.running:
                for match in self.matches:
                    # 1. Avanzar minuto de juego
                    if random.random() < 0.3:
                        match["minute"] += 1
                        if match["minute"] > 90:
                            match["minute"] = 1  # Reiniciar partido simulado
                            match["score_home"] = 0
                            match["score_away"] = 0

                    # 2. Posibilidad de gol
                    if random.random() < 0.02:
                        if random.random() < 0.5:
                            match["score_home"] += 1
                        else:
                            match["score_away"] += 1

                    # 3. Generar cuotas simuladas para cada bookie (1, X, 2)
                    # Creamos cuotas base basadas en el minuto y marcador
                    diff = match["score_home"] - match["score_away"]
                    time_left = 95 - match["minute"]

                    # Probabilidades base crudas
                    prob_home = 0.38 + (diff * 0.25) - (match["minute"] * 0.002 if diff < 0 else 0)
                    prob_away = 0.32 - (diff * 0.25) - (match["minute"] * 0.002 if diff > 0 else 0)
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
                    g = match["score_home"] + match["score_away"]
                    if g >= 3:
                        prob_over = 0.98
                    else:
                        t_ratio = max(0.01, min(1.0, (95.0 - match["minute"]) / 95.0))
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
                            "match_id": match["id"],
                            "league": match["league"],
                            "minute": match["minute"],
                            "score": f"{match['score_home']}-{match['score_away']}",
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
                                "home_name": BOOKIES_NAMES["Bookie_A_Soft"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_A_Soft"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_home * (1 / m_a) + noise_a), 2),
                                    round(max(1.01, q_draw * (1 / m_a) - noise_a / 2), 2),
                                    round(max(1.01, q_away * (1 / m_a) - noise_a / 2), 2)
                                ]
                            }
                            odds_update["bookies"]["Bookie_B_Sharp"] = {
                                "home_name": BOOKIES_NAMES["Bookie_B_Sharp"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_B_Sharp"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_home * (1 / m_b)), 2),
                                    round(max(1.01, q_draw * (1 / m_b)), 2),
                                    round(max(1.01, q_away * (1 / m_b)), 2)
                                ]
                            }
                            odds_update["bookies"]["Bookie_C_Exchange"] = {
                                "home_name": BOOKIES_NAMES["Bookie_C_Exchange"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_C_Exchange"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_home * (1 / m_c) - noise_c / 2), 2),
                                    round(max(1.01, q_draw * (1 / m_c) + noise_c), 2),
                                    round(max(1.01, q_away * (1 / m_c) - noise_c / 2), 2)
                                ]
                            }
                        elif market_type == "OVER_UNDER":
                            odds_update["bookies"]["Bookie_A_Soft"] = {
                                "home_name": BOOKIES_NAMES["Bookie_A_Soft"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_A_Soft"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_over * (1 / m_a) + noise_a), 2),
                                    round(max(1.01, q_under * (1 / m_a) - noise_a), 2)
                                ]
                            }
                            odds_update["bookies"]["Bookie_B_Sharp"] = {
                                "home_name": BOOKIES_NAMES["Bookie_B_Sharp"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_B_Sharp"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_over * (1 / m_b)), 2),
                                    round(max(1.01, q_under * (1 / m_b)), 2)
                                ]
                            }
                            odds_update["bookies"]["Bookie_C_Exchange"] = {
                                "home_name": BOOKIES_NAMES["Bookie_C_Exchange"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_C_Exchange"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_over * (1 / m_c) - noise_c), 2),
                                    round(max(1.01, q_under * (1 / m_c) + noise_c), 2)
                                ]
                            }
                        elif market_type == "DNB":
                            odds_update["bookies"]["Bookie_A_Soft"] = {
                                "home_name": BOOKIES_NAMES["Bookie_A_Soft"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_A_Soft"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_dnb_home * (1 / m_a) + noise_a), 2),
                                    round(max(1.01, q_dnb_away * (1 / m_a) - noise_a), 2)
                                ]
                            }
                            odds_update["bookies"]["Bookie_B_Sharp"] = {
                                "home_name": BOOKIES_NAMES["Bookie_B_Sharp"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_B_Sharp"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_dnb_home * (1 / m_b)), 2),
                                    round(max(1.01, q_dnb_away * (1 / m_b)), 2)
                                ]
                            }
                            odds_update["bookies"]["Bookie_C_Exchange"] = {
                                "home_name": BOOKIES_NAMES["Bookie_C_Exchange"][match["home"]],
                                "away_name": BOOKIES_NAMES["Bookie_C_Exchange"][match["away"]],
                                "odds": [
                                    round(max(1.01, q_dnb_home * (1 / m_c) - noise_c), 2),
                                    round(max(1.01, q_dnb_away * (1 / m_c) + noise_c), 2)
                                ]
                            }

                        payload = json.dumps(odds_update)
                        await client.xadd("sport_feeds:odds", {"data": payload}, maxlen=1000)

                await asyncio.sleep(2.0)
        except Exception as e:
            print(f"ERROR EN EL BUCLE DE SIMULACIÓN: {e}")
            import traceback
            traceback.print_exc()

