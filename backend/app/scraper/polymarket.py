import asyncio
import random
import time
import json
from app.database.redis_client import redis_manager
from app.database.db import AsyncSessionLocal
from app.database.models import PredictionMarketOpportunity

# Lista de preguntas realistas para simular mercados de predicción
PREDICTION_QUESTIONS_TEMPLATE = [
    {
        "event_id": "poly_1",
        "question": "Will Al Hilal win the Saudi Pro League 2025/2026?",
        "outcome_a": "Yes",
        "outcome_b": "No"
    },
    {
        "event_id": "poly_2",
        "question": "Will Zamalek SC win the Egyptian Premier League?",
        "outcome_a": "Yes",
        "outcome_b": "No"
    },
    {
        "event_id": "poly_3",
        "question": "Will Cristiano Ronaldo score 30+ goals in the Saudi Pro League this season?",
        "outcome_a": "Yes",
        "outcome_b": "No"
    },
    {
        "event_id": "poly_4",
        "question": "Will Gor Mahia qualify for the CAF Champions League group stage?",
        "outcome_a": "Yes",
        "outcome_b": "No"
    },
    {
        "event_id": "poly_5",
        "question": "Will Orlando Pirates win the South African Premiership?",
        "outcome_a": "Yes",
        "outcome_b": "No"
    }
]

class PolymarketScraper:
    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._scrape_loop())
        print("PolymarketScraper: Bucle de monitoreo iniciado.")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        print("PolymarketScraper: Bucle de monitoreo detenido.")

    async def _scrape_loop(self):
        # Intentamos obtener datos reales o simulados, y calcular oportunidades de arbitraje.
        # Guardamos las oportunidades en la base de datos sqlite/postgres y las exponemos.
        while self.running:
            try:
                await self._process_markets()
                await asyncio.sleep(5.0)  # Chequear cada 5 segundos
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error en PolymarketScraper: {e}")
                await asyncio.sleep(5.0)

    async def _process_markets(self):
        # Simulamos/calculamos cuotas para Polymarket
        # En Polymarket las cuotas se transan en centavos (0-100 centavos por contrato).
        # Si Yes + No < 100 centavos, hay arbitraje directo.
        
        async with AsyncSessionLocal() as db:
            # Primero, limpiar oportunidades anteriores para no acumular basura obsoleta
            await db.execute(
                # Borrar todas las oportunidades anteriores
                # Para SQLite/PostgreSQL usando SQLAlchemy 2.0:
                PredictionMarketOpportunity.__table__.delete()
            )
            await db.commit()

            for item in PREDICTION_QUESTIONS_TEMPLATE:
                # Generar precios de contratos que a veces sumen menos de 100 centavos ($1)
                # Ejemplo: Yes = 51c, No = 46c. Suma = 97c. ROI = (1.00 / 0.97 - 1) * 100
                price_a_cents = random.randint(30, 70)
                # Ocasionalmente crear un surebet (suma < 100)
                if random.random() < 0.60:
                    price_b_cents = 100 - price_a_cents - random.randint(2, 6)
                else:
                    price_b_cents = 100 - price_a_cents + random.randint(1, 4)

                price_b_cents = max(5, min(95, price_b_cents))
                price_a_cents = max(5, min(95, price_a_cents))

                sum_price = price_a_cents + price_b_cents
                if sum_price < 100:
                    # Encontrado Arbitraje!
                    # Convertir a cuotas decimales
                    # odds = 1 / (precio_en_dolares)
                    odds_a = round(100.0 / price_a_cents, 2)
                    odds_b = round(100.0 / price_b_cents, 2)
                    
                    # Calcular ROI real
                    # Inversión total necesaria para garantizar $1 de retorno
                    # Stake_a = 1 / odds_a, Stake_b = 1 / odds_b
                    # Total spent = sum_price / 100.0
                    total_spent = sum_price / 100.0
                    roi = round(((1.0 - total_spent) / total_spent) * 100, 2)

                    opportunity = PredictionMarketOpportunity(
                        event_id=item["event_id"],
                        question=item["question"],
                        outcome_a=item["outcome_a"],
                        outcome_b=item["outcome_b"],
                        odds_a=odds_a,
                        odds_b=odds_b,
                        roi=roi,
                        timestamp=time.time()
                    )
                    db.add(opportunity)
            
            await db.commit()
