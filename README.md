# Soccer Bets Arbitrage v2

Plataforma de arbitraje deportivo en tiempo real (Surebets) y mercados de predicción. El sistema integra feeds en vivo (simulados en Redis), análisis en segundo plano para cálculo de arbitrajes multidimensionales, persistencia SQLite/PostgreSQL asíncrona, y una interfaz de usuario interactiva y moderna con sugerencias basadas en historial H2H.

---

## Arquitectura del Sistema

El proyecto está dividido en dos partes principales:

### 1. Backend (`/backend`)
*   **FastAPI**: API REST de alto rendimiento y servidor de WebSockets para notificaciones en tiempo real.
*   **Redis Stream**: Tubería unificada de cuotas deportivas (`sport_feeds:odds`) que desacopla la ingesta de datos del análisis. Incluye un simulador de Redis en memoria si no se detecta un servidor externo.
*   **Worker de Análisis (`analyzer.py`)**: Consumidor asíncrono que procesa cuotas en tiempo real, detecta surebets, calcula los stakes óptimos, persiste oportunidades en base de datos y publica alertas activas.
*   **Base de Datos (SQLAlchemy + aiosqlite/asyncpg)**: Capa de datos relacional asíncrona con fallback automático a SQLite local (`soccer_bets.db`).
*   **Scraper de Polymarket (`polymarket.py`)**: Demonio asíncrono que sondea contratos Yes/No en tiempo real y calcula arbitrajes de predicciones.
*   **Simulador de Cuotas (`simulator.py`)**: Motor de simulación respaldado por base de datos que gestiona el ciclo de vida de los partidos (`SCHEDULED` → `IN_PLAY` → `FINISHED`), genera cuotas dinámicas y publica al Redis Stream.
*   **Seeder de Datos (`seed.py`)**: Población automática de la base de datos con partidos H2H históricos y partidos programados al primer arranque.
*   **Motor de Sugerencias (`/api/suggestions`)**: Endpoint que analiza el historial Head-to-Head (H2H) de equipos y genera predicciones con niveles de confianza para partidos programados.

### 2. Frontend (`/frontend`)
*   **React + TypeScript + Vite**: Single Page Application veloz y tipada.
*   **Diseño Premium**: Interfaz responsive construida con vanilla CSS, paleta de colores oscuros inspirada en Figma, micro-animaciones y badges visuales.
*   **WebSocket Client**: Conexión bidireccional directa con el backend para recibir alertas instantáneas.
*   **Calculadora Integrada**: Conversión de cuotas, cálculo de stakes ponderados por ROI y registro directo de transacciones. La calculadora retiene la surebet seleccionada aunque expire del feed activo, mostrando un badge de advertencia.
*   **Ledger e Historial**: Registro detallado de apuestas en vivo y predicciones, con panel de control para liquidar apuestas (`WON`/`LOST`/`REFUNDED`) y recálculo automático de rendimiento (Win Rate, Net Profit, ROI).
*   **Congelar Feed (Freeze)**: Botón para pausar las actualizaciones en tiempo real del WebSocket, permitiendo analizar y actuar sobre surebets sin que la lista se reordene o vacíe.
*   **Panel de Sugerencias H2H**: Tab dedicado que muestra predicciones de resultados basadas en estadísticas de encuentros previos (victorias, empates, promedio de goles, porcentaje Over 2.5).
*   **Historial Persistido de Surebets**: Sección debajo de las surebets activas que muestra las últimas oportunidades detectadas almacenadas en base de datos, seleccionables para carga en la calculadora.

---

## Estructura del Repositorio

```
soccer-bets_v2/
├── .agents/
│   └── AGENTS.md            # Reglas y convenciones para agentes IA y desarrolladores
├── backend/
│   ├── app/
│   │   ├── core/            # Lógica matemática, cálculos y matcher difuso
│   │   ├── database/
│   │   │   ├── db.py        # Conexión async SQLAlchemy (SQLite/PostgreSQL)
│   │   │   ├── models.py    # Modelos ORM: Match, SurebetOpportunity, Bet, etc.
│   │   │   ├── redis_client.py  # Cliente Redis con fallback en memoria
│   │   │   └── seed.py      # Seeder automático de datos H2H y partidos programados
│   │   ├── scraper/
│   │   │   ├── simulator.py # Simulador de cuotas respaldado por BD
│   │   │   └── polymarket.py # Scraper de mercados de predicción
│   │   ├── workers/
│   │   │   └── analyzer.py  # Worker de detección de surebets y arbitraje cruzado
│   │   ├── config.py        # Configuración de la aplicación (Telegram, API keys)
│   │   └── main.py          # Punto de entrada FastAPI, endpoints REST/WS y lifespan
│   ├── requirements.txt     # Dependencias de Python
│   └── soccer_bets.db       # Base de datos SQLite local (creada automáticamente)
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Componente principal: dashboard, calculadora, sugerencias
│   │   ├── main.tsx         # Entrada de React
│   │   └── index.css        # Estilos globales y diseño premium (Vanilla CSS)
│   ├── package.json         # Dependencias de React/Vite
│   └── vite.config.ts       # Configuración de empaquetado Vite
├── docker-compose.yml       # Composición Docker (Redis)
└── README.md                # Documentación general del repositorio
```

---

## Funcionalidades Principales

### Detección de Surebets en Tiempo Real
El sistema analiza continuamente las cuotas de múltiples casas de apuestas simuladas y detecta oportunidades de arbitraje en los siguientes mercados:
*   **Full Time (1X2)**: Resultado final con 3 outcomes.
*   **Over/Under 2.5 Goles**: Mercado de 2 outcomes.
*   **Draw No Bet (DNB)**: Mercado de 2 outcomes sin empate.

### Arbitraje Cruzado (Deportivo + Predicción)
Combina cuotas deportivas tradicionales con contratos Yes/No de mercados de predicción (Polymarket) para encontrar oportunidades de arbitraje interdimensional.

### Sugerencias y Predicciones H2H
Para cada partido programado, el sistema consulta el historial completo de enfrentamientos previos entre ambos equipos y calcula:
*   **Distribución de resultados**: Victorias locales, empates y victorias visitantes con barra visual.
*   **Promedio de goles por partido** y **porcentaje de partidos Over 2.5**.
*   **Sugerencia de resultado** con porcentaje de confianza (ej. "Doble Op.: Al Ahly o Empate — 75%").
*   **Sugerencia de goles** con porcentaje de confianza (ej. "Over 2.5 Goles — 66.7%").

### Estabilización del Feed
*   **Freeze Feed**: Pausa las actualizaciones en la interfaz para que las tarjetas de surebets no desaparezcan mientras el usuario analiza una oportunidad.
*   **Calculadora persistente**: Si una surebet expira mientras está cargada en la calculadora, no se reinicia. Se mantiene con un badge de advertencia visual.
*   **Historial persistido**: Las surebets se almacenan en base de datos y pueden consultarse y cargarse en la calculadora incluso después de haber expirado del feed activo.

### Gestión Dinámica de Partidos
*   El simulador ya no repite partidos antiguos en bucle infinito. Los partidos siguen un ciclo de vida controlado por la base de datos: **Programado → En Juego → Finalizado**.
*   Nuevos partidos se programan automáticamente al finalizar los anteriores.
*   El seeder de datos popula la base de datos con historial H2H realista al primer arranque.

---

## Instalación y Configuración

### Requisitos
*   Python 3.10+
*   Node.js 18+
*   Redis Server (opcional, el sistema incluye un simulador de Redis en memoria si no detecta uno ejecutándose localmente).

### Levantar el Backend
1. Entra a la carpeta de backend:
   ```bash
   cd backend
   ```
2. Crea e inicia un entorno virtual:
   ```bash
   python -m venv .venv
   # En Windows:
   .\.venv\Scripts\activate
   # En macOS/Linux:
   source .venv/bin/activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Levanta el servidor de desarrollo:
   ```bash
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   > **Nota**: Al iniciar por primera vez, el backend creará automáticamente la base de datos SQLite y la poblará con datos H2H de prueba.

### Levantar el Frontend
1. Entra a la carpeta de frontend:
   ```bash
   cd ../frontend
   ```
2. Instala las dependencias:
   ```bash
   npm install
   ```
3. Levanta el servidor Vite:
   ```bash
   npm run dev
   ```
4. Abre [http://localhost:5173](http://localhost:5173) en tu navegador.

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/surebets` | Surebets activas del Sorted Set de Redis |
| `GET` | `/api/surebets/history` | Últimas 30 surebets persistidas en BD |
| `GET` | `/api/suggestions` | Predicciones H2H para partidos programados |
| `GET` | `/api/cross-opportunities` | Oportunidades de arbitraje cruzado |
| `GET` | `/api/prediction-opportunities` | Oportunidades de arbitraje en Polymarket |
| `GET` | `/api/stats` | Métricas generales del sistema |
| `GET` | `/api/bets` | Historial de apuestas registradas |
| `POST` | `/api/bets` | Registrar una nueva apuesta en el ledger |
| `PUT` | `/api/bets/{id}/settle` | Liquidar una apuesta (WON/LOST/REFUNDED) |
| `WS` | `/ws/surebets` | WebSocket de actualizaciones en tiempo real |

---

## Estado de Desarrollo (Fases)

| Fase | Estado | Descripción |
|------|--------|-------------|
| **1** | ✅ Completada | Worker asíncrono en segundo plano y normalización de nombres (Fuzzy Matching) |
| **2** | ✅ Completada | Base de datos asíncrona local y Ledger persistente de auditoría |
| **3** | ✅ Completada | Mercados 2-Way (Over/Under, DNB) y arbitraje en Polymarket |
| **4** | ✅ Completada | Arbitraje cruzado, notificaciones Web y panel de métricas |
| **5** | ✅ Completada | Simulador basado en BD, sugerencias H2H, historial persistido y estabilización del feed |
