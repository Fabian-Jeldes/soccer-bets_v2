from sqlalchemy import Column, String, Integer, Float, Text
from app.database.db import Base
import time

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(String, primary_key=True, index=True)
    league = Column(String, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    score = Column(String, default="0-0")
    minute = Column(Integer, default=0)
    status = Column(String, default="IN_PLAY")  # IN_PLAY, FINISHED
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)

class SurebetOpportunity(Base):
    __tablename__ = "surebet_opportunities"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    match_id = Column(String, nullable=False, index=True)
    market_type = Column(String, nullable=False, default="FULL_TIME")  # FULL_TIME, OVER_UNDER, DNB, PREDICTION
    roi = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    total_spent = Column(Float, nullable=False)
    outcomes = Column(Text, nullable=False)  # JSON serialized string
    timestamp = Column(Float, default=time.time)

class PredictionMarketOpportunity(Base):
    __tablename__ = "prediction_market_opportunities"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    event_id = Column(String, nullable=False, index=True)
    question = Column(String, nullable=False)
    outcome_a = Column(String, nullable=False)
    outcome_b = Column(String, nullable=False)
    odds_a = Column(Float, nullable=False)
    odds_b = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    timestamp = Column(Float, default=time.time)

class Bet(Base):
    __tablename__ = "bets"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    match_id = Column(String, nullable=False, index=True)
    teams = Column(String, nullable=False)
    league = Column(String, nullable=False)
    outcomes = Column(Text, nullable=False)  # JSON serialized string
    total_spent = Column(Float, nullable=False)
    expected_profit = Column(Float, nullable=False)
    actual_return = Column(Float, default=0.0)
    status = Column(String, default="PENDING")  # PENDING, WON, LOST, REFUNDED
    placed_at = Column(Float, default=time.time)
    settled_at = Column(Float, nullable=True)
    is_prediction = Column(Integer, default=0)  # 0 = false, 1 = true


# Duplicate Bet class removed – original definition retained above
