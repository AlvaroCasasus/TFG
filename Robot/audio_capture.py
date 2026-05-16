#!/usr/bin/env python
# -*- coding: utf-8 -*-
# audio_capture.py
# pip install webrtcvad sounddevice scipy
from __future__ import print_function

import wave
import tempfile
import sounddevice as sd
import webrtcvad
import signal

_stop = False

def _handle_signal(sig, frame):
    global _stop
    _stop = True

signal.signal(signal.SIGINT, _handle_signal)

SAMPLE_RATE       = 16000
FRAME_MS          = 30
FRAME_SAMPLES     = int(SAMPLE_RATE * FRAME_MS / 1000)
SILENCE_TIMEOUT   = 2.5
AGGRESSIVENESS    = 3
MICROPHONE_DEVICE = None
MAX_RECORD_SECONDS = 5  # maximo de grabacion tras detectar voz

def record_until_silence():
    vad = webrtcvad.Vad(AGGRESSIVENESS)

    print("[Mic] Escuchando...")

    frames_with_voice = []
    silent_frames     = 0
    speaking          = False
    max_silent_frames = int(SILENCE_TIMEOUT * 1000 / FRAME_MS)
    max_voice_frames  = int(MAX_RECORD_SECONDS * 1000 / FRAME_MS)

    with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1,
                           dtype="int16", blocksize=FRAME_SAMPLES,
                           device=MICROPHONE_DEVICE) as stream:
        while True:
            frame, _ = stream.read(FRAME_SAMPLES)
            is_speech = vad.is_speech(bytes(bytearray(frame)), SAMPLE_RATE)
	    #print("[Mic] is_speech: {}".format(is_speech))  # ← temporal

            if is_speech:
                if not speaking:
                    print("[Mic] Voz detectada, grabando...")
                speaking      = True
                silent_frames = 0
                frames_with_voice.append(bytes(bytearray(frame)))

            elif speaking:
                frames_with_voice.append(bytes(bytearray(frame)))
                silent_frames += 1
                if silent_frames >= max_silent_frames:
                    print("[Mic] Silencio detectado, fin de grabacion.")
                    break

            # Corte por duracion maxima
            #if speaking and len(frames_with_voice) >= max_voice_frames:
            #    print("[Mic] Duracion maxima alcanzada ({}s).".format(MAX_RECORD_SECONDS))
             #   break

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    wf = wave.open(tmp_path, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b"".join(frames_with_voice))
    wf.close()  # ← cierre explícito en vez de with

    return tmp_path
