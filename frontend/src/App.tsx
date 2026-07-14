import { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  TrendingUp, 
  Coins, 
  ShieldCheck, 
  AlertCircle, 
  Percent, 
  Clock, 
  Calculator,
  BookOpen,
  History,
  CheckCircle2,
  XCircle
} from 'lucide-react';


interface Outcome {
  outcome: string;
  bookie: string;
  odds: number;
  stake: number;
}

interface Surebet {
  match_id: string;
  league: string;
  teams: string;
  score: string;
  minute: number;
  outcomes: Outcome[];
  total_spent: number;
  profit: number;
  roi: number;
  timestamp: number;
  market_type?: string;
}

export default function App() {
  const [connected, setConnected] = useState<boolean>(false);
  const [surebets, setSurebets] = useState<Surebet[]>([]);
  const [selectedSurebet, setSelectedSurebet] = useState<Surebet | null>(null);
  const [budget, setBudget] = useState<number>(1000);
  
  // Filtros
  const [minRoi, setMinRoi] = useState<number>(0);
  const [selectedLeague, setSelectedLeague] = useState<string>('All');

  // Estados de la Fase 2 (Ledger de Apuestas y Persistencia) e Integración de Fase 3 y 4
  const [activeTab, setActiveTab] = useState<'live' | 'two-way' | 'prediction' | 'cross' | 'ledger'>('live');
  const [bets, setBets] = useState<any[]>([]);
  const [placingBet, setPlacingBet] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [stats, setStats] = useState<any>({
    total_spent: 0,
    net_profit: 0,
    win_rate: 0,
    roi: 0,
    count_won: 0,
    count_lost: 0,
    count_pending: 0,
    count_total: 0
  });

  // Estados de la Fase 3 (Mercados de Predicción)
  const [predictionOpps, setPredictionOpps] = useState<any[]>([]);
  const [selectedPrediction, setSelectedPrediction] = useState<any | null>(null);

  // Estados de la Fase 4 (Arbitraje Cruzado y Notificaciones)
  const [crossOpportunities, setCrossOpportunities] = useState<any[]>([]);
  const [selectedCrossOpp, setSelectedCrossOpp] = useState<any | null>(null);
  const notifiedRefs = useRef<Record<string, number>>({});

  // Sintetizar tono de notificación interactivo (Web Audio API)
  const playBeep = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.setValueAtTime(880, ctx.currentTime + 0.1); // A5
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.005, ctx.currentTime + 0.35);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.35);
    } catch (e) {
      console.warn('AudioContext alert failed to play', e);
    }
  };

  // Disparar notificación nativa del navegador
  const triggerBrowserNotification = (sb: any) => {
    if (Notification.permission === 'granted') {
      try {
        const title = `⚽ ¡Arbitraje Detectado! (+${sb.roi}%)`;
        const body = `${sb.teams} | Mercado: ${sb.market_type || 'CROSS_MARKET'}`;
        new Notification(title, { body, silent: true });
      } catch (e) {
        console.warn('Desktop notification failed', e);
      }
    }
  };

  const fetchBetsAndStats = async () => {
    try {
      const betsRes = await fetch('http://localhost:8000/api/bets');
      if (betsRes.ok) {
        const betsData = await betsRes.json();
        setBets(betsData);
      }
      
      const statsRes = await fetch('http://localhost:8000/api/bets/stats');
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (err) {
      console.error('Error al obtener apuestas/estadísticas:', err);
    }
  };

  const fetchPredictionOpps = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/prediction-opportunities');
      if (res.ok) {
        const data = await res.json();
        setPredictionOpps(data);
      }
    } catch (err) {
      console.error('Error al obtener oportunidades de predicción:', err);
    }
  };

  const fetchCrossOpps = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/cross-opportunities');
      if (res.ok) {
        const data = await res.json();
        setCrossOpportunities(data);
      }
    } catch (err) {
      console.error('Error al obtener oportunidades cruzadas:', err);
    }
  };

  // Solicitar permisos de notificación en el arranque de la app
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    fetchBetsAndStats();
    
    if (activeTab === 'prediction') {
      fetchPredictionOpps();
      const interval = setInterval(fetchPredictionOpps, 3000);
      return () => clearInterval(interval);
    } else if (activeTab === 'cross') {
      fetchCrossOpps();
      const interval = setInterval(fetchCrossOpps, 3000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  const handleRegisterBet = async () => {
    if (!selectedSurebet || !calc) return;
    setPlacingBet(true);
    try {
      const outcomes = selectedSurebet.outcomes.map((out, idx) => ({
        outcome: out.outcome,
        bookie: out.bookie,
        odds: out.odds,
        stake: calc.stakes[idx]
      }));

      const res = await fetch('http://localhost:8000/api/bets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          match_id: selectedSurebet.match_id,
          teams: selectedSurebet.teams,
          league: selectedSurebet.league,
          outcomes,
          total_spent: calc.totalSpent,
          expected_profit: calc.profit
        })
      });

      if (res.ok) {
        setNotification({ message: '¡Apuesta registrada exitosamente!', type: 'success' });
        fetchBetsAndStats();
        setTimeout(() => setNotification(null), 4000);
      } else {
        setNotification({ message: 'Error al registrar la apuesta.', type: 'error' });
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (err) {
      setNotification({ message: 'Error de red al conectar con el servidor.', type: 'error' });
      setTimeout(() => setNotification(null), 4000);
    } finally {
      setPlacingBet(false);
    }
  };

  const handleSettleBet = async (betId: number, status: 'WON' | 'LOST' | 'REFUNDED') => {
    try {
      const res = await fetch(`http://localhost:8000/api/bets/${betId}/settle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      if (res.ok) {
        setNotification({ message: `Apuesta #${betId} marcada como ${status}`, type: 'success' });
        fetchBetsAndStats();
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (err) {
      console.error('Error al liquidar apuesta:', err);
    }
  };

  const handleRegisterPredictionBet = async () => {
    if (!selectedPrediction || !predCalc) return;
    setPlacingBet(true);
    try {
      const outcomes = [
        {
          outcome: selectedPrediction.outcome_a,
          odds: selectedPrediction.odds_a,
          stake: predCalc.stakes[0]
        },
        {
          outcome: selectedPrediction.outcome_b,
          odds: selectedPrediction.odds_b,
          stake: predCalc.stakes[1]
        }
      ];

      const res = await fetch('http://localhost:8000/api/prediction-bets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: selectedPrediction.event_id,
          question: selectedPrediction.question,
          outcomes,
          total_spent: predCalc.totalSpent,
          expected_profit: predCalc.profit
        })
      });

      if (res.ok) {
        setNotification({ message: '¡Apuesta de predicción registrada exitosamente!', type: 'success' });
        fetchBetsAndStats();
        setSelectedPrediction(null);
        setTimeout(() => setNotification(null), 4000);
      } else {
        setNotification({ message: 'Error al registrar la apuesta de predicción.', type: 'error' });
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (err) {
      setNotification({ message: 'Error de red al registrar la apuesta.', type: 'error' });
      setTimeout(() => setNotification(null), 4000);
    } finally {
      setPlacingBet(false);
    }
  };


  // Buffer para throttling/batching de actualizaciones en vivo
  const updateBuffer = useRef<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Conexión WebSocket con reconexión automática
  useEffect(() => {
    let reconnectTimeout: number;

    const connectWS = () => {
      const ws = new WebSocket('ws://localhost:8000/ws/surebets');
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('WebSocket conectado al backend.');
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'initial_state') {
          setSurebets(msg.data);
        } else if (msg.type === 'update') {
          const sb = msg.data;
          // Throttling de notificaciones de alto ROI (>= 3.0%)
          if (sb && sb.roi >= 3.0) {
            const key = `${sb.match_id || sb.sport_match_id}_${sb.market_type || 'CROSS_MARKET'}`;
            const now = Date.now();
            const lastTime = notifiedRefs.current[key] || 0;
            if (now - lastTime > 15000) {
              notifiedRefs.current[key] = now;
              playBeep();
              triggerBrowserNotification(sb);
            }
          }
          // Agregar al buffer para aplicar batching
          updateBuffer.current.push(sb);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('WebSocket desconectado. Intentando reconectar...');
        reconnectTimeout = window.setTimeout(connectWS, 3000);
      };

      ws.onerror = (error) => {
        console.error('Error en WebSocket:', error);
        ws.close();
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
      clearTimeout(reconnectTimeout);
    };
  }, []);

  // API Fetch periódica para limpiar surebets obsoletas y sincronizar estado
  useEffect(() => {
    const fetchActiveSurebets = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/surebets');
        if (res.ok) {
          const data = await res.json();
          setSurebets(data);
        }
      } catch (err) {
        console.error('Error al sincronizar surebets desde la API:', err);
      }
    };

    // Sincronización inicial rápida
    fetchActiveSurebets();

    const interval = setInterval(fetchActiveSurebets, 6000);
    return () => clearInterval(interval);
  }, []);

  // Loop de requestAnimationFrame para batching/throttling de actualizaciones (60 FPS)
  useEffect(() => {
    let animationFrameId: number;

    const processUpdates = () => {
      if (updateBuffer.current.length > 0) {
        const batch = [...updateBuffer.current];
        updateBuffer.current = [];

        // Throttling para surebets de deportes
        setSurebets((prev) => {
          const next = [...prev];
          const sportBatch = batch.filter(sb => sb.market_type !== 'CROSS_MARKET');
          for (const newSb of sportBatch) {
            const idx = next.findIndex((item) => item.match_id === newSb.match_id && item.market_type === newSb.market_type);
            if (idx > -1) {
              next[idx] = newSb;
            } else {
              next.push(newSb);
            }
          }
          return next.sort((a, b) => b.roi - a.roi);
        });

        // Throttling para oportunidades cruzadas (Cross-Market)
        const crossBatch = batch.filter(sb => sb.market_type === 'CROSS_MARKET');
        if (crossBatch.length > 0) {
          setCrossOpportunities((prevCross) => {
            const nextCross = [...prevCross];
            for (const newCross of crossBatch) {
              const idx = nextCross.findIndex((item) => item.sport_match_id === newCross.sport_match_id && item.prediction_market_id === newCross.prediction_market_id);
              if (idx > -1) {
                nextCross[idx] = newCross;
              } else {
                nextCross.push(newCross);
              }
            }
            return nextCross.sort((a, b) => b.roi - a.roi);
          });
        }
      }

      animationFrameId = requestAnimationFrame(processUpdates);
    };

    animationFrameId = requestAnimationFrame(processUpdates);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  // Limpieza automática local de surebets inactivas (más de 8 segundos sin actualizar)
  useEffect(() => {
    const cleanExpired = () => {
      const now = Date.now() / 1000;
      setSurebets((prev) => prev.filter((sb) => now - sb.timestamp < 8.0));
      setCrossOpportunities((prev) => prev.filter((co) => now - co.timestamp < 8.0));
    };

    const interval = setInterval(cleanExpired, 2000);
    return () => clearInterval(interval);
  }, []);

  // Obtener ligas únicas para el filtro
  const leagues = ['All', ...Array.from(new Set(surebets.map((sb) => sb.league)))];

  // Filtrar la lista de surebets
  // Filtrar la lista de surebets según el tab activo y los filtros aplicados
  const filteredSurebets = surebets.filter((sb) => {
    const matchLeague = selectedLeague === 'All' || sb.league === selectedLeague;
    const matchRoi = sb.roi >= minRoi;
    
    // Filtrar por tipo de mercado según la pestaña activa
    const matchTabType = activeTab === 'live'
      ? (!sb.market_type || sb.market_type === 'FULL_TIME')
      : (sb.market_type === 'OVER_UNDER' || sb.market_type === 'DNB');

    return matchLeague && matchRoi && matchTabType;
  });

  // Si la surebet seleccionada ya no está activa, deseleccionarla
  useEffect(() => {
    if (selectedSurebet) {
      const active = surebets.find((sb) => sb.match_id === selectedSurebet.match_id && sb.market_type === selectedSurebet.market_type);
      if (active) {
        // Actualizar datos dinámicos en vivo en la calculadora
        setSelectedSurebet(active);
      } else {
        setSelectedSurebet(null);
      }
    }
  }, [surebets]);

  // Si el mercado de predicción seleccionado ya no está en la lista activa, deseleccionarlo
  useEffect(() => {
    if (selectedPrediction) {
      const active = predictionOpps.find((opp) => opp.id === selectedPrediction.id);
      if (active) {
        setSelectedPrediction(active);
      } else {
        setSelectedPrediction(null);
      }
    }
  }, [predictionOpps]);

  // Cálculos dinámicos de la calculadora para surebets deportivas
  const getCalcResults = () => {
    if (!selectedSurebet) return null;
    const odds = selectedSurebet.outcomes.map((o) => o.odds);
    const sumInvOdds = odds.reduce((acc, o) => acc + 1 / o, 0);

    // Stakes crudos
    const rawStakes = odds.map((o) => (budget * (1 / o)) / sumInvOdds);
    // Redondear a enteros para evitar bloqueos
    const roundedStakes = rawStakes.map((s) => Math.max(1, Math.round(s)));
    const totalSpent = roundedStakes.reduce((acc, s) => acc + s, 0);

    // Retornos y ganancias
    const returns = roundedStakes.map((s, i) => Math.round(s * odds[i] * 100) / 100);
    const minReturn = Math.min(...returns);
    const profit = Math.round((minReturn - totalSpent) * 100) / 100;
    const roi = Math.round((profit / totalSpent) * 10000) / 100;

    return {
      stakes: roundedStakes,
      returns,
      totalSpent,
      profit,
      roi,
      hasArbitrage: profit > 0,
      arbPercentage: Math.round(sumInvOdds * 10000) / 100
    };
  };

  const calc = getCalcResults();

  // Cálculos dinámicos de la calculadora para mercados de predicción (Polymarket)
  const getPredictionCalcResults = () => {
    if (!selectedPrediction) return null;
    const odds = [selectedPrediction.odds_a, selectedPrediction.odds_b];
    const sumInvOdds = odds.reduce((acc, o) => acc + 1 / o, 0);

    // Stakes crudos
    const rawStakes = odds.map((o) => (budget * (1 / o)) / sumInvOdds);
    // Redondear a enteros
    const roundedStakes = rawStakes.map((s) => Math.max(1, Math.round(s)));
    const totalSpent = roundedStakes.reduce((acc, s) => acc + s, 0);

    // Retornos y ganancias
    const returns = roundedStakes.map((s, i) => Math.round(s * odds[i] * 100) / 100);
    const minReturn = Math.min(...returns);
    const profit = Math.round((minReturn - totalSpent) * 100) / 100;
    const roi = Math.round((profit / totalSpent) * 10000) / 100;

    return {
      stakes: roundedStakes,
      returns,
      totalSpent,
      profit,
      roi,
      hasArbitrage: profit > 0,
      arbPercentage: Math.round(sumInvOdds * 10000) / 100
    };
  };

  const predCalc = getPredictionCalcResults();

  // Cálculos dinámicos de la calculadora para arbitraje cruzado (Cross-Market)
  const getCrossCalcResults = () => {
    if (!selectedCrossOpp) return null;
    const odds = selectedCrossOpp.outcomes.map((o: any) => o.odds);
    const sumInvOdds = odds.reduce((acc: number, o: number) => acc + 1 / o, 0);

    // Stakes crudos
    const rawStakes = odds.map((o: number) => (budget * (1 / o)) / sumInvOdds);
    // Redondear a enteros
    const roundedStakes = rawStakes.map((s: number) => Math.max(1, Math.round(s)));
    const totalSpent = roundedStakes.reduce((acc: number, s: number) => acc + s, 0);

    // Retornos y ganancias
    const returns = roundedStakes.map((s: number, i: number) => Math.round(s * odds[i] * 100) / 100);
    const minReturn = Math.min(...returns);
    const profit = Math.round((minReturn - totalSpent) * 100) / 100;
    const roi = Math.round((profit / totalSpent) * 10000) / 100;

    return {
      stakes: roundedStakes,
      returns,
      totalSpent,
      profit,
      roi,
      hasArbitrage: profit > 0,
      arbPercentage: Math.round(sumInvOdds * 10000) / 100
    };
  };

  const crossCalc = getCrossCalcResults();

  // Registrar apuesta cruzada en el ledger
  const handleRegisterCrossBet = async () => {
    if (!selectedCrossOpp || !crossCalc) return;
    setPlacingBet(true);
    try {
      const outcomes = selectedCrossOpp.outcomes.map((out: any, idx: number) => ({
        outcome: out.outcome,
        bookie: out.bookie,
        odds: out.odds,
        stake: crossCalc.stakes[idx]
      }));

      const res = await fetch('http://localhost:8000/api/cross-bets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sport_match_id: selectedCrossOpp.sport_match_id,
          prediction_market_id: selectedCrossOpp.prediction_market_id,
          teams: selectedCrossOpp.teams,
          outcomes,
          total_spent: crossCalc.totalSpent,
          expected_profit: crossCalc.profit
        })
      });

      if (res.ok) {
        setNotification({ message: '¡Apuesta cruzada registrada exitosamente!', type: 'success' });
        fetchBetsAndStats();
        setSelectedCrossOpp(null);
        setTimeout(() => setNotification(null), 4000);
      } else {
        setNotification({ message: 'Error al registrar la apuesta cruzada.', type: 'error' });
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (err) {
      setNotification({ message: 'Error de red al conectar con el servidor.', type: 'error' });
      setTimeout(() => setNotification(null), 4000);
    } finally {
      setPlacingBet(false);
    }
  };

  // Generar puntos para el gráfico SVG de evolución del capital
  const getChartData = () => {
    const settledBets = bets
      .filter((b) => b.status === 'WON' || b.status === 'LOST' || b.status === 'REFUNDED')
      .sort((a, b) => a.placed_at - b.placed_at);
      
    let cumulative = 0;
    const chartPoints = [{ x: 0, y: 0, date: 'Inicio' }];
    
    settledBets.forEach((bet, index) => {
      let profit = 0;
      if (bet.status === 'WON') {
        profit = (bet.actual_return || (bet.total_spent + bet.expected_profit)) - bet.total_spent;
      } else if (bet.status === 'LOST') {
        profit = -bet.total_spent;
      }
      cumulative += profit;
      
      const dateStr = new Date(bet.placed_at * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + new Date(bet.placed_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      chartPoints.push({
        x: index + 1,
        y: Number(cumulative.toFixed(2)),
        date: dateStr
      });
    });
    
    return chartPoints;
  };

  // Métricas rápidas para el dashboard
  const avgRoi = surebets.length > 0 
    ? (surebets.reduce((acc, sb) => acc + sb.roi, 0) / surebets.length).toFixed(2)
    : "0.00";
  const maxRoi = surebets.length > 0
    ? Math.max(...surebets.map((sb) => sb.roi)).toFixed(2)
    : "0.00";

  return (
    <div className="app-container">
      {/* Header */}
      <header>
        <div className="logo-section">
          <TrendingUp className="logo-icon" size={26} />
          <h1 className="logo-text">SOCCERBETS ARBITRAGE v2</h1>
        </div>

        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button 
            className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`}
            onClick={() => { setActiveTab('live'); setSelectedSurebet(null); }}
          >
            <Activity size={16} />
            <span>Surebets en Vivo (1X2)</span>
          </button>
          <button 
            className={`tab-btn ${activeTab === 'two-way' ? 'active' : ''}`}
            onClick={() => { setActiveTab('two-way'); setSelectedSurebet(null); }}
          >
            <Percent size={16} />
            <span>Mercados 2-Way</span>
          </button>
          <button 
            className={`tab-btn ${activeTab === 'prediction' ? 'active' : ''}`}
            onClick={() => { setActiveTab('prediction'); setSelectedPrediction(null); }}
          >
            <Coins size={16} />
            <span>Predicción</span>
          </button>
          <button 
            className={`tab-btn ${activeTab === 'cross' ? 'active' : ''}`}
            onClick={() => { setActiveTab('cross'); setSelectedCrossOpp(null); }}
          >
            <TrendingUp size={16} />
            <span>Arbitraje Cruzado</span>
          </button>
          <button 
            className={`tab-btn ${activeTab === 'ledger' ? 'active' : ''}`}
            onClick={() => setActiveTab('ledger')}
          >
            <History size={16} />
            <span>Historial y Auditoría</span>
          </button>
        </div>

        <div className="connection-badge">
          <div className={`connection-dot ${connected ? 'connected' : 'disconnected'}`}></div>
          <span>{connected ? 'MOTOR EN VIVO (REDIS)' : 'RECONECTANDO...'}</span>
        </div>
      </header>

      {/* Toast Notification */}
      {notification && (
        <div className={`toast-notification ${notification.type}`}>
          <AlertCircle size={18} />
          <span>{notification.message}</span>
        </div>
      )}

      {/* Main Grid */}
      <main style={{ gridTemplateColumns: activeTab === 'ledger' ? '1fr' : undefined }}>
        {(activeTab === 'live' || activeTab === 'two-way') ? (
          <>
            {/* Left Side: Stats, Filters and Surebet List */}
            <div className="dashboard-left">
              {/* Metrics */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">Surebets Activas</span>
                  <span className="metric-value">{filteredSurebets.length}</span>
                </div>
                <div className="metric-card teal">
                  <span className="metric-label">ROI Promedio</span>
                  <span className="metric-value">{avgRoi}%</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">ROI Máximo Activo</span>
                  <span className="metric-value">{maxRoi}%</span>
                </div>
              </div>

              {/* Filters */}
              <div className="filters-bar">
                <div className="filter-group">
                  <span className="filter-label">Filtrar por Liga</span>
                  <select 
                    className="filter-select"
                    value={selectedLeague}
                    onChange={(e) => setSelectedLeague(e.target.value)}
                  >
                    {leagues.map((l) => (
                      <option key={l} value={l}>{l}</option>
                    ))}
                  </select>
                </div>

                <div className="filter-group">
                  <span className="filter-label">Mínimo ROI (%)</span>
                  <input 
                    type="number" 
                    step="0.1"
                    min="0"
                    className="filter-input"
                    value={minRoi}
                    onChange={(e) => setMinRoi(parseFloat(e.target.value) || 0)}
                  />
                </div>
                
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  <Clock size={16} />
                  <span>Actualizaciones en tiempo real activas (latencia sub-200ms)</span>
                </div>
              </div>

              {/* List Section */}
              <div>
                <div className="list-section-header">
                  <h2>{activeTab === 'live' ? 'Oportunidades de Arbitraje (1X2)' : 'Oportunidades de Arbitraje 2-Way (O/U, DNB)'}</h2>
                  <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
                    Mostrando {filteredSurebets.length} de {surebets.filter(sb => activeTab === 'live' ? (!sb.market_type || sb.market_type === 'FULL_TIME') : (sb.market_type === 'OVER_UNDER' || sb.market_type === 'DNB')).length}
                  </span>
                </div>

                {filteredSurebets.length === 0 ? (
                  <div className="empty-state">
                    <AlertCircle className="empty-icon" size={48} />
                    <div>
                      <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>No hay surebets activas</p>
                      <p style={{ fontSize: '0.85rem' }}>Esperando discrepancias de cuotas del simulador...</p>
                    </div>
                  </div>
                ) : (
                  <div className="surebets-container">
                    {filteredSurebets.map((sb) => (
                      <div 
                        key={`${sb.match_id}-${sb.market_type}`}
                        className={`surebet-card ${selectedSurebet?.match_id === sb.match_id && selectedSurebet?.market_type === sb.market_type ? 'selected' : ''}`}
                        onClick={() => setSelectedSurebet(sb)}
                      >
                        <div className="card-top">
                          <span className="league-badge">{sb.league}</span>
                          {sb.market_type && sb.market_type !== 'FULL_TIME' && (
                            <span className="league-badge" style={{ backgroundColor: 'rgba(13, 148, 136, 0.15)', color: 'var(--accent-teal)', border: '1px solid var(--accent-teal-glow)', marginLeft: '0.5rem' }}>
                              {sb.market_type}
                            </span>
                          )}
                          <span className="roi-badge">+{sb.roi}% ROI</span>
                        </div>

                        <div className="card-teams">
                          {sb.teams}
                        </div>

                        <div className="match-info-row">
                          <div className="info-item">
                            <Clock size={14} />
                            <span>Minuto {sb.minute}'</span>
                          </div>
                          <div className="info-item">
                            <Activity size={14} />
                            <span>Marcador: {sb.score}</span>
                          </div>
                        </div>

                        <div className="card-outcomes">
                          {sb.outcomes.map((out, idx) => (
                            <div key={idx} className="outcome-pill">
                              <span className="outcome-label">{out.outcome}</span>
                              <span className="outcome-bookie">{out.bookie.replace('_', ' ')}</span>
                              <span className="outcome-odds">{out.odds.toFixed(2)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Side: Interactive Stake Calculator */}
            <div className="sidebar-panel">
              <div className="panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-teal)' }}>
                  <Calculator size={20} />
                  <span className="panel-title">Calculadora de Arbitraje</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Ajusta montos con redondeo inteligente para evadir limitaciones de cuentas.
                </p>
              </div>

              {!selectedSurebet ? (
                <div className="no-selection">
                  <BookOpen size={40} />
                  <p>Selecciona una oportunidad de arbitraje de la lista para calcular los stakes óptimos.</p>
                </div>
              ) : (
                <div className="calculator-body">
                  <div>
                    <p style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.25rem' }}>{selectedSurebet.teams}</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {selectedSurebet.league} • Minuto {selectedSurebet.minute}' • Marcador {selectedSurebet.score} {selectedSurebet.market_type ? `• ${selectedSurebet.market_type}` : ''}
                    </p>
                  </div>

                  {/* Budget Input */}
                  <div className="input-container">
                    <div className="input-label-row">
                      <span>Presupuesto Total (Inversión)</span>
                      <span>USD / ARS / EUR</span>
                    </div>
                    <div className="budget-input-wrapper">
                      <span className="currency-symbol">$</span>
                      <input 
                        type="number" 
                        className="budget-input"
                        value={budget}
                        onChange={(e) => setBudget(Math.max(10, parseFloat(e.target.value) || 0))}
                      />
                    </div>
                  </div>

                  {/* Stake Distribution */}
                  <div className="calc-distribution">
                    <p className="filter-label">Distribución de Stakes Redondeados</p>
                    {selectedSurebet.outcomes.map((out, idx) => (
                      <div key={idx} className="dist-row">
                        <div className="dist-left">
                          <span className="dist-outcome">{out.outcome}</span>
                          <span className="dist-sub">{out.bookie.replace('_', ' ')} (Cuota {out.odds.toFixed(2)})</span>
                        </div>
                        <div className="dist-right">
                          <span className="dist-stake">${calc?.stakes[idx]}</span>
                          <span className="dist-return">Retorno: ${calc?.returns[idx]}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Profit Summary */}
                  <div className="calc-summary">
                    <div className="summary-row total-spent">
                      <span>Inversión Real (Redondeada):</span>
                      <span>${calc?.totalSpent}</span>
                    </div>
                    <div className="summary-row total-spent">
                      <span>Porcentaje de Arbitraje (Arb %):</span>
                      <span>{calc?.arbPercentage}%</span>
                    </div>
                    <div className="summary-row profit">
                      <span>Retorno Neto Seguro:</span>
                      <span>+${calc?.profit} ({calc?.roi}%)</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem', backgroundColor: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.15)', borderRadius: '8px', fontSize: '0.75rem', color: 'var(--state-warning)' }}>
                    <ShieldCheck size={28} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>
                      El redondeo a números enteros evita que las casas "soft" detecten patrones algorítmicos automatizados, aumentando la vida útil de tus cuentas.
                    </span>
                  </div>

                  {/* Register Bet Button */}
                  <button 
                    className="register-bet-btn"
                    disabled={placingBet}
                    onClick={handleRegisterBet}
                  >
                    {placingBet ? 'Registrando...' : 'Registrar Apuesta en Ledger'}
                  </button>
                </div>
              )}
            </div>
          </>
        ) : activeTab === 'prediction' ? (
          <>
            {/* Left Side: Stats and Polymarket Prediction Opportunities List */}
            <div className="dashboard-left">
              {/* Metrics */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">Oportunidades Activas</span>
                  <span className="metric-value">{predictionOpps.length}</span>
                </div>
                <div className="metric-card teal">
                  <span className="metric-label">ROI Promedio</span>
                  <span className="metric-value">
                    {(predictionOpps.reduce((acc, o) => acc + o.roi, 0) / (predictionOpps.length || 1)).toFixed(2)}%
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">ROI Máximo Activo</span>
                  <span className="metric-value">
                    {(predictionOpps.length > 0 ? Math.max(...predictionOpps.map(o => o.roi)) : 0.00).toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* List Section */}
              <div>
                <div className="list-section-header">
                  <h2>Contratos de Predicción Polymarket (Yes/No)</h2>
                  <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
                    Oportunidades de arbitraje seguras en base a precios de contratos de eventos reales
                  </span>
                </div>

                {predictionOpps.length === 0 ? (
                  <div className="empty-state">
                    <AlertCircle className="empty-icon" size={48} />
                    <div>
                      <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>No hay oportunidades activas</p>
                      <p style={{ fontSize: '0.85rem' }}>Monitoreando la API pública de Polymarket...</p>
                    </div>
                  </div>
                ) : (
                  <div className="surebets-container">
                    {predictionOpps.map((opp) => (
                      <div 
                        key={opp.id}
                        className={`surebet-card prediction-card ${selectedPrediction?.id === opp.id ? 'selected' : ''}`}
                        onClick={() => setSelectedPrediction(opp)}
                      >
                        <div className="card-top">
                          <span className="league-badge" style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)' }}>Polymarket</span>
                          <span className="roi-badge">+{opp.roi}% ROI</span>
                        </div>

                        <div className="card-teams" style={{ fontSize: '1rem', fontWeight: 600, margin: '0.75rem 0' }}>
                          {opp.question}
                        </div>

                        <div className="card-outcomes">
                          <div className="outcome-pill">
                            <span className="outcome-label">{opp.outcome_a}</span>
                            <span className="outcome-bookie">Yes Contract</span>
                            <span className="outcome-odds">@{opp.odds_a.toFixed(2)}</span>
                          </div>
                          <div className="outcome-pill">
                            <span className="outcome-label">{opp.outcome_b}</span>
                            <span className="outcome-bookie">No Contract</span>
                            <span className="outcome-odds">@{opp.odds_b.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Side: Prediction Calculator */}
            <div className="sidebar-panel">
              <div className="panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-teal)' }}>
                  <Calculator size={20} />
                  <span className="panel-title">Calculadora de Predicciones</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Arbitraje seguro comprando Yes/No en Polymarket.
                </p>
              </div>

              {!selectedPrediction ? (
                <div className="no-selection">
                  <BookOpen size={40} />
                  <p>Selecciona una pregunta de la lista para calcular los stakes óptimos en Polymarket.</p>
                </div>
              ) : (
                <div className="calculator-body">
                  <div>
                    <p style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.25rem' }}>{selectedPrediction.question}</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Contrato de Predicción • Polymarket
                    </p>
                  </div>

                  {/* Budget Input */}
                  <div className="input-container">
                    <div className="input-label-row">
                      <span>Presupuesto Total (Inversión)</span>
                      <span>USD</span>
                    </div>
                    <div className="budget-input-wrapper">
                      <span className="currency-symbol">$</span>
                      <input 
                        type="number" 
                        className="budget-input"
                        value={budget}
                        onChange={(e) => setBudget(Math.max(10, parseFloat(e.target.value) || 0))}
                      />
                    </div>
                  </div>

                  {/* Stake Distribution */}
                  <div className="calc-distribution">
                    <p className="filter-label">Distribución de Stakes en Polymarket</p>
                    
                    <div className="dist-row">
                      <div className="dist-left">
                        <span className="dist-outcome">{selectedPrediction.outcome_a}</span>
                        <span className="dist-sub">Contract Yes (Cuota @{selectedPrediction.odds_a.toFixed(2)})</span>
                      </div>
                      <div className="dist-right">
                        <span className="dist-stake">${predCalc?.stakes[0]}</span>
                        <span className="dist-return">Retorno: ${predCalc?.returns[0]}</span>
                      </div>
                    </div>
                    
                    <div className="dist-row">
                      <div className="dist-left">
                        <span className="dist-outcome">{selectedPrediction.outcome_b}</span>
                        <span className="dist-sub">Contract No (Cuota @{selectedPrediction.odds_b.toFixed(2)})</span>
                      </div>
                      <div className="dist-right">
                        <span className="dist-stake">${predCalc?.stakes[1]}</span>
                        <span className="dist-return">Retorno: ${predCalc?.returns[1]}</span>
                      </div>
                    </div>
                  </div>

                  {/* Profit Summary */}
                  <div className="calc-summary">
                    <div className="summary-row total-spent">
                      <span>Inversión Real:</span>
                      <span>${predCalc?.totalSpent}</span>
                    </div>
                    <div className="summary-row total-spent">
                      <span>Porcentaje de Arbitraje (Arb %):</span>
                      <span>{predCalc?.arbPercentage}%</span>
                    </div>
                    <div className="summary-row profit">
                      <span>Retorno Neto Seguro:</span>
                      <span>+${predCalc?.profit} ({predCalc?.roi}%)</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem', backgroundColor: 'rgba(13, 148, 136, 0.05)', border: '1px solid rgba(13, 148, 136, 0.15)', borderRadius: '8px', fontSize: '0.75rem', color: 'var(--accent-teal)' }}>
                    <ShieldCheck size={28} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>
                      Polymarket liquida contratos a $1.00 USD cada uno. La suma invertida en Yes y No es siempre menor a $1.00 USD por contrato, garantizando ganancias netas.
                    </span>
                  </div>

                  {/* Register Bet Button */}
                  <button 
                    className="register-bet-btn"
                    disabled={placingBet}
                    onClick={handleRegisterPredictionBet}
                  >
                    {placingBet ? 'Registrando...' : 'Registrar Apuesta en Ledger'}
                  </button>
                </div>
              )}
            </div>
          </>
        ) : activeTab === 'cross' ? (
          <>
            {/* Left Side: Cross-Market Opportunities List */}
            <div className="dashboard-left">
              {/* Metrics */}
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">Surebets Cruzadas</span>
                  <span className="metric-value">{crossOpportunities.length}</span>
                </div>
                <div className="metric-card teal">
                  <span className="metric-label">ROI Promedio</span>
                  <span className="metric-value">
                    {(crossOpportunities.reduce((acc, o) => acc + o.roi, 0) / (crossOpportunities.length || 1)).toFixed(2)}%
                  </span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">ROI Máximo Activo</span>
                  <span className="metric-value">
                    {(crossOpportunities.length > 0 ? Math.max(...crossOpportunities.map(o => o.roi)) : 0.00).toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* List Section */}
              <div>
                <div className="list-section-header">
                  <h2>Oportunidades de Arbitraje Cruzado (Cross-Market)</h2>
                  <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
                    Surebets combinando contratos de predicción Yes/No con cuotas tradicionales de partidos de fútbol.
                  </span>
                </div>

                {crossOpportunities.length === 0 ? (
                  <div className="empty-state">
                    <AlertCircle className="empty-icon" size={48} />
                    <div>
                      <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>No hay surebets cruzadas activas</p>
                      <p style={{ fontSize: '0.85rem' }}>Buscando coincidencias entre cuotas tradicionales y contratos de Polymarket...</p>
                    </div>
                  </div>
                ) : (
                  <div className="surebets-container">
                    {crossOpportunities.map((opp) => (
                      <div 
                        key={opp.id}
                        className={`surebet-card cross-card ${selectedCrossOpp?.id === opp.id ? 'selected' : ''}`}
                        onClick={() => setSelectedCrossOpp(opp)}
                      >
                        <div className="card-top">
                          <span className="league-badge" style={{ backgroundColor: 'rgba(139, 92, 246, 0.15)', color: '#8b5cf6', border: '1px solid rgba(139, 92, 246, 0.3)' }}>Cross-Market</span>
                          <span className="roi-badge">+{opp.roi}% ROI</span>
                        </div>

                        <div className="card-teams" style={{ fontSize: '1rem', fontWeight: 600, margin: '0.5rem 0' }}>
                          {opp.teams}
                        </div>
                        
                        <div className="card-question" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                          🔮 {opp.prediction_question}
                        </div>

                        <div className="card-outcomes">
                          {opp.outcomes.map((out: any, idx: number) => (
                            <div key={idx} className="outcome-pill">
                              <span className="outcome-label">{out.outcome}</span>
                              <span className="outcome-bookie">{out.bookie.replace('Bookie_', '').replace('_', ' ')}</span>
                              <span className="outcome-odds">@{out.odds.toFixed(2)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Side: Cross-Market Calculator */}
            <div className="sidebar-panel">
              <div className="panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#8b5cf6' }}>
                  <Calculator size={20} />
                  <span className="panel-title">Calculadora Cruzada</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Stakes óptimos para cubrir todos los escenarios entre Polymarket y casas tradicionales.
                </p>
              </div>

              {!selectedCrossOpp ? (
                <div className="no-selection">
                  <BookOpen size={40} />
                  <p>Selecciona una surebet cruzada de la lista para calcular los stakes óptimos en cada extremo.</p>
                </div>
              ) : (
                <div className="calculator-body">
                  <div>
                    <p style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.25rem' }}>{selectedCrossOpp.teams}</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {selectedCrossOpp.prediction_question}
                    </p>
                  </div>

                  {/* Budget Input */}
                  <div className="input-container">
                    <div className="input-label-row">
                      <span>Presupuesto Total (Inversión)</span>
                      <span>USD</span>
                    </div>
                    <div className="budget-input-wrapper">
                      <span className="currency-symbol">$</span>
                      <input 
                        type="number" 
                        className="budget-input"
                        value={budget}
                        onChange={(e) => setBudget(Math.max(10, parseFloat(e.target.value) || 0))}
                      />
                    </div>
                  </div>

                  {/* Stake Distribution */}
                  <div className="calc-distribution">
                    <p className="filter-label">Distribución de Stakes Sugeridos</p>
                    {selectedCrossOpp.outcomes.map((out: any, idx: number) => (
                      <div key={idx} className="dist-row">
                        <div className="dist-left">
                          <span className="dist-outcome">{out.outcome}</span>
                          <span className="dist-sub">{out.bookie.replace('Bookie_', '').replace('_', ' ')} (Cuota {out.odds.toFixed(2)})</span>
                        </div>
                        <div className="dist-right">
                          <span className="dist-stake">${crossCalc?.stakes[idx]}</span>
                          <span className="dist-return">Retorno: ${crossCalc?.returns[idx]}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Profit Summary */}
                  <div className="calc-summary">
                    <div className="summary-row total-spent">
                      <span>Inversión Real:</span>
                      <span>${crossCalc?.totalSpent}</span>
                    </div>
                    <div className="summary-row total-spent">
                      <span>Porcentaje de Arbitraje (Arb %):</span>
                      <span>{crossCalc?.arbPercentage}%</span>
                    </div>
                    <div className="summary-row profit">
                      <span>Retorno Neto Seguro:</span>
                      <span>+${crossCalc?.profit} ({crossCalc?.roi}%)</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem', backgroundColor: 'rgba(139, 92, 246, 0.05)', border: '1px solid rgba(139, 92, 246, 0.15)', borderRadius: '8px', fontSize: '0.75rem', color: '#8b5cf6' }}>
                    <ShieldCheck size={28} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>
                      Esta apuesta combina la seguridad del contrato de Polymarket con las cuotas máximas de casas de apuestas tradicionales.
                    </span>
                  </div>

                  {/* Register Bet Button */}
                  <button 
                    className="register-bet-btn"
                    disabled={placingBet}
                    onClick={handleRegisterCrossBet}
                    style={{ backgroundColor: '#8b5cf6', borderColor: '#8b5cf6' }}
                  >
                    {placingBet ? 'Registrando...' : 'Registrar Apuesta en Ledger'}
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="ledger-view">
            {/* SVG Chart of Cumulative Profit */}
            {bets.filter((b) => b.status === 'WON' || b.status === 'LOST').length > 0 && (
              <div className="ledger-table-container" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                  Evolución Histórica del Capital (Ganancia Neta Acumulada)
                </h3>
                <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
                  {(() => {
                    const chartData = getChartData();
                    if (chartData.length < 2) return <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Registra más apuestas finalizadas para visualizar tu curva de crecimiento.</p>;
                    
                    const width = 600;
                    const height = 180;
                    const padding = 30;
                    
                    const maxX = chartData.length - 1;
                    
                    const yValues = chartData.map((d) => d.y);
                    const minY = Math.min(...yValues) < 0 ? Math.min(...yValues) * 1.15 : 0;
                    const maxY = Math.max(...yValues) > 0 ? Math.max(...yValues) * 1.15 : 10;
                    
                    // Generate points string for line
                    const points = chartData.map((d, i) => {
                      const sx = padding + (i / maxX) * (width - 2 * padding);
                      const sy = height - padding - ((d.y - minY) / (maxY - minY)) * (height - 2 * padding);
                      return `${sx},${sy}`;
                    }).join(' ');
                    
                    // Generate path string for gradient area
                    const areaPoints = [
                      `${padding},${height - padding}`, // start bottom left
                      ...chartData.map((d, i) => {
                        const sx = padding + (i / maxX) * (width - 2 * padding);
                        const sy = height - padding - ((d.y - minY) / (maxY - minY)) * (height - 2 * padding);
                        return `${sx},${sy}`;
                      }),
                      `${width - padding},${height - padding}` // end bottom right
                    ].join(' ');

                    return (
                      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
                        <defs>
                          <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--accent-teal)" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="var(--accent-teal)" stopOpacity="0.00" />
                          </linearGradient>
                        </defs>
                        {/* Grid lines */}
                        <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="rgba(255,255,255,0.05)" />
                        <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="rgba(255,255,255,0.05)" />
                        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
                        
                        {/* Area fill */}
                        <polygon points={areaPoints} fill="url(#chart-grad)" />
                        
                        {/* Line path */}
                        <polyline points={points} fill="none" stroke="var(--accent-teal)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
                        
                        {/* Points and Tooltips */}
                        {chartData.map((pt, i) => {
                          const sx = padding + (i / maxX) * (width - 2 * padding);
                          const sy = height - padding - ((pt.y - minY) / (maxY - minY)) * (height - 2 * padding);
                          return (
                            <g key={i} className="chart-dot-group">
                              <circle cx={sx} cy={sy} r="4.5" fill="#1e293b" stroke="var(--accent-teal)" strokeWidth="2.5" />
                              <title>{`${pt.date}\nCapital: $${pt.y}`}</title>
                            </g>
                          );
                        })}
                        {/* Y-axis Labels */}
                        <text x={padding - 8} y={padding + 4} fill="var(--text-secondary)" fontSize="10" textAnchor="end">${maxY.toFixed(0)}</text>
                        <text x={padding - 8} y={height - padding + 4} fill="var(--text-secondary)" fontSize="10" textAnchor="end">${minY.toFixed(0)}</text>
                        {/* X-axis Labels */}
                        <text x={padding} y={height - 8} fill="var(--text-secondary)" fontSize="10" textAnchor="middle">Inicio</text>
                        <text x={width - padding} y={height - 8} fill="var(--text-secondary)" fontSize="10" textAnchor="middle">Actual</text>
                      </svg>
                    );
                  })()}
                </div>
              </div>
            )}

            {/* Stats Cards */}
            <div className="metrics-grid stats-grid">
              <div className="metric-card">
                <span className="metric-label">Inversión Histórica</span>
                <span className="metric-value">${stats.total_spent.toFixed(2)}</span>
              </div>
              <div className={`metric-card ${stats.net_profit >= 0 ? 'green-card' : 'red-card'}`}>
                <span className="metric-label">Ganancia Real Neta</span>
                <span className="metric-value">
                  {stats.net_profit >= 0 ? '+' : ''}${stats.net_profit.toFixed(2)}
                </span>
              </div>
              <div className={`metric-card ${stats.roi >= 0 ? 'green-card' : 'red-card'}`}>
                <span className="metric-label">ROI Real Neto</span>
                <span className="metric-value">
                  {stats.roi >= 0 ? '+' : ''}{stats.roi.toFixed(2)}%
                </span>
              </div>
              <div className="metric-card teal">
                <span className="metric-label">Tasa de Aciertos</span>
                <span className="metric-value">{stats.win_rate.toFixed(1)}%</span>
                <span className="metric-subtext" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {stats.count_won} G / {stats.count_lost} P de {stats.count_total - stats.count_pending} finalizadas
                </span>
              </div>
            </div>

            {/* Bet Ledger Table */}
            <div className="ledger-table-container">
              <div className="list-section-header">
                <h2>Historial de Apuestas Auditadas</h2>
                <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
                  Total: {bets.length} apuesta(s) ({stats.count_pending} pendientes)
                </span>
              </div>

              {bets.length === 0 ? (
                <div className="empty-state">
                  <BookOpen className="empty-icon" size={48} />
                  <div>
                    <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>No hay apuestas registradas</p>
                    <p style={{ fontSize: '0.85rem' }}>Las apuestas que registres desde la calculadora aparecerán aquí.</p>
                  </div>
                </div>
              ) : (
                <div className="bets-table-wrapper">
                  <table className="ledger-table">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Partido / Liga</th>
                        <th>Inversión</th>
                        <th>Retorno Esperado</th>
                        <th>Distribución</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bets.map((bet) => {
                        const dateStr = new Date(bet.placed_at * 1000).toLocaleString();
                        return (
                          <tr key={bet.id} className="ledger-row">
                            <td className="date-cell">{dateStr}</td>
                            <td>
                              <div className="match-teams" style={{ fontWeight: 600 }}>{bet.teams}</div>
                              <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', marginTop: '0.25rem' }}>
                                {bet.is_prediction === 1 ? (
                                  <span className="league-badge" style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)', padding: '0.05rem 0.3rem', fontSize: '0.65rem', borderRadius: '4px' }}>Predicción</span>
                                ) : bet.is_prediction === 2 ? (
                                  <span className="league-badge" style={{ backgroundColor: 'rgba(139, 92, 246, 0.15)', color: '#8b5cf6', border: '1px solid rgba(139, 92, 246, 0.3)', padding: '0.05rem 0.3rem', fontSize: '0.65rem', borderRadius: '4px' }}>Cruzado</span>
                                ) : (
                                  <>
                                    <span className="league-badge" style={{ padding: '0.05rem 0.3rem', fontSize: '0.65rem', borderRadius: '4px' }}>Deporte</span>
                                    <span className="league-badge" style={{ padding: '0.05rem 0.3rem', fontSize: '0.65rem', backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-secondary)', borderRadius: '4px' }}>
                                      {bet.outcomes[0]?.outcome.includes('DNB') ? 'DNB' : bet.outcomes[0]?.outcome.includes('Goles') ? 'O/U' : '1X2'}
                                    </span>
                                  </>
                                )}
                                <span className="match-league" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{bet.league}</span>
                              </div>
                            </td>
                            <td className="amount-cell">${bet.total_spent.toFixed(2)}</td>
                            <td className="amount-cell" style={{ color: 'var(--state-success)', fontWeight: 600 }}>+${bet.expected_profit.toFixed(2)}</td>
                            <td>
                              <div className="outcome-dist">
                                {bet.outcomes.map((out: any, idx: number) => (
                                  <div key={idx} className="dist-pill-small">
                                    <span style={{ fontWeight: 600 }}>{out.outcome.split(' ')[0]}: </span>
                                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>{out.bookie.replace('Bookie_', '').replace('_', ' ')}</span>
                                    <span style={{ color: 'var(--accent-teal)' }}> @{out.odds.toFixed(2)}</span>
                                    <span style={{ fontWeight: 600 }}> (${out.stake})</span>
                                  </div>
                                ))}
                              </div>
                            </td>
                            <td>
                              <span className={`status-badge ${bet.status.toLowerCase()}`}>
                                {bet.status}
                              </span>
                            </td>
                            <td>
                              {bet.status === 'PENDING' ? (
                                <div className="action-buttons">
                                  <button 
                                    className="settle-btn won"
                                    onClick={() => handleSettleBet(bet.id, 'WON')}
                                  >
                                    <CheckCircle2 size={14} />
                                    <span>Ganada</span>
                                  </button>
                                  <button 
                                    className="settle-btn lost"
                                    onClick={() => handleSettleBet(bet.id, 'LOST')}
                                  >
                                    <XCircle size={14} />
                                    <span>Perdida</span>
                                  </button>
                                </div>
                              ) : (
                                <span className="settled-info">
                                  Retorno: ${bet.actual_return.toFixed(2)}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

