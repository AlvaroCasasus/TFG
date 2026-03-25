#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
API Flask para controlar Robotnik Summit XL-HL.
Compatible con ROS 1 y Python 2.7.

Endpoints:
  POST /robot/audio/play    - Recibir audio del servidor y reproducirlo
  POST /robot/audio/capture - Grabar audio del micrófono y enviarlo al servidor
  POST /robot/move          - Ejecutar movimiento
  GET  /robot/position      - Obtener posición actual
  POST /robot/stop          - Detener el robot
"""

from __future__ import print_function

import math
import os
import base64
import tempfile
import subprocess
import collections

import rospy
import tf.transformations as tft
from flask import Flask, request, jsonify
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

import requests as http_requests  # para reenviar audio al servidor


# ================================================================
# Compatibilidad subprocess.run en Python 2.7
# ================================================================
if not hasattr(subprocess, 'run'):
    def _subprocess_run(cmd, capture_output=False, text=False, timeout=None):
        stdout_pipe = subprocess.PIPE if capture_output else None
        stderr_pipe = subprocess.PIPE if capture_output else None
        proc = subprocess.Popen(cmd, stdout=stdout_pipe, stderr=stderr_pipe)
        try:
            out, err = proc.communicate(timeout=timeout)
        except TypeError:
            out, err = proc.communicate()
        if text:
            if out is not None:
                out = out.decode('utf-8', 'ignore')
            if err is not None:
                err = err.decode('utf-8', 'ignore')
        CP = collections.namedtuple('CompletedProcess', ['returncode', 'stdout', 'stderr'])
        return CP(proc.returncode, out, err)
    subprocess.run = _subprocess_run


# ================================================================
# Configuración — ajusta según tu entorno
# ================================================================
SERVER_IP       = "150.244.56.149"   # IP del servidor con Whisper + Gemma
SERVER_PORT     = 8888
SERVER_ENDPOINT = "/upload"        # endpoint del servidor que recibe el audio

DEFAULT_V_LIN   = 0.3              # m/s
DEFAULT_V_ANG   = 0.7              # rad/s
DEFAULT_DURATION = 2.0             # segundos por comando de movimiento
AUDIO_SAMPLE_RATE = 48000
AUDIO_DURATION    = 5              # segundos de grabación por defecto


# ================================================================
# Controlador del robot
# ================================================================
class RobotController(object):

    def __init__(self):
        rospy.init_node("summit_flask_api", anonymous=True)
        self.pub_cmd = rospy.Publisher("/robot/cmd_vel", Twist, queue_size=10)
        self.is_moving = False
        self._last_odom = None
        rospy.Subscriber("/odom", Odometry, self._odom_callback)
        rospy.loginfo("RobotController iniciado.")

    def _odom_callback(self, msg):
        self._last_odom = msg

    # ――― movimiento ―――
    def _publish_for(self, lin_x, ang_z, duration):
        self.is_moving = True
        twist = Twist()
        twist.linear.x  = lin_x
        twist.angular.z = ang_z
        rate = rospy.Rate(10)
        end  = rospy.Time.now() + rospy.Duration(duration)
        while rospy.Time.now() < end and not rospy.is_shutdown():
            self.pub_cmd.publish(twist)
            rate.sleep()
        self.stop()

    def stop(self):
        self.pub_cmd.publish(Twist())
        self.is_moving = False

    def move(self, direction, velocity=None, angular_velocity=None, duration=None):
        """
        Mueve el robot según la dirección indicada.
        direction: 'adelante' | 'atras' | 'derecha' | 'izquierda'
        """
        v = velocity         if velocity         is not None else DEFAULT_V_LIN
        w = angular_velocity if angular_velocity is not None else DEFAULT_V_ANG
        d = duration         if duration         is not None else DEFAULT_DURATION

        moves = {
            "adelante":   ( v,  0.0),
            "atras":      (-v,  0.0),
            "derecha":    (0.0, -w),
            "izquierda":  (0.0,  w),
        }

        if direction not in moves:
            return False, "Dirección no válida: {}".format(direction)

        lin, ang = moves[direction]
        self._publish_for(lin, ang, d)
        return True, "Movimiento '{}' ejecutado.".format(direction)

    # ――― posición ―――
    def get_position(self):
        """Devuelve la posición actual desde odometría."""
        if self._last_odom is None:
            return None

        pos = self._last_odom.pose.pose.position
        ori = self._last_odom.pose.pose.orientation

        # Convertir quaternion a yaw
        q = [ori.x, ori.y, ori.z, ori.w]
        _, _, yaw = tft.euler_from_quaternion(q)
        yaw_deg   = round(math.degrees(yaw), 1)

        return {
            "x":       round(pos.x, 2),
            "y":       round(pos.y, 2),
            "z":       round(pos.z, 2),
            "yaw_deg": yaw_deg
        }


# ================================================================
# Flask
# ================================================================
app    = Flask(__name__)
robot  = None


def get_robot():
    global robot
    if robot is None:
        robot = RobotController()
    return robot


# ================================================================
# ENDPOINT 1 — Recibir audio del servidor y reproducirlo
# ================================================================
@app.route('/robot/audio/play', methods=['POST'])
def play_audio():
    """
    Recibe un fichero de audio WAV del servidor y lo reproduce.

    Espera multipart/form-data con campo 'audio',
    o JSON con campo 'audio_data' en base64.
    """
    temp_path = None
    try:
        # — Modo A: multipart (fichero directo) —
        if 'audio' in request.files:
            audio_file = request.files['audio']
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_path = tmp.name
                audio_file.save(temp_path)

        # — Modo B: JSON con base64 —
        elif request.is_json:
            data = request.get_json()
            audio_b64 = data.get('audio_data')
            if not audio_b64:
                return jsonify({'error': 'Falta audio_data en JSON'}), 400
            audio_bytes = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_path = tmp.name
                tmp.write(audio_bytes)
        else:
            return jsonify({'error': 'Se requiere multipart/form-data o JSON con audio_data'}), 400

        # Reproducir con aplay
        #result = subprocess.run(['aplay', temp_path], capture_output=True, text=True)
        result = subprocess.run(
        ['aplay', '-f', 'S16_LE', '-r', '48000', '-c', '1', temp_path],
        capture_output=True, text=True
        )

        if result.returncode != 0:
            return jsonify({
                'error': 'Error reproduciendo audio: {}'.format(result.stderr)
            }), 500

        rospy.loginfo("Audio reproducido correctamente.")
        return jsonify({'status': 'success', 'message': 'Audio reproducido.'})

    except Exception as e:
        rospy.logerr("play_audio error: {}".format(e))
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ================================================================
# ENDPOINT 2 — Grabar audio y enviarlo al servidor
# ================================================================
@app.route('/robot/audio/capture', methods=['POST'])
def capture_and_send():
    """
    Graba audio del micrófono del robot y lo envía al servidor.

    Parámetros JSON opcionales:
      - duration:     segundos de grabación (default: 5)
      - sample_rate:  Hz (default: 16000)
    """
    temp_path = None
    try:
        data        = request.get_json() or {}
        duration    = data.get('duration',    AUDIO_DURATION)
        sample_rate = data.get('sample_rate', AUDIO_SAMPLE_RATE)

        # Grabar con arecord
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            temp_path = tmp.name

        cmd = [
            'arecord',
            '-f', 'S16_LE',
            '-c', '1',
            '-r', str(sample_rate),
            '-t', 'wav',
            '-d', str(duration),
            temp_path
        ]

        rospy.loginfo("Grabando {} segundos...".format(duration))
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({'error': 'Error grabando: {}'.format(result.stderr)}), 500

        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            return jsonify({'error': 'Archivo de audio vacío tras grabación.'}), 500

        # Enviar al servidor
        server_url = "http://{}:{}{}".format(SERVER_IP, SERVER_PORT, SERVER_ENDPOINT)
        rospy.loginfo("Enviando audio a {}".format(server_url))

        with open(temp_path, 'rb') as f:
            response = http_requests.post(
                server_url,
                files={'audio': ('recording.wav', f, 'audio/wav')},
                timeout=30  # Whisper puede tardar
            )

        if response.status_code != 200:
            return jsonify({
                'error': 'El servidor respondió con {}'.format(response.status_code)
            }), 502

        server_data = response.json()
        rospy.loginfo("Respuesta servidor: {}".format(server_data))

        return jsonify({
            'status':        'success',
            'transcripcion': server_data.get('transcripcion', ''),
            'respuesta':     server_data.get('respuesta', '')
        })

    except http_requests.exceptions.ConnectionError:
        return jsonify({'error': 'No se pudo conectar al servidor.'}), 503
    except http_requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout esperando respuesta del servidor.'}), 504
    except Exception as e:
        rospy.logerr("capture_and_send error: {}".format(e))
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ================================================================
# ENDPOINT 3 — Ejecutar movimiento
# ================================================================
@app.route('/robot/move', methods=['POST'])
def move_robot():
    """
    Mueve el robot.

    Parámetros JSON:
      - direction:        'adelante' | 'atras' | 'derecha' | 'izquierda'  (requerido)
      - velocity:         m/s   (opcional, default: 0.3)
      - angular_velocity: rad/s (opcional, default: 0.7)
      - duration:         s     (opcional, default: 2.0)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Se requiere JSON con direction.'}), 400

        direction = data.get('direction')
        if not direction:
            return jsonify({'error': 'Falta el campo direction.'}), 400

        ok, msg = get_robot().move(
            direction        = direction,
            velocity         = data.get('velocity'),
            angular_velocity = data.get('angular_velocity'),
            duration         = data.get('duration')
        )

        if not ok:
            return jsonify({'error': msg}), 400

        return jsonify({'status': 'success', 'message': msg})

    except Exception as e:
        rospy.logerr("move_robot error: {}".format(e))
        return jsonify({'error': str(e)}), 500


# ================================================================
# ENDPOINT 4 — Obtener posición
# ================================================================
@app.route('/robot/position', methods=['GET'])
def get_position():
    """
    Devuelve la posición actual del robot desde odometría.

    Respuesta:
      { "x": float, "y": float, "z": float, "yaw_deg": float }
    """
    try:
        pos = get_robot().get_position()

        if pos is None:
            return jsonify({
                'error': 'Odometría no disponible aún. ¿Está /odom publicando?'
            }), 503

        return jsonify({'status': 'success', 'position': pos})

    except Exception as e:
        rospy.logerr("get_position error: {}".format(e))
        return jsonify({'error': str(e)}), 500


# ================================================================
# ENDPOINT 5 — Parada de emergencia
# ================================================================
@app.route('/robot/stop', methods=['POST'])
def stop_robot():
    """Detiene el robot inmediatamente."""
    try:
        get_robot().stop()
        return jsonify({'status': 'success', 'message': 'Robot detenido.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ================================================================
# ENDPOINT 6 — Estado robot
# ================================================================
@app.route('/robot/status', methods=['GET'])
def robot_status():
    """Verifica que el robot está operativo."""
    try:
        return jsonify({
            'status': 'online',
            'is_moving': get_robot().is_moving,
            'odom_available': get_robot()._last_odom is not None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ================================================================
# Main
# ================================================================
if __name__ == '__main__':
    print("Iniciando API del robot Summit XL...")
    print("  POST /robot/audio/play    - Reproducir audio recibido del servidor")
    print("  POST /robot/audio/capture - Grabar y enviar audio al servidor")
    print("  POST /robot/move          - Mover el robot")
    print("  GET  /robot/position      - Posición actual")
    print("  POST /robot/stop          - Parada de emergencia")
    get_robot()
    app.run(host='0.0.0.0', port=5000, debug=False)
