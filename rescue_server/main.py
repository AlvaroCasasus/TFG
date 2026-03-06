from flask import Flask
from routes.audio import audio_bp
from models.whisper_model import get_whisper
from models.gemma_model import get_gemma

app = Flask(__name__)
app.register_blueprint(audio_bp)

if __name__ == "__main__":
    print("Servidor Whisper + Gemma-3 activo en puerto 8888")
    # Precarga al arrancar
    get_whisper()
    get_gemma()
    app.run(host="0.0.0.0", port=8888)
