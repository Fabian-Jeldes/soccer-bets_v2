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

### Seeder de Datos (`app/database/seed.py`)
*   **REGLA**: Al iniciar el backend por primera vez (base de datos vacía), el seeder se ejecuta automáticamente en el `lifespan` de FastAPI.
*   **REGLA**: El seeder inserta partidos históricos finalizados (`FINISHED`) con datos H2H realistas y partidos programados (`SCHEDULED`) con `start_time` en el futuro. Si la tabla `matches` ya tiene registros, se omite la siembra.
*   **REGLA**: Cada partido debe incluir la columna `start_time` (Float, epoch timestamp) para que el simulador gestione las transiciones de estado correctamente.

### Simulador de Cuotas (`app/scraper/simulator.py`)
*   **REGLA**: El simulador opera contra la base de datos (no usa listas estáticas en memoria). Lee partidos `IN_PLAY`, incrementa sus minutos, y publica cuotas al Redis Stream `sport_feeds:odds`.
*   **REGLA**: Las transiciones de estado siguen el flujo: `SCHEDULED` → `IN_PLAY` (cuando `time.time() >= start_time`) → `FINISHED` (cuando `minute >= 90`). Al finalizar un partido, se agenda automáticamente un nuevo partido `SCHEDULED` para el mismo matchup.
*   **REGLA**: Si hay menos de 3 partidos `IN_PLAY`, el simulador promueve partidos `SCHEDULED` cuyo `start_time` ya se haya alcanzado.

### Worker Analyzer (`app/workers/analyzer.py`)
*   **REGLA**: El análisis de cuotas consume del Redis Stream `sport_feeds:odds`.
*   **REGLA**: Para evitar colisiones y limpieza accidental de surebets de diferentes categorías de un mismo partido (ej. borrar una de `FULL_TIME` al procesar una nueva de `OVER_UNDER`), el borrado y ordenamiento en el Sorted Set de Redis (`surebets:active`) debe realizarse combinando `match_id` y `market_type`.
*   **REGLA**: Toda surebet detectada con ROI > 0 debe ser persistida en la tabla `SurebetOpportunity` de la base de datos para historial y auditoría.
*   **Fuzzy Matching**: Antes de comparar nombres de equipos, se debe pasar la correspondencia difusa utilizando el módulo `app/core/matcher.py`.
*   **Encoding Windows**: La impresión de mensajes con emojis a la consola de Windows debe manejarse con `try/except UnicodeEncodeError` y fallback a `.encode(encoding, errors='replace')` para evitar que el worker se detenga.

### Endpoints de API
*   **`GET /api/suggestions`**: Devuelve predicciones H2H para partidos `SCHEDULED`, calculando récord de victorias, empates, promedio de goles y porcentaje Over 2.5 a partir de los partidos `FINISHED` del mismo matchup.
*   **`GET /api/surebets/history`**: Devuelve las últimas 30 surebets persistidas en la tabla `SurebetOpportunity`, ordenadas por timestamp descendente.
*   **`GET /api/surebets`**: Devuelve surebets activas del Sorted Set de Redis.
*   **`GET /api/cross-opportunities`**: Devuelve oportunidades de arbitraje cruzado (deportivo + predicción).

---

## 3. Convenciones Críticas de Código (Frontend)

### Diseño y Estilos
*   **Estilo**: Se utiliza **Vanilla CSS** exclusivo en `frontend/src/index.css` para el sistema de diseño (paletas oscuras premium, colores dinámicos HSL, bordes semi-transparentes, desenfoques de fondo y animaciones fluidas).
*   **TypeScript**: Evitar el uso de `any` para datos de la API. Definir y mantener interfaces exactas como `Surebet`, `Outcome`, `Bet`, etc.
*   **Registro**: La calculadora de stakes debe soportar de manera adaptativa cuotas de 2 ó 3 resultados dependiendo del tipo de mercado y realizar el redondeo en base a los criterios financieros establecidos.

### Freeze Feed (Congelar Actualizaciones)
*   **REGLA**: El estado `freezeFeed` se sincroniza con una ref (`freezeFeedRef`) para que los callbacks del WebSocket, el `requestAnimationFrame` loop, el fetch polling y la limpieza automática de surebets expiradas respeten el congelamiento sin desfases.
*   **REGLA**: Cuando el feed está congelado, los mensajes del WebSocket se descartan (no se acumulan) y las llamadas de fetch no actualizan el estado.

### Calculadora y Persistencia de Selección
*   **REGLA**: Cuando una surebet seleccionada en la calculadora expira del feed activo, **no se debe deseleccionar** (`setSelectedSurebet(null)` prohibido). En su lugar, se mantienen los datos y se muestra un badge de advertencia `"⚠️ Inactivo (Histórico)"`.
*   **REGLA**: Las surebets del historial persistido (`/api/surebets/history`) se pueden cargar en la calculadora haciendo clic sobre ellas. Se distinguen visualmente con bordes punteados y opacidad reducida.

### Panel de Sugerencias (H2H)
*   **REGLA**: El tab `'suggestions'` ocupa el ancho completo del grid (`gridTemplateColumns: '1fr'`) al igual que el tab `'ledger'`.
*   **REGLA**: Las sugerencias se refrescan cada 8 segundos cuando el tab está activo, y se pueden refrescar manualmente con el botón "Refrescar".

---

## 4. Estado de Fases
*   **Fase 1 (Completada)**: Worker asíncrono en segundo plano y normalización de nombres de equipos (Fuzzy matching).
*   **Fase 2 (Completada)**: Base de datos asíncrona local y Ledger persistente de auditoría.
*   **Fase 3 (Completada)**: Mercados 2-Way (Over/Under, DNB) y Arbitraje de predicciones en Polymarket.
*   **Fase 4 (Completada)**: Arbitraje cruzado, notificaciones Web y panel de métricas avanzado.
*   **Fase 5 (Completada)**: Simulador basado en BD, sugerencias H2H, historial persistido de surebets, y estabilización del feed (Freeze Feed + calculadora no-destructiva).
