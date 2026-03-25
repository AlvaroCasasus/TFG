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
    result = model.transcribe(
        audio_path,
        language="es",
        temperature=0.0,        # completamente determinista
        best_of=1,              # sin muestreo múltiple
        beam_size=5,            # búsqueda en haz más exhaustiva
        no_speech_threshold=0.6, # descarta audio si probabilidad de silencio > 60%
        compression_ratio_threshold=2.4,  # descarta alucinaciones
        condition_on_previous_text=False  # cada fragmento independiente
    )
    return result["text"].strip()
