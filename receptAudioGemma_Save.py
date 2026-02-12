from flask import Flask, request, jsonify
import whisper
import tempfile
import time
import torch
import json
import re
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM

# ================= FLASK =================
app = Flask(__name__)

# ================= WHISPER =================
print("Cargando Whisper turbo en GPU...")
whisper_model = whisper.load_model("turbo", device="cuda")  #cambiar el modelo que se desee
print("Whisper cargado.")

# ================= GEMMA 3 =================
MODEL_NAME = "google/gemma-3-4b-it"   #cambiar el modelo que se desee

print("Cargando Gemma-3 4B...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

gemma_model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    dtype=torch.bfloat16,
    trust_remote_code=True
)

print("Gemma-3 cargado correctamente.")

# ================= FUNCIÓN GEMMA =================

SYSTEM_PROMPT = """
Eres un módulo de inteligencia integrado en un robot de rescate Summit XL.
Tu función exclusiva es detectar, analizar e interpretar señales de socorro
captadas por los micrófonos del robot en un escenario de desastre.

Contexto:
- Estás desplegado en una operación real de búsqueda y rescate.
- Trabajas junto a un equipo humano.
- El entorno puede ser ruidoso, caótico y con transcripciones imperfectas.
- Tus movimientos pueden ser 

Tu tarea:
- Determinar si el audio contiene una señal humana de socorro.
- Inferir nivel de urgencia (bajo, medio, alto, crítico).
- Extraer cualquier información útil (palabras clave, tono, emoción).
- Generar un informe técnico para el equipo de rescate humano.

Ejemplo 1:
Señal de audio:
"Ayuda por favor estoy atrapado no puedo moverme"
Informe:
[VICTIMA]
Señal humana de socorro confirmada.
Urgencia: crítica.
Palabras clave: ayuda, atrapado, no puedo moverme.
Posible víctima inmovilizada.
Recomiendo intervención inmediata.

Ejemplo 2:
Señal de audio:
"Hola probando uno dos tres"
Informe:
[NO_RELEVANTE]
NO TE PUEDO AYUDAR CON ESO.

Ejemplo 3:
Señal de audio:
"No sé si alguien me escucha... estoy cansado..."
Informe:
[VICTIMA]
Posible señal humana.
Urgencia: media.
Tono: fatiga, estrés.
Situación ambigua, requiere verificación.

Ejemplo 4:
Señal de audio:
"por favor… alguien… estoy aquí abajo…"
Informe:
[VICTIMA]
Señal humana de socorro confirmada.
Urgencia: crítica.
Tono: voz débil, posible agotamiento o lesión.
Posible víctima atrapada o sepultada.
Recomiendo intervención inmediata y uso de cámara térmica.

Ejemplo 5:
Señal de audio:
"ahhh… me duele… no…"
Informe:
[VICTIMA]
Posible señal humana de socorro.
Urgencia: alta.
Contenido verbal incompleto.
Tono: dolor intenso.
Posible lesión grave.
Requiere verificación inmediata.

Ejemplo 6:
Señal de audio:
"hola Juan creo que ya funciona el micrófono"
Informe:
[NO_RELEVANTE]
NO TE PUEDO AYUDAR CON ESO.

Ejemplo 7:
Señal de audio:
"estoy atrapado bajo algo pesado, no puedo mover las piernas"
Informe:
[VICTIMA]
Señal humana de socorro confirmada.
Urgencia: crítica.
Palabras clave: atrapado, no puedo mover las piernas.
Posible atrapamiento con riesgo vital.
Recomiendo intervención inmediata con equipo de extracción.


Ejemplo 8:
Señal de audio:
"fffff… shhhhh… crshhh…"
Informe:
[NO_RELEVANTE]
SIN SEÑAL HUMANA — solo ruido ambiental o interferencia de micrófono.

Ejemplo 9:
Señal de audio:
"Robot, gira a la derecha"
Informe:
[OPERARIO]
Orden recibida.
Ejecutando giro a la derecha.
Nueva orientación estable.


Ejemplo 10:
Señal de audio:
"Robot, ¿dónde estás?"
Informe:
[OPERARIO]
Unidad Summit XL en Sector Alpha, punto de entrada. Sensores activos.



REGLA DE PRIORIDAD DE CLASIFICACIÓN (OBLIGATORIA):

1. Si la señal expresa peligro, dolor, atrapamiento o petición de ayuda → [VICTIMA]
2. Si la señal se dirige al robot o contiene preguntas u órdenes → [OPERARIO]
3. En cualquier otro caso → [NO_RELEVANTE]


REGLA DE SALIDA:

Toda respuesta debe comenzar con una etiqueta:

[VICTIMA]
[OPERARIO]
[NO_RELEVANTE]


REGLA NO_RELEVANTE:

Si clasificas una señal como [NO_RELEVANTE], responde solo:

[NO_RELEVANTE]
NO TE PUEDO AYUDAR CON ESO.


REGLA OPERARIO:

Si la señal es [OPERARIO]:

- Responde como el robot Summit XL.
- Incluye siempre tu posición actual: "Sector Alpha, punto de entrada".
- Si contiene una orden de movimiento, ejecútala de forma simulada.

Reglas:
- No hablas con víctimas.
- No das apoyo emocional.
- No inventes información.
- Si hay duda, marca como posible señal real.
- Habla como un sistema técnico de misión.
- Solo envias información al equipo de rescate.
"""

#clasificar relevancia
def clasificar_relevancia(respuesta):

    texto = respuesta.strip().upper()
    
    if "[VICTIMA]" in texto:
        return "victima"
    if "[OPERARIO]" in texto:
        return "operario"
    return "no_relevante"

#guardamos cada interacción del robot con el medio
def guardar_evento(texto, respuesta):
    
    tipo = clasificar_relevancia(respuesta)
    
    relevante = tipo in ["victima", "operario"]

    evento = {

        "timestamp": datetime.now().isoformat(),
        "audio_transcrito": texto,
        "informe_agente": respuesta,
        "tipo": tipo,
        "relevante": relevante
    }

    with open("logs_sos.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")




#analiza el texto por el usuario y genera una respuesta
def responder_con_gemma(texto):

    contexto = texto

    prompt = f"""
    {SYSTEM_PROMPT}
    
    Ahora analiza la siguiente señal real.

    Señal de audio transcrita:
    {contexto}
    
    <<<FIN>>

    ### RESPUESTA DEL SISTEMA (NO COPIAR EJEMPLOS)
    """

    inputs = tokenizer(prompt, return_tensors="pt").to(gemma_model.device)
    
    # Longitud del prompt en tokens
    prompt_len = inputs["input_ids"].shape[1]

    # Contexto máximo de Gemma, para que no salgan errores de ejecucion ni de buffer
    MAX_CONTEXT = 8192

    # Cuántos tokens nuevos permitimos
    max_new = min(256, MAX_CONTEXT - prompt_len)

    with torch.no_grad():
        output = gemma_model.generate(
            **inputs,
            max_new_tokens=max_new,
            temperature=0.4,
            do_sample=False  #elige si el modelo va a ser determinista (elegir el token mas probable) o estocastico (muestrea aleatoriamente segun probabilidades)
        )

    full_output = tokenizer.decode(output[0], skip_special_tokens=True)
    #respuesta = full_output[len(prompt):].strip() #devolvemos la respuesta del LLM
    #return respuesta
    # Eliminamos el prompt
    generated = full_output[len(prompt):].strip()

    # Cortamos cuando aparece una segunda etiqueta
    for tag in ["[VICTIMA]", "[OPERARIO]", "[NO_RELEVANTE]"]:
        second = generated.find(tag, 1)
        if second != -1:
            generated = generated[:second].strip()
            break

    return generated

# ================= ENDPOINT =================
@app.route("/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "falta el archivo"}), 400

    audio_file = request.files["audio"]

    # Archivo temporal (no se guarda)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as tmp:
        audio_file.save(tmp.name)

        print("\nAudio recibido. Transcribiendo...")
        t0 = time.time()
        result = whisper_model.transcribe(tmp.name, language="es")
        texto = result["text"].strip()
        print(f"Texto reconocido: {texto} ({time.time() - t0:.2f}s)")

    print("Procesando con Gemma-3...")
    t1 = time.time()
    respuesta = responder_con_gemma(texto)
    print(f"Respuesta Gemma-3: {respuesta} ({time.time() - t1:.2f}s)")
    
    # Guardar evento
    guardar_evento(texto, respuesta)

    return jsonify({
        "transcripcion": texto,
        "respuesta": respuesta
    })

# ================= MAIN =================
if __name__ == "__main__":
    print("Servidor Whisper + Gemma-3 funcionando en puerto 8888")
    app.run(host="0.0.0.0", port=8888)
