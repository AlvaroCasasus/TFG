import requests

IP_RECEPTOR = "150.244.56.149"   # <-- Cambia a la IP del receptor
SERVER_URL = f"http://{IP_RECEPTOR}:8888/upload"

def enviar_audio(path_audio):
    files = {"audio": open(path_audio, "rb")}
    response = requests.post(SERVER_URL, files=files)

    print("Respuesta del servidor:", response.json())

# Ejemplo: envía un audio
enviar_audio("PruebaSonidoRescate6.ogg")
