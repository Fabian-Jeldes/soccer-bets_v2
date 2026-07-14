# Soccer Bets Arbitrage v2

Plataforma de arbitraje deportivo en tiempo real (Surebets) y mercados de predicción. El sistema integra feeds en vivo (simulados en Redis), análisis en segundo plano para cálculo de arbitrajes multidimensionales, persistencia SQLite/PostgreSQL asíncrona, y una interfaz de usuario interactiva y moderna.

---

## Arquitectura del Sistema

El proyecto está dividido en dos partes principales:

### 1. Backend (`/backend`)
*   **FastAPI**: API REST de alto rendimiento y servidor de WebSockets para notificaciones en tiempo real.
*   **Redis Stream**: Tubería unificada de cuotas deportivas (`sport_feeds:odds`) que desacopla la ingesta de datos del análisis.
*   **Worker de Análisis (`analyzer.py`)**: Consumidor asíncrono que procesa cuotas en tiempo real, detecta surebets, calcula los stakes óptimos y publica alertas activas.
*   **Base de Datos (SQLAlchemy + aiosqlite/asyncpg)**: Capa de datos relacional asíncrona con fallback automático a SQLite local (`soccer_bets.db`).
*   **Scraper de Polymarket (`polymarket.py`)**: Demonio asíncrono que sondea contratos Yes/No en tiempo real y calcula arbitrajes de predicciones.

### 2. Frontend (`/frontend`)
*   **React + TypeScript + Vite**: Single Page Application veloz y tipada.
*   **Diseño Premium**: Interfaz responsive construida con vanilla CSS, paleta de colores oscuros inspirada en Figma, micro-animaciones y badges visuales.
*   **WebSocket Client**: Conexión bidireccional directa con el backend para recibir alertas instantáneas.
*   **Calculadora Integrada**: Conversión de cuotas, cálculo de stakes ponderados por ROI y registro directo de transacciones.
*   **Ledger e Historial**: Registro detallado de apuestas en vivo y predicciones, con panel de control para liquidar apuestas (`WON`/`LOST`/`REFUNDED`) y recálculo automático de rendimiento (Win Rate, Net Profit, ROI).

---

## Estructura del Repositorio

```
soccer-bets_v2/
├── backend/
│   ├── app/
│   │   ├── core/           # Lógica matemática, cálculos y matcher
│   │   ├── database/       # Conectividad SQLite/Postgres y modelos SQLAlchemy
│   │   ├── scraper/        # Simulador de partidos y scraper de Polymarket
│   │   ├── workers/        # Worker analyzer de surebets
│   │   └── main.py         # Punto de entrada FastAPI y endpoints REST/WS
│   ├── requirements.txt    # Dependencias de Python
│   └── soccer_bets.db      # Base de datos SQLite local (creada automáticamente)
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Componente principal, dashboard y calculadora
│   │   ├── main.tsx        # Entrada de React
│   │   └── index.css       # Estilos globales y diseño premium
│   ├── package.json        # Dependencias de React/Vite
│   └── vite.config.ts      # Configuración de empaquetado Vite
└── README.md               # Documentación general del repositorio
```

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
