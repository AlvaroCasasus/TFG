import json
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_MAX_BYTES
from processing.classifier import classify

# Rotación automática: máximo 10 MB, guarda 3 ficheros históricos
_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=3, encoding="utf-8")

def save_event(transcription: str, response: str, duration_whisper: float, duration_gemma: float):
    tipo = classify(response)
    event = {
        "timestamp": datetime.now().isoformat(),
        "audio_transcrito": transcription,
        "informe_agente": response,
        "tipo": tipo,
        "relevante": tipo in ("victima", "operario"),
        "tiempos": {
            "whisper_s": round(duration_whisper, 2),
            "gemma_s": round(duration_gemma, 2)
        }
    }
    _handler.stream = open(LOG_FILE, "a", encoding="utf-8")
    _handler.stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    _handler.stream.close()
