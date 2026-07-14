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

  // Estados de la Fase 2 (Ledger de Apuestas y Persistencia) e Integración de Fase 3
  const [activeTab, setActiveTab] = useState<'live' | 'two-way' | 'prediction' | 'ledger'>('live');
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

  useEffect(() => {
    fetchBetsAndStats();
    
    if (activeTab === 'prediction') {
      fetchPredictionOpps();
      const interval = setInterval(fetchPredictionOpps, 3000);
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
  const updateBuffer = useRef<Surebet[]>([]);
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
          // Agregar al buffer para aplicar batching
          updateBuffer.current.push(msg.data);
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

        setSurebets((prev) => {
          const next = [...prev];
          for (const newSb of batch) {
            const idx = next.findIndex((item) => item.match_id === newSb.match_id);
            if (idx > -1) {
              next[idx] = newSb;
            } else {
              next.push(newSb);
            }
          }
          // Ordenar por ROI descendente
          return next.sort((a, b) => b.roi - a.roi);
        });
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
        ) : (
          <div className="ledger-view">
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

