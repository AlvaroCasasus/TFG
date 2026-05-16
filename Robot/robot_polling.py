#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
robot_client_sim.py
Loop principal del cliente del robot Summit XL.
 
Modo simulado  (SIMULATION_MODE = True):
  - Acciones: imprime el resultado y devuelve True
  - Audio:    guarda el .wav en received_audio/
  - Posición: usa SIMULATED_POSITION de config_robot.py
 
Modo real (SIMULATION_MODE = False):
  - Acciones: publica en /cmd_vel vía ROS
  - Audio:    reproduce por altavoz Bluetooth
  - Posición: lee desde el topic de odometría
 
Para pasar a real: cambia SIMULATION_MODE = False en config_robot.py
"""
 
from __future__ import print_function
 
import os
import sys
import time
import requests
 
from audio_capture import record_until_silence
from config_robot import (
    SERVER_URL, POLL_INTERVAL, MAX_BACKOFF,
    SIMULATION_MODE, SIMULATED_POSITION
)
import signal
import sys

def signal_handler(sig, frame):
    print("\n[Robot] Detenido.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
 
# ── Importación condicional sim / real ───────────────────
if SIMULATION_MODE:
    from executor_sim import execute_action, save_audio as play_audio
    print("[Modo] SIMULACIÓN activa")
 
    def get_position():
        return SIMULATED_POSITION
 
else:
    from ros_commander import init_ros, execute_action, get_position
    from audio_player  import play_audio
    print("[Modo] ROBOT REAL activo")
    init_ros()
# ─────────────────────────────────────────────────────────
 
 
def fetch_pending(position):
    """
    POST /pending con la posición actual del robot.
    Devuelve ("ok", item), ("empty", None) o ("error", None).
    """
    try:
        r = requests.post(
            "{}/pending".format(SERVER_URL),
            json={"position": position},
            timeout=5
        )
 
        if r.status_code == 200:
            data = r.json()
            if data.get("pending"):
                return "ok", data
            return "empty", None        # servidor OK pero sin pendientes
 
        print("[Polling] HTTP {}".format(r.status_code))
        return "error", None
 
    except requests.exceptions.ConnectionError:
        print("[Polling] Sin conexión con el servidor.")
    except requests.exceptions.Timeout:
        print("[Polling] Timeout.")
    except Exception as e:
        print("[Polling] Error inesperado: {}".format(e))
 
    return "error", None
 
 
def upload_audio(audio_path):
    try:
        with open(audio_path, "rb") as f:
            r = requests.post(
                "{}/upload".format(SERVER_URL),
                files={"audio": ("audio.wav", f, "audio/wav")},
                timeout=60
            )
        if r.status_code == 200:
            data = r.json()
            print("[Upload] Transcripcion : {}".format(
                data.get("transcripcion", "").encode("utf-8")))
            print("[Upload] Respuesta LLM : {}".format(
                data.get("respuesta", "").encode("utf-8")))
            return data
        else:
            print("[Upload] Error HTTP {}".format(r.status_code))
    except Exception as e:
        print("[Upload] Fallo enviando audio: {}".format(str(e)))
    return None
 
 
def main_loop():
    backoff            = POLL_INTERVAL
    consecutive_errors = 0
 
    print("[Robot] Iniciando. Servidor: {}".format(SERVER_URL))
    print("-" * 55)
 
    while True:
        position = get_position()
 
        # ── 1. Capturar y enviar audio ───────────────────
        audio_path = None
        try:
            audio_path = record_until_silence()
            upload_audio(audio_path)
        except Exception as e:
            print("[Robot] Error en captura/envio: {}".format(e))
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
 
        # ── 2. Consultar pendientes ──────────────────────
        status, item = fetch_pending(position)
 
        if status == "ok":
            consecutive_errors = 0
            backoff = POLL_INTERVAL
 
            action = item.get("action")
            audio  = item.get("audio")
 
            if action:
                ok = execute_action(action)
                print("[Robot] Accion '{}' → {}".format(action, "OK" if ok else "FALLO"))
            else:
                print("[Robot] Sin accion en este item.")
 
            if audio:
                play_audio(audio)
            else:
                print("[Robot] Sin audio en este item.")
 
        elif status == "empty":
            # El servidor responde bien, no hay nada pendiente — comportamiento normal
            consecutive_errors = 0
            backoff = POLL_INTERVAL
 
        elif status == "error":
            consecutive_errors += 1
            if consecutive_errors >= 3:
                backoff = min(backoff * 2, MAX_BACKOFF)
                print("[Robot] {} fallos seguidos. Reintentando en {}s...".format(
                    consecutive_errors, backoff))
 
        time.sleep(backoff)
 
 
if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[Robot] Detenido.")
        sys.exit(0)
