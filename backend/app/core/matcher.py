from metaphone import doublemetaphone
from rapidfuzz import fuzz

def get_phonetic_keys(name: str) -> set[str]:
    """
    Genera un conjunto de claves fonéticas para una cadena de texto (nombre de equipo),
    filtrando palabras genéricas de fútbol.
    """
    clean_name = name.lower()
    # Eliminar términos comunes para no sesgar la fonética
    stopwords = {"fc", "cf", "sc", "united", "city", "town", "athletic", "club", "de", "del", "al"}
    words = [w for w in clean_name.split() if w not in stopwords]
    
    keys = set()
    for word in words:
        p_key, a_key = doublemetaphone(word)
        if p_key:
            keys.add(p_key)
        if a_key:
            keys.add(a_key)
    return keys

def match_teams_phonetic(name_a: str, name_b: str) -> bool:
    """
    Determina si dos nombres tienen coincidencia fonética básica compartiendo al menos una clave fonética clave.
    """
    keys_a = get_phonetic_keys(name_a)
    keys_b = get_phonetic_keys(name_b)
    
    # Si comparten al menos una clave fonética no vacía, hay coincidencia fonética
    return len(keys_a.intersection(keys_b)) > 0

def calculate_similarity(name_a: str, name_b: str) -> float:
    """
    Calcula un score de similitud (0-100) combinando token set ratio y coincidencia fonética.
    """
    # 1. Similitud de tokens difusos
    token_score = fuzz.token_set_ratio(name_a, name_b)
    
    # 2. Coincidencia fonética (bonificación si coincide fonéticamente)
    phonetic_match = match_teams_phonetic(name_a, name_b)
    
    final_score = token_score
    if phonetic_match and token_score >= 60:
        # Dar un bono si coinciden fonéticamente y tienen cierta similitud ortográfica
        final_score = min(100.0, token_score + 10)
        
    return float(final_score)

def find_best_match(team_name: str, choices: list[str], threshold: float = 75.0) -> tuple[str, float] | None:
    """
    Busca el mejor nombre de coincidencia para un equipo dentro de una lista de opciones.
    Devuelve (nombre_elegido, score) o None si está por debajo del umbral.
    """
    if not choices:
        return None
        
    best_choice = None
    best_score = 0.0
    
    for choice in choices:
        score = calculate_similarity(team_name, choice)
        if score > best_score:
            best_score = score
            best_choice = choice
            
    if best_score >= threshold:
        return best_choice, best_score
        
    return None
