#robot/actions.py
import requests
from config import ROBOT_IP, ROBOT_PORT
ROBOT_URL = f"http://{ROBOT_IP}:{ROBOT_PORT}"


def init_robot():
    """
    Inicializa la conexión con el robot.
    """
    # --- API REST ---
    try:
        response = requests.get(f"http://10.27.41.52:8888/status", timeout=3)
        if response.status_code == 200:
            print("[Robot] Conexión OK.")
    except requests.exceptions.ConnectionError:
        print("[Robot] AVISO: No se pudo conectar. ¿Está encendido?")
    except requests.exceptions.Timeout:
        print("[Robot] AVISO: Timeout al conectar.")



def mover_robot(direccion: str) -> bool:
    """
    Envía un comando de movimiento al robot.
    Devuelve True si el comando se ejecutó correctamente.
 
    Valores esperados de direccion: 'adelante', 'atras', 'derecha', 'izquierda'
    """

    return true



def obtener_posicion() -> str:
    """
    Consulta la posición actual del robot.
    Devuelve un string descriptivo para enviar por audio.
    """
    return "Ubicación Universidad Autónoma de Madrid"

