from flask import Flask
from routes.audio import audio_bp
from models.whisper_model import get_whisper
from models.gemma_model import get_gemma
from queue import Queue

app = Flask(__name__)
pending = Queue()
app.config["PENDING"] = pending
app.config["ROBOT_POSITION"] = None  # se rellena con el primer poll
app.register_blueprint(audio_bp)

if __name__ == "__main__":
   
    # Precarga los modelos al arrancar
    get_whisper()
    get_gemma()


    print("Servidor Whisper + Gemma-3 activo en puerto 8888")
    app.run(host="0.0.0.0", port=8888)
