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
from app.database.models import Match, SurebetOpportunity, Bet, PredictionMarketOpportunity, CrossMarketOpportunity
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
    
    # Sembrar Base de Datos si está vacía
    from app.database.seed import seed_db_if_empty
    await seed_db_if_empty()
    
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

# Endpoint para obtener sugerencias/predicciones basadas en el historial H2H
@app.get("/api/suggestions")
async def get_suggestions(db: AsyncSession = Depends(get_db)):
    result_scheduled = await db.execute(
        select(Match).where(Match.status == "SCHEDULED").order_by(Match.start_time.asc())
    )
    scheduled_matches = result_scheduled.scalars().all()
    
    suggestions = []
    for match in scheduled_matches:
        home = match.home_team
        away = match.away_team
        
        # Buscar partidos históricos finalizados para estos dos equipos (H2H)
        stmt_h2h = select(Match).where(
            (Match.status == "FINISHED") & 
            (
                ((Match.home_team == home) & (Match.away_team == away)) |
                ((Match.home_team == away) & (Match.away_team == home))
            )
        )
        res_h2h = await db.execute(stmt_h2h)
        h2h_matches = res_h2h.scalars().all()
        
        n_matches = len(h2h_matches)
        h_wins = 0
        a_wins = 0
        draws = 0
        total_goals = 0
        over_2_5 = 0
        
        for hm in h2h_matches:
            try:
                sh, sa = map(int, hm.score.split("-"))
            except Exception:
                sh, sa = 0, 0
                
            total_goals += (sh + sa)
            if (sh + sa) > 2.5:
                over_2_5 += 1
                
            if hm.home_team == home:
                if sh > sa:
                    h_wins += 1
                elif sa > sh:
                    a_wins += 1
                else:
                    draws += 1
            else:  # hm.home_team == away (invertido)
                if sa > sh:
                    h_wins += 1
                elif sh > sa:
                    a_wins += 1
                else:
                    draws += 1
                    
        if n_matches > 0:
            pct_home = (h_wins / n_matches) * 100
            pct_away = (a_wins / n_matches) * 100
            pct_draw = (draws / n_matches) * 100
            pct_over = (over_2_5 / n_matches) * 100
            avg_goals = round(total_goals / n_matches, 2)
            
            # Sugerencia Ganador
            if h_wins > a_wins and pct_home >= 45:
                sug_winner = f"Ganador: {home}"
                win_confidence = round(pct_home, 1)
            elif a_wins > h_wins and pct_away >= 45:
                sug_winner = f"Ganador: {away}"
                win_confidence = round(pct_away, 1)
            elif pct_draw >= 35:
                sug_winner = "Empate"
                win_confidence = round(pct_draw, 1)
            else:
                sug_winner = f"Doble Op.: {home} o Empate"
                win_confidence = round(pct_home + pct_draw, 1)
                
            # Sugerencia Goles
            if pct_over >= 50:
                sug_goals = "Over 2.5 Goles"
                goals_confidence = round(pct_over, 1)
            else:
                sug_goals = "Under 2.5 Goles"
                goals_confidence = round(100 - pct_over, 1)
        else:
            pct_home = pct_away = pct_draw = pct_over = 0
            avg_goals = 0.0
            sug_winner = "Doble Op.: Local/Visitante"
            win_confidence = 50.0
            sug_goals = "Under 2.5 Goles"
            goals_confidence = 50.0
            
        suggestions.append({
            "match_id": match.id,
            "league": match.league,
            "home_team": home,
            "away_team": away,
            "start_time": match.start_time,
            "h2h_stats": {
                "total_matches": n_matches,
                "home_wins": h_wins,
                "away_wins": a_wins,
                "draws": draws,
                "avg_goals": avg_goals,
                "over_2_5_pct": round(pct_over, 1)
            },
            "suggestions": {
                "winner": sug_winner,
                "winner_confidence": win_confidence,
                "goals": sug_goals,
                "goals_confidence": goals_confidence
            }
        })
        
    return suggestions

# Endpoint para listar historial reciente de oportunidades de surebet
@app.get("/api/surebets/history")
async def get_surebets_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SurebetOpportunity).order_by(SurebetOpportunity.timestamp.desc()).limit(30))
    opps = result.scalars().all()
    
    return [
        {
            "id": opp.id,
            "match_id": opp.match_id,
            "market_type": opp.market_type,
            "roi": opp.roi,
            "profit": opp.profit,
            "total_spent": opp.total_spent,
            "outcomes": json.loads(opp.outcomes) if opp.outcomes else [],
            "timestamp": opp.timestamp
        }
        for opp in opps
    ]

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

@app.get("/api/cross-opportunities")
async def get_cross_opportunities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrossMarketOpportunity).order_by(CrossMarketOpportunity.roi.desc()))
    opportunities = result.scalars().all()
    return [
        {
            "id": opp.id,
            "sport_match_id": opp.sport_match_id,
            "prediction_market_id": opp.prediction_market_id,
            "teams": opp.teams,
            "sport_bookmaker": opp.sport_bookmaker,
            "prediction_question": opp.prediction_question,
            "combination_type": opp.combination_type,
            "roi": opp.roi,
            "outcomes": json.loads(opp.outcomes) if opp.outcomes else [],
            "timestamp": opp.timestamp
        }
        for opp in opportunities
    ]

class CrossBetOutcomeInput(BaseModel):
    outcome: str
    bookie: str
    odds: float
    stake: float

class CrossBetCreateInput(BaseModel):
    sport_match_id: str
    prediction_market_id: str
    teams: str
    outcomes: list[CrossBetOutcomeInput]
    total_spent: float
    expected_profit: float

@app.post("/api/cross-bets")
async def create_cross_bet(bet_data: CrossBetCreateInput, db: AsyncSession = Depends(get_db)):
    outcomes_list = [out.model_dump() for out in bet_data.outcomes]
    outcomes_json = json.dumps(outcomes_list)
    db_bet = Bet(
        match_id=f"{bet_data.sport_match_id}_{bet_data.prediction_market_id}",
        teams=bet_data.teams,
        league="Cross-Market",
        outcomes=outcomes_json,
        total_spent=bet_data.total_spent,
        expected_profit=bet_data.expected_profit,
        status="PENDING",
        is_prediction=2,  # 2 = Cross-Market Bet
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


