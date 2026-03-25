import requests
import os
from config import ROBOT_IP, ROBOT_PORT, ROBOT_AUDIO_ENDPOINT

def send_audio_to_robot(audio_path: str) -> bool:
    """Envía el fichero de audio al robot. Devuelve True si ok."""
    url = f"http://{ROBOT_IP}:{ROBOT_PORT}{ROBOT_AUDIO_ENDPOINT}"
    try:
        with open(audio_path, "rb") as f:
            response = requests.post(
                url,
                files={"audio": ("response.wav", f, "audio/wav")},
                timeout=5
            )
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"[Robot] No se pudo conectar a {url}")
        return False
    except requests.exceptions.Timeout:
        print(f"[Robot] Timeout enviando audio al robot.")
        return False
