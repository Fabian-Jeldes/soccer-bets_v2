import asyncio
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database.redis_client import redis_manager
from app.scraper.simulator import InPlaySimulator
from app.workers.analyzer import SurebetAnalyzer
from app.scraper.polymarket import PolymarketScraper
from app.database.db import init_db, get_db
from app.database.models import Bet, PredictionMarketOpportunity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

# Inicializar simulador, worker de análisis y scraper de Polymarket
simulator = InPlaySimulator()
analyzer = SurebetAnalyzer()
polymarket_scraper = PolymarketScraper()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Conectar a Redis al iniciar
    redis_client = await redis_manager.connect()
    print("Conectado a Redis exitosamente.")
    
    # Inicializar Base de Datos
    await init_db()
    print("Base de Datos inicializada.")
    
    # Iniciar simulador de cuotas
    await simulator.start()
    print("Simulador de cuotas iniciado.")
    
    # Iniciar scraper de Polymarket
    await polymarket_scraper.start()
    print("Scraper de Polymarket iniciado.")
    
    # Iniciar worker de análisis
    await analyzer.start()
    print("Worker de análisis de surebets iniciado.")
    
    yield
    
    # Detener y desconectar al apagar
    analyzer.stop()
    polymarket_scraper.stop()
    simulator.stop()
    await redis_manager.disconnect()
    print("Desconectado de Redis.")



app = FastAPI(
    title="Soccer Bets Algorithmic Arbitrage Engine",
    version="2.0",
    lifespan=lifespan
)

# Permitir CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta básica de estado
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "redis_host": settings.REDIS_HOST,
        "ws_port": settings.WS_PORT
    }

# Endpoint para listar surebets activas actuales
@app.get("/api/surebets")
async def get_active_surebets():
    client = redis_manager.client
    if not client:
        return []
    
    # Obtener todas las surebets ordenadas de mayor a menor ROI
    raw_surebets = await client.zrevrange("surebets:active", 0, -1)
    surebets = []
    for sb in raw_surebets:
        try:
            surebets.append(json.loads(sb))
        except json.JSONDecodeError:
            pass
    return surebets

# WebSocket para recibir actualizaciones en vivo de surebets
@app.websocket("/ws/surebets")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"Cliente WebSocket conectado desde: {websocket.client}")
    
    # Crear cliente Redis Pub/Sub específico para esta conexión
    pubsub = redis_manager.client.pubsub()
    await pubsub.subscribe("surebets:stream")
    
    # Enviar el estado inicial de surebets activas al cliente recién conectado
    initial_surebets = await get_active_surebets()
    await websocket.send_json({"type": "initial_state", "data": initial_surebets})
    
    async def listen_pubsub():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json({"type": "update", "data": data})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error en PubSub listener: {e}")

    # Correr el listener en background
    listener_task = asyncio.create_task(listen_pubsub())
    
    try:
        # Mantener la conexión abierta y procesar mensajes entrantes (ping/pong u otros)
        while True:
            # Esperar mensajes (en caso de que el frontend envíe algo, o solo para detectar desconexión)
            data = await websocket.receive_text()
            # Opcional: eco o procesar comandos
    except WebSocketDisconnect:
        print("Cliente WebSocket desconectado.")
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe("surebets:stream")
        await pubsub.close()

# --- ENDPOINTS DE PERSISTENCIA Y LEDGER DE APUESTAS ---

class BetOutcomeInput(BaseModel):
    outcome: str
    bookie: str
    odds: float
    stake: float

class BetCreateInput(BaseModel):
    match_id: str
    teams: str
    league: str
    outcomes: list[BetOutcomeInput]
    total_spent: float
    expected_profit: float

# Registrar apuesta colocada
@app.post("/api/bets")
async def create_bet(bet_data: BetCreateInput, db: AsyncSession = Depends(get_db)):
    outcomes_list = [out.model_dump() for out in bet_data.outcomes]
    outcomes_json = json.dumps(outcomes_list)
    db_bet = Bet(
        match_id=bet_data.match_id,
        teams=bet_data.teams,
        league=bet_data.league,
        outcomes=outcomes_json,
        total_spent=bet_data.total_spent,
        expected_profit=bet_data.expected_profit,
        status="PENDING",
        placed_at=time.time()
    )
    db.add(db_bet)
    await db.commit()
    await db.refresh(db_bet)
    return {
        "id": db_bet.id,
        "match_id": db_bet.match_id,
        "teams": db_bet.teams,
        "league": db_bet.league,
        "outcomes": outcomes_list,
        "total_spent": db_bet.total_spent,
        "expected_profit": db_bet.expected_profit,
        "status": db_bet.status,
        "placed_at": db_bet.placed_at
    }

# Listar historial de apuestas
@app.get("/api/bets")
async def get_bets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bet).order_by(Bet.placed_at.desc()))
    bets = result.scalars().all()
    
    decoded_bets = []
    for bet in bets:
        try:
            outcomes_data = json.loads(bet.outcomes)
        except Exception:
            outcomes_data = []
            
        decoded_bets.append({
            "id": bet.id,
            "match_id": bet.match_id,
            "teams": bet.teams,
            "league": bet.league,
            "outcomes": outcomes_data,
            "total_spent": bet.total_spent,
            "expected_profit": bet.expected_profit,
            "actual_return": bet.actual_return,
            "status": bet.status,
            "placed_at": bet.placed_at,
            "settled_at": bet.settled_at,
            "is_prediction": bet.is_prediction
        })
    return decoded_bets

# Obtener estadísticas de rendimiento histórico
@app.get("/api/bets/stats")
async def get_bets_stats(db: AsyncSession = Depends(get_db)):
    # Total invertido histórico (todas las apuestas)
    res_spent = await db.execute(select(func.sum(Bet.total_spent)))
    total_spent = res_spent.scalar() or 0.0
    
    # Obtener todas las apuestas finalizadas
    res_settled = await db.execute(select(Bet).where(Bet.status.in_(["WON", "LOST", "REFUNDED"])))
    settled_bets = res_settled.scalars().all()
    
    net_profit = sum(bet.actual_return - bet.total_spent for bet in settled_bets)
    
    settled_count = len(settled_bets)
    won_count = sum(1 for b in settled_bets if b.status == "WON")
    lost_count = sum(1 for b in settled_bets if b.status == "LOST")
    
    # Apuestas pendientes
    res_pending = await db.execute(select(func.count(Bet.id)).where(Bet.status == "PENDING"))
    pending_count = res_pending.scalar() or 0
    
    win_rate = (won_count / settled_count * 100) if settled_count > 0 else 0.0
    
    total_settled_spent = sum(b.total_spent for b in settled_bets)
    roi = (net_profit / total_settled_spent * 100) if total_settled_spent > 0 else 0.0
    
    return {
        "total_spent": round(total_spent, 2),
        "net_profit": round(net_profit, 2),
        "win_rate": round(win_rate, 2),
        "roi": round(roi, 2),
        "count_won": won_count,
        "count_lost": lost_count,
        "count_pending": pending_count,
        "count_total": settled_count + pending_count
    }

# Registrar liquidación de apuestas (WON, LOST, REFUNDED)
class SettleBetInput(BaseModel):
    status: str
    actual_return: float = None

@app.post("/api/bets/{bet_id}/settle")
async def settle_bet(bet_id: int, input_data: SettleBetInput, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bet).where(Bet.id == bet_id))
    bet = result.scalar_one_or_none()
    if not bet:
        return {"error": "Bet not found"}, 404
        
    bet.status = input_data.status
    if input_data.actual_return is not None:
        bet.actual_return = input_data.actual_return
    else:
        if input_data.status == "WON":
            bet.actual_return = bet.total_spent + bet.expected_profit
        elif input_data.status == "REFUNDED":
            bet.actual_return = bet.total_spent
        else: # LOST
            bet.actual_return = 0.0
            
    bet.settled_at = time.time()
    await db.commit()
    await db.refresh(bet)
    
    return {
        "status": "success",
        "bet": {
            "id": bet.id,
            "status": bet.status,
            "actual_return": bet.actual_return,
            "settled_at": bet.settled_at
        }
    }

# --- ENDPOINTS PARA MERCADOS DE PREDICCIÓN (POLYMARKET) ---

@app.get("/api/prediction-opportunities")
async def get_prediction_opportunities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PredictionMarketOpportunity).order_by(PredictionMarketOpportunity.roi.desc()))
    opportunities = result.scalars().all()
    return [
        {
            "id": opp.id,
            "event_id": opp.event_id,
            "question": opp.question,
            "outcome_a": opp.outcome_a,
            "outcome_b": opp.outcome_b,
            "odds_a": opp.odds_a,
            "odds_b": opp.odds_b,
            "roi": opp.roi,
            "timestamp": opp.timestamp
        }
        for opp in opportunities
    ]

class PredictionBetOutcomeInput(BaseModel):
    outcome: str
    odds: float
    stake: float

class PredictionBetCreateInput(BaseModel):
    event_id: str
    question: str
    outcomes: list[PredictionBetOutcomeInput]
    total_spent: float
    expected_profit: float

@app.post("/api/prediction-bets")
async def create_prediction_bet(bet_data: PredictionBetCreateInput, db: AsyncSession = Depends(get_db)):
    outcomes_list = [
        {"outcome": out.outcome, "bookie": "Polymarket", "odds": out.odds, "stake": out.stake}
        for out in bet_data.outcomes
    ]
    outcomes_json = json.dumps(outcomes_list)
    db_bet = Bet(
        match_id=bet_data.event_id,
        teams=bet_data.question,  # Guardar la pregunta en teams
        league="Polymarket",
        outcomes=outcomes_json,
        total_spent=bet_data.total_spent,
        expected_profit=bet_data.expected_profit,
        status="PENDING",
        is_prediction=1,
        placed_at=time.time()
    )
    db.add(db_bet)
    await db.commit()
    await db.refresh(db_bet)
    return {
        "id": db_bet.id,
        "match_id": db_bet.match_id,
        "teams": db_bet.teams,
        "league": db_bet.league,
        "outcomes": outcomes_list,
        "total_spent": db_bet.total_spent,
        "expected_profit": db_bet.expected_profit,
        "status": db_bet.status,
        "is_prediction": db_bet.is_prediction,
        "placed_at": db_bet.placed_at
    }

