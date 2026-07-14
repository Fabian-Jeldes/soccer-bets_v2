# Workspace Rules & Conventions - Soccer Bets Arbitrage v2

Este archivo sirve como registro (catastro) y conjunto de reglas para agentes de inteligencia artificial y desarrolladores que operen en este repositorio.

---

## 1. Tecnologías Clave y Puertos
*   **Backend**: FastAPI en el puerto `8000` (también sirve WebSockets en `/ws/surebets`).
*   **Frontend**: React (TypeScript + Vite) en el puerto `5173`.
*   **Canal en Tiempo Real**: Redis (o fallback en memoria mediante `app/database/redis_client.py`).
*   **Base de Datos**: SQLite local (`backend/soccer_bets.db`) o PostgreSQL asíncrono configurado mediante `DATABASE_URL` en `.env`.

---

## 2. Convenciones Críticas de Código (Backend)

### Capa Asíncrona (Base de Datos)
*   **REGLA**: Cualquier consulta o escritura a la base de datos dentro del contexto de FastAPI o tareas asíncronas debe realizarse usando sesiones asíncronas de SQLAlchemy (`AsyncSessionLocal` o `get_db`).
*   **REGLA**: Al importar modelos para inicialización en `db.py`, asegúrate de registrarlos en el archivo de inicialización para que la metadata de SQLAlchemy los detecte al invocar `init_db()`.
*   **Fallback**: Si se modifica el esquema de modelos (`models.py`), el archivo SQLite local `soccer_bets.db` debe ser regenerado (borrado para que el script lo vuelva a crear con las nuevas columnas) o migrado mediante comandos SQL ALTER.

### Worker Analyzer (`app/workers/analyzer.py`)
*   **REGLA**: El análisis de cuotas consume del Redis Stream `sport_feeds:odds`.
*   **REGLA**: Para evitar colisiones y limpieza accidental de surebets de diferentes categorías de un mismo partido (ej. borrar una de `FULL_TIME` al procesar una nueva de `OVER_UNDER`), el borrado y ordenamiento en el Sorted Set de Redis (`surebets:active`) debe realizarse combinando `match_id` y `market_type`.
*   **Fuzzy Matching**: Antes de comparar nombres de equipos, se debe pasar la correspondencia difusa utilizando el módulo `app/core/matcher.py`.

---

## 3. Convenciones Críticas de Código (Frontend)

### Diseño y Estilos
*   **Estilo**: Se utiliza **Vanilla CSS** exclusivo en `frontend/src/index.css` para el sistema de diseño (paletas oscuras premium, colores dinámicos HSL, bordes semi-transparentes, desenfoques de fondo y animaciones fluidas).
*   **TypeScript**: Evitar el uso de `any` para datos de la API. Definir y mantener interfaces exactas como `Surebet`, `Outcome`, `Bet`, etc.
*   **Registro**: La calculadora de stakes debe soportar de manera adaptativa cuotas de 2 ó 3 resultados dependiendo del tipo de mercado y realizar el redondeo en base a los criterios financieros establecidos.

---

## 4. Estado de Fases
*   **Fase 1 (Completada)**: Worker asíncrono en segundo plano y normalización de nombres de equipos (Fuzzy matching).
*   **Fase 2 (Completada)**: Base de datos asíncrona local y Ledger persistente de auditoría.
*   **Fase 3 (Completada)**: Mercados 2-Way (Over/Under, DNB) y Arbitraje de predicciones en Polymarket.
*   **Fase 4 (Planificada/En Progreso)**: Arbitraje cruzado, notificaciones Web y panel de métricas avanzado.
