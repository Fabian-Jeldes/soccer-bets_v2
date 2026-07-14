import time
import random
from sqlalchemy import select
from app.database.db import AsyncSessionLocal
from app.database.models import Match

# Ligas y equipos canonicales
MATCHUPS = [
    {
        "league": "Algerian Ligue 1",
        "home": "MC Alger",
        "away": "CR Belouizdad",
    },
    {
        "league": "Kenyan Premier League",
        "home": "Gor Mahia",
        "away": "Tusker FC",
    },
    {
        "league": "Egyptian Premier League",
        "home": "Al Ahly",
        "away": "Zamalek SC",
    },
    {
        "league": "Saudi Pro League",
        "home": "Al Hilal",
        "away": "Al Nassr",
    },
    {
        "league": "South African Premiership",
        "home": "Mamelodi Sundowns",
        "away": "Orlando Pirates",
    }
]

async def seed_db_if_empty():
    async with AsyncSessionLocal() as session:
        # Verificar si ya existen partidos en la tabla
        stmt = select(Match).limit(1)
        res = await session.execute(stmt)
        if res.scalar_one_or_none() is not None:
            print("Base de datos ya cuenta con partidos. Omitiendo siembra.")
            return
            
        print("Sembrando base de datos con partidos históricos (H2H) y programados...")
        now = time.time()
        
        # 1. Sembrar partidos históricos finalizados (12 por cada enfrentamiento)
        for idx, m in enumerate(MATCHUPS):
            for i in range(12):
                # Generar marcadores aleatorios pero razonables
                score_home = random.choice([0, 1, 2, 3])
                score_away = random.choice([0, 1, 2, 3])
                
                # Distribuir fechas en los últimos 7 días
                time_offset = random.uniform(2 * 3600, 7 * 24 * 3600)  # entre 2 horas y 7 días atrás
                match_time = now - time_offset
                
                db_match = Match(
                    id=f"hist_{m['home'].replace(' ', '_').lower()}_{m['away'].replace(' ', '_').lower()}_{i}",
                    league=m["league"],
                    home_team=m["home"],
                    away_team=m["away"],
                    score=f"{score_home}-{score_away}",
                    minute=90,
                    status="FINISHED",
                    start_time=match_time,
                    created_at=match_time,
                    updated_at=match_time + 5400  # 90 minutos después
                )
                session.add(db_match)
                
            # 2. Sembrar 1 partido programado para el futuro cercano
            # Tiempos de inicio escalonados: entre 3 y 45 minutos en el futuro
            start_offset = random.uniform(180, 2700)
            db_match = Match(
                id=f"upcoming_{m['home'].replace(' ', '_').lower()}_{m['away'].replace(' ', '_').lower()}",
                league=m["league"],
                home_team=m["home"],
                away_team=m["away"],
                score="0-0",
                minute=0,
                status="SCHEDULED",
                start_time=now + start_offset,
                created_at=now,
                updated_at=now
            )
            session.add(db_match)
            
        await session.commit()
        print("Siembra de base de datos finalizada exitosamente.")
