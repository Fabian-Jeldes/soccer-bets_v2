def calculate_arbitrage_percentage(odds: list[float]) -> float:
    """
    Calcula el porcentaje de arbitraje para un conjunto de cuotas.
    Si el resultado es < 1.0 (100%), existe una oportunidad de surebet.
    """
    if not odds or any(o <= 0 for o in odds):
        return 1.0
    return sum(1.0 / o for o in odds)

def calculate_stakes(budget: float, odds: list[float], round_to_int: bool = True) -> dict:
    """
    Calcula la distribución de montos a apostar para cada cuota basándose en un presupuesto (budget).
    Si round_to_int es True, los montos se redondean a números enteros para evadir bloqueos de bookies
    y se recalcula el retorno y ganancia real.
    """
    arb_pct = calculate_arbitrage_percentage(odds)
    if arb_pct >= 1.0:
        return {"has_arbitrage": False, "roi": 0.0, "stakes": [], "returns": [], "profit": 0.0}

    raw_stakes = [(budget * (1.0 / o)) / arb_pct for o in odds]
    
    if round_to_int:
        # Redondear cada stake al entero más cercano
        stakes = [max(1.0, round(s)) for s in raw_stakes]
        # Ajustar el último stake para no exceder/subestimar demasiado el presupuesto total si es crítico,
        # o simplemente usar la suma real de stakes como el nuevo presupuesto invertido.
        total_spent = sum(stakes)
    else:
        stakes = raw_stakes
        total_spent = budget

    # Calcular retornos individuales (cada escenario posible)
    returns = [round(s * o, 2) for s, o in zip(stakes, odds)]
    min_return = min(returns)
    profit = round(min_return - total_spent, 2)
    roi = round((profit / total_spent) * 100, 2)

    return {
        "has_arbitrage": profit > 0,
        "arb_percentage": round(arb_pct * 100, 2),
        "roi": roi,
        "total_spent": total_spent,
        "stakes": stakes,
        "returns": returns,
        "profit": profit
    }

def convert_prediction_market_to_decimal(cents_price: float) -> float:
    """
    Convierte el precio de un contrato en centavos (0-100) de mercados de predicción (Polymarket, Kalshi)
    a cuota decimal equivalente.
    """
    if cents_price <= 0 or cents_price >= 100:
        return 1.00
    return round(1.0 / (cents_price / 100.0), 4)

def calculate_effective_odds(decimal_odds: float, commission_rate: float) -> float:
    """
    Calcula la cuota decimal efectiva real descontando una comisión fija sobre la ganancia neta.
    commission_rate es un flotante entre 0.0 y 1.0 (ej. 0.02 para 2%).
    """
    if decimal_odds <= 1.0:
        return 1.0
    return round(1.0 + (decimal_odds - 1.0) * (1.0 - commission_rate), 4)
