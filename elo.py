# Actualiza el ELO de dos jugadores y guarda el resultado
from constants import K_FACTOR

def update_elo(jugador1, jugador2, ganador, score_str=None):
    elo_data = load_elo()
    id1 = jugador1.id if hasattr(jugador1, 'id') else jugador1['id']
    id2 = jugador2.id if hasattr(jugador2, 'id') else jugador2['id']
    ganador_id = ganador.id if hasattr(ganador, 'id') else ganador['id']
    # Valor inicial si no existe
    rating1 = elo_data.get(str(id1), 1000)
    rating2 = elo_data.get(str(id2), 1000)
    # Resultado esperado
    expected1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
    expected2 = 1 / (1 + 10 ** ((rating1 - rating2) / 400))
    # Resultado real
    if ganador_id == id1:
        score1, score2 = 1, 0
    else:
        score1, score2 = 0, 1
    # K_FACTOR dinámico según diferencia de rondas
    k = K_FACTOR
    if score_str:
        try:
            s1, s2 = [int(x) for x in score_str.split('-')]
            diff = abs(s1 - s2)
            total = s1 + s2
            # K_FACTOR proporcional: más diferencia y más rounds, más ELO
            k = 20 + int(diff * (total / 5))
            k = max(20, min(100, k))
        except Exception:
            k = K_FACTOR
    # Si la diferencia es extrema (>= 70% de los rounds), ignora el factor de expectativa
    if score_str:
        try:
            s1, s2 = [int(x) for x in score_str.split('-')]
            diff = abs(s1 - s2)
            total = s1 + s2
            if diff >= int(0.7 * total):
                # Gana el K_FACTOR completo
                if ganador_id == id1:
                    new_rating1 = rating1 + k
                    new_rating2 = rating2 - k
                else:
                    new_rating1 = rating1 - k
                    new_rating2 = rating2 + k
            else:
                new_rating1 = rating1 + k * (score1 - expected1)
                new_rating2 = rating2 + k * (score2 - expected2)
        except Exception:
            new_rating1 = rating1 + k * (score1 - expected1)
            new_rating2 = rating2 + k * (score2 - expected2)
    else:
        new_rating1 = rating1 + k * (score1 - expected1)
        new_rating2 = rating2 + k * (score2 - expected2)
    elo_data[str(id1)] = round(new_rating1)
    elo_data[str(id2)] = round(new_rating2)
    save_elo(elo_data)
# elo.py

import json
import os

ELO_FILE = "elo.json"

# Cargar el Elo de los jugadores desde el archivo JSON
def load_elo():
    if not os.path.exists(ELO_FILE):
        return {}
    try:
        with open(ELO_FILE, 'r') as file:
            return json.load(file)
    except Exception:
        return {}

# Guardar el Elo de los jugadores en el archivo JSON
def save_elo(elo_data):
    with open(ELO_FILE, 'w') as file:
        json.dump(elo_data, file, indent=4)
