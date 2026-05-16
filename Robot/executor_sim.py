# -*- coding: utf-8 -*-
"""
sim_executor.py
Simula la ejecución de acciones del robot y el guardado de audio.
En producción esto se reemplaza por ros_commander.py y audio_player.py.
"""

import os
import base64
import tempfile
from datetime import datetime
from audio_player import play_audio
from config_robot import AUDIO_SAVE_DIR, SIMULATED_POSITION

# Acciones de movimiento válidas
MOVE_ACTIONS = {"MOVE:adelante", "MOVE:atras", "MOVE:derecha", "MOVE:izquierda"}


def execute_action(action):
    """
    Simula la ejecución de una acción.
    Devuelve True si la acción fue reconocida, False si no.
    """
    if action is None:
        return False

    if action in MOVE_ACTIONS:
        direction = action.split(":")[1]
        print("[SIM] Movimiento ejecutado: {} → OK".format(direction))
        return True

    if action == "QUERY:POSITION":
        pos = SIMULATED_POSITION
        print("[SIM] Posicion consultada → x={x}, y={y}, sector={sector}".format(**pos))
        return True

    if action == "QUERY:INFO":
        print("[SIM] Info consultada → Summit XL, robot de rescate, simulacion activa")
        return True

    print("[SIM] Accion desconocida: {}".format(action))
    return False


# def save_audio(audio_b64):
#     """
#     Decodifica el audio en base64 y lo guarda en AUDIO_SAVE_DIR
#     con timestamp en el nombre. Devuelve la ruta guardada o None.
#     """
#     if not audio_b64:
#         return None

#     os.makedirs(AUDIO_SAVE_DIR, exist_ok=True)

#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename  = "respuesta_{}.wav".format(timestamp)
#     filepath  = os.path.join(AUDIO_SAVE_DIR, filename)

#     try:
#         audio_bytes = base64.b64decode(audio_b64)
#         with open(filepath, "wb") as f:
#             f.write(audio_bytes)
#         print("[SIM] Audio guardado en: {}".format(filepath))
#         return filepath
#     except Exception as e:
#         print("[SIM] Error guardando audio: {}".format(e))
#         return None



# En simulación el audio usa exactamente la misma función que en real
save_audio = play_audio