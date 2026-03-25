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
from tts.speaker import text_to_audio
import base64
from flask import current_app
from tts.speaker import text_to_audio

audio_bp = Blueprint("audio", __name__)

def _build_prompt(system_prompt: str, user_input: str) -> str:
    return f"{system_prompt}\n\n### ENTRADA REAL (NO ES EJEMPLO)\n{user_input}\n\n### RESPUESTA DEL SISTEMA\n"

with open("prompts/system_prompt.txt", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


#@audio_bp.route("/pending", methods=["GET"])
#def pending_response():
#    pending = current_app.config["PENDING"]
#    if pending.empty():
#       return jsonify({"pending": False})
#
#    item = pending.get()
#   return jsonify({
#       "pending": True,
#       "action":  item.get("action"),   # ej: "MOVE:adelante" o None
#        "audio":   item.get("audio")     # audio en base64 o None
#    })


@audio_bp.route("/pending", methods=["POST"])      # ← POST
def pending_response():
    # Guardar posición si viene en el body
    body = request.get_json(silent=True) or {}
    position = body.get("position")
    if position:
        current_app.config["ROBOT_POSITION"] = position  # ← guarda en app config

    pending = current_app.config["PENDING"]
    if pending.empty():
        return jsonify({"pending": False})
    item = pending.get()
    return jsonify({
        "pending": True,
        "action":  item.get("action"),
        "audio":   item.get("audio")
    })



@audio_bp.route("/upload", methods=["POST"])
def upload_audio():

    # Solo para pruebas — ver la IP del robot
    print(f"[DEBUG] Petición recibida desde: {request.remote_addr}")

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
        position = current_app.config.get("ROBOT_POSITION")
        respuesta = handle(block, robot_position=position)
        print(f"[Gemma] '{respuesta}' ({dur_gemma:.2f}s)")
    except Exception as e:
        return jsonify({"error": f"Error en LLM: {str(e)}"}), 500

# --- Detectar si hay acción de movimiento ---
    accion = None
    for cmd in ["adelante", "atras", "derecha", "izquierda"]:
        if "MOVE:{}".format(cmd) in block:
            accion = "MOVE:{}".format(cmd)
            break
    if "QUERY:POSITION" in block:
        accion = "QUERY:POSITION"

    # --- Generar audio de respuesta ---
    audio_b64 = None
    audio_path = None
    try:
        audio_path = text_to_audio(respuesta)
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

# --- Meter en cola para que el robot lo recoja ---
    current_app.config["PENDING"].put({
        "action": accion,
        "audio":  audio_b64
    })

    save_event(texto, respuesta, dur_whisper, dur_gemma)
    return jsonify({"transcripcion": texto, "respuesta": respuesta})

