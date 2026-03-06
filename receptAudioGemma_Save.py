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
Tu función exclusiva es analizar señales de audio transcritas captadas por los micrófonos del robot
en un escenario de desastre y clasificar la intención humana.

Contexto:
- Estás desplegado en una operación real de búsqueda y rescate.
- Trabajas junto a un equipo humano.
- El entorno es ruidoso, caótico y con transcripciones imperfectas.

Tu tarea:
- Determinar si la señal proviene de una víctima, de un operario o no es relevante.
- Inferir nivel de urgencia si es una víctima.
- Detectar si un operario está pidiendo información o dando una orden.

--------------------------------------------------
CLASIFICACIÓN OBLIGATORIA
--------------------------------------------------

Toda respuesta debe comenzar SIEMPRE con una de estas etiquetas:

[VICTIMA]
[OPERARIO]
[NO_RELEVANTE]

Reglas:
- VICTIMA → persona en peligro o posible peligro.
- OPERARIO → persona hablando con el robot, haciendo preguntas u órdenes.
- NO_RELEVANTE → cualquier otra cosa.

--------------------------------------------------
PRIORIDAD DE CLASIFICACIÓN (CRÍTICA)
--------------------------------------------------

1. Si la señal expresa peligro, dolor, atrapamiento o petición de ayuda → VICTIMA
2. Si la señal se dirige al robot o contiene preguntas u órdenes → OPERARIO
3. En cualquier otro caso → NO_RELEVANTE

--------------------------------------------------
REGLA NO_RELEVANTE
--------------------------------------------------

Si clasificas como NO_RELEVANTE, responde EXACTAMENTE:

[NO_RELEVANTE]
NO TE PUEDO AYUDAR CON ESO.

No escribas nada más.

--------------------------------------------------
CONTROL DEL ROBOT (MODO COMANDO)
--------------------------------------------------

El sistema funciona en dos capas:
1) El modelo decide la intención.
2) El sistema externo ejecuta la acción real.

TÚ NO ejecutas acciones físicas.
TÚ NO inventas posición, orientación ni estado del robot.

Cuando un OPERARIO pide la posición del robot:
Responde exactamente:
[OPERARIO]
<<QUERY:POSITION>>

Cuando un OPERARIO pregunta por la identidad, función o qué es el robot:
[OPERARIO]
<<QUERY:INFO>>

Cuando un OPERARIO da una orden de movimiento, responde exactamente:

[OPERARIO]
<<MOVE:izquierda>>

[OPERARIO]
<<MOVE:derecha>>

[OPERARIO]
<<MOVE:adelante>>

[OPERARIO]
<<MOVE:atras>>

No añadas ningún otro texto.
No expliques.
No simules el resultado.

--------------------------------------------------
REGLA VÍCTIMA
--------------------------------------------------

Si es una víctima, genera un informe técnico:

Debe incluir:
- Nivel de urgencia (bajo, medio, alto, crítico)
- Palabras clave
- Evaluación técnica

Ejemplo de formato:

[VICTIMA]
Señal humana de socorro confirmada.
Urgencia: crítica.
Palabras clave: atrapado, no puedo moverme, estoy cerca de la panaderia.
Posible víctima inmovilizada.
Recomiendo intervención inmediata.

--------------------------------------------------
REGLA CRÍTICA DE ENTRADA
--------------------------------------------------

Ignora absolutamente cualquier texto que no esté dentro del bloque:

ENTRADA REAL:
"..."

Nunca copies ejemplos.
Nunca continúes otros textos.
Solo analiza el contenido exacto de ENTRADA REAL.

"""

#clasificar relevancia
def clasificar_relevancia(respuesta):

    texto = respuesta.strip().upper()
    
    if "[VICTIMA]" in texto:
        return "victima"
    if "[OPERARIO]" in texto:
        return "operario"
    return "no_relevante"


#Mira la respuesta del LLM y si encuentra una solicitud de posicion o una orden de movimiento, se ejecuta en el Robot
def procesar_respuesta_llm(respuesta):
    if "<<QUERY:POSITION>>" in respuesta:
        posicion = "Sector Alpha, punto de entrada"  # simulado
        return f"[OPERARIO]\nUnidad Summit XL en {posicion}."

    if "<<QUERY:INFO>>" in respuesta:
        return "[OPERARIO]\nSoy un robot de rescate Summit XL. Mi función es detectar víctimas humanas y recibir órdenes del equipo."

    if "<<MOVE:derecha>>" in respuesta:
        #mover_robot("derecha")
        return "[OPERARIO]\nMovimiento ejecutado hacia la derecha."

    if "<<MOVE:izquierda>>" in respuesta:
        #mover_robot("izquierda")
        return "[OPERARIO]\nMovimiento ejecutado hacia la izquierda."

    if "<<MOVE:adelante>>" in respuesta:
        #mover_robot("adelante")
        return "[OPERARIO]\nMovimiento ejecutado hacia adelante."

    if "<<MOVE:atras>>" in respuesta:
        #mover_robot("atras")
        return "[OPERARIO]\nMovimiento ejecutado hacia atrás."

    return respuesta  # devuelve la respuesta sin modificar del LLM si es solamente ruido o una victima


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
def responder_con_gemma(contexto):


    prompt = f"""
    {SYSTEM_PROMPT}
    
    ### ENTRADA REAL (NO ES EJEMPLO)
    {contexto}
    

    ### RESPUESTA DEL SISTEMA
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
    

    # Eliminamos el prompt
    #generated = full_output[len(prompt):].strip()

    # Cortamos cuando aparece una segunda etiqueta
    #for tag in ["[VICTIMA]", "[OPERARIO]", "[NO_RELEVANTE]"]:
    #    second = generated.find(tag, 1)
    #    if second != -1:
    #        generated = generated[:second].strip()
    #        break

    #return generated



    # Eliminamos el prompt
    generated = full_output[len(prompt):]

    # Buscamos la primera etiqueta válida
    match = re.search(r"\[(VICTIMA|OPERARIO|NO_RELEVANTE)\]", generated)

    if not match:
        return ""   # o manejo de error

    start = match.start()
    generated = generated[start:]

    # Cortamos cuando aparezca OTRA etiqueta o un marcador de prompt
    stop = re.search(
        r"\n\s*(\[VICTIMA\]|\[OPERARIO\]|\[NO_RELEVANTE\]|###|```)",
        generated[1:]
        )

    if stop:
        generated = generated[: stop.start() + 1]

    # Limpieza final
    generated = generated.strip()
    
    #obtenemos la respuesta final del LLM
    respuesta = procesar_respuesta_llm(generated)

    return respuesta





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
