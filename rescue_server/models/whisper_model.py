import whisper
from config import WHISPER_MODEL_NAME, WHISPER_DEVICE

_model = None

def get_whisper():
    global _model
    if _model is None:
        print(f"Cargando Whisper '{WHISPER_MODEL_NAME}' en {WHISPER_DEVICE}...")
        _model = whisper.load_model(WHISPER_MODEL_NAME, device=WHISPER_DEVICE)
        print("Whisper cargado.")
    return _model

def transcribe(audio_path: str, language: str = "es") -> str:
    model = get_whisper()
    result = model.transcribe(audio_path, language=language)
    return result["text"].strip()
