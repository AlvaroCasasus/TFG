# -*- coding: utf-8 -*-
"""
audio_player.py
Guarda y reproduce audio recibido del servidor por Bluetooth.

Requisitos:
    sudo apt install pulseaudio pulseaudio-module-bluetooth

Para encontrar el nombre exacto del sink Bluetooth:
    pactl list sinks short
    → copia el nombre que empiece por 'bluez_sink' y ponlo en config_robot.py
"""

import os
import base64
import subprocess
import subprocess
import os
from datetime import datetime
from config_robot import AUDIO_SAVE_DIR, BLUETOOTH_SINK_NAME


def _get_bluetooth_sink():
    """
    Busca el sink Bluetooth activo en PulseAudio.
    Primero intenta con BLUETOOTH_SINK_NAME de config_robot.py;
    si no lo encuentra, busca automáticamente cualquier bluez_sink activo.
    """
    try:
	with open(os.devnull, "w") as devnull:
	    result = subprocess.check_output(
		["pactl", "list", "sinks", "short"],
		stderr=devnull
	    ).decode()

        for line in result.splitlines():
            if BLUETOOTH_SINK_NAME in line:
                return line.split()[1]

        # Fallback: cualquier sink bluez disponible
        for line in result.splitlines():
            if "bluez_sink" in line:
                sink = line.split()[1]
                print("[Audio] Sink '{}' no encontrado. Usando: {}".format(
                    BLUETOOTH_SINK_NAME, sink))
                return sink

        print("[Audio] No se encontró ningún sink Bluetooth.")
        print("[Audio] Comprueba que el dispositivo está conectado: pactl list sinks short")

    except OSError:
	print("[Audio] pactl no disponible.")
    except Exception as e:
        print("[Audio] Error buscando sink Bluetooth: {}".format(e))

    return None




def _reproduce(filepath):
    sink = _get_bluetooth_sink()
    if not sink:
        print("[Audio] Sin sink Bluetooth. Audio guardado en: {}".format(filepath))
        return

    # Convertir a formato compatible con Bluetooth (44100Hz stereo)
    converted = filepath.replace(".wav", "_bt.wav")
    try:
        subprocess.call([
            "ffmpeg", "-y", "-i", filepath,
            "-ar", "44100", "-ac", "2",
            converted
        ])
        print("[Audio] Reproduciendo por Bluetooth: {}".format(sink))
        ret = subprocess.call(["paplay", "--device={}".format(sink), converted])
        if ret != 0:
            print("[Audio] paplay fallo (codigo {}).".format(ret))
    except Exception as e:
        print("[Audio] Error: {}".format(e))
    finally:
	pass
        #if os.path.exists(converted):
         #   os.remove(converted)


def play_audio(audio_b64):
    """
    Decodifica el audio base64, lo guarda con timestamp y lo reproduce por Bluetooth.
    """
    if not audio_b64:
        return

    if not os.path.exists(AUDIO_SAVE_DIR):
    	os.makedirs(AUDIO_SAVE_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = os.path.join(AUDIO_SAVE_DIR, "respuesta_{}.wav".format(timestamp))

    try:
        audio_bytes = base64.b64decode(audio_b64)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        print("[Audio] Guardado en: {}".format(filepath))
        _reproduce(filepath)
    except Exception as e:
        print("[Audio] Error procesando audio: {}".format(e))
