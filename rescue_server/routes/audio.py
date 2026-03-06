import os
import time
import tempfile
from flask import Blueprint, request, jsonify
from models.whisper_model import transcribe
from models.gemma_model import generate
from processing.classifier import extract_first_block
from processing.command_handler import handle
from logging_handler import save_event
from config import AUDIO_MAX_BYTES, ALLOWED_AUDIO_EXTENSIONS

audio_bp = Blueprint("audio", __name__)

def _build_prompt(system_prompt: str, user_input: str) -> str:
    return f"{system_prompt}\n\n### ENTRADA REAL (NO ES EJEMPLO)\n{user_input}\n\n### RESPUESTA DEL SISTEMA\n"

with open("prompts/system_prompt.txt", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

@audio_bp.route("/upload", methods=["POST"])
def upload_audio():
    # --- Validación ---
    if "audio" not in request.files:
        return jsonify({"error": "Falta el archivo de audio."}), 400

    audio_file = request.files["audio"]
    ext = os.path.splitext(audio_file.filename or "")[-1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({"error": f"Formato no soportado: {ext}"}), 415

    audio_file.seek(0, 2)
    size = audio_file.tell()
    audio_file.seek(0)
    if size > AUDIO_MAX_BYTES:
        return jsonify({"error": "Archivo demasiado grande."}), 413

    # --- Transcripción ---
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            audio_file.save(tmp_path)

        t0 = time.time()
        texto = transcribe(tmp_path)
        dur_whisper = time.time() - t0
        print(f"[Whisper] '{texto}' ({dur_whisper:.2f}s)")

    except Exception as e:
        return jsonify({"error": f"Error en transcripción: {str(e)}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    # --- Generación LLM ---
    try:
        t1 = time.time()
        raw = generate(_build_prompt(SYSTEM_PROMPT, texto))
        dur_gemma = time.time() - t1
        block = extract_first_block(raw)
        respuesta = handle(block)
        print(f"[Gemma] '{respuesta}' ({dur_gemma:.2f}s)")
    except Exception as e:
        return jsonify({"error": f"Error en LLM: {str(e)}"}), 500

    save_event(texto, respuesta, dur_whisper, dur_gemma)

    return jsonify({"transcripcion": texto, "respuesta": respuesta})
