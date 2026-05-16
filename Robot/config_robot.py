#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ─────────────────────────────────────────
# MODO DE EJECUCIÓN
# Cambia a False cuando estés en el robot real
# ─────────────────────────────────────────
SIMULATION_MODE = False

# ─────────────────────────────────────────
# Servidor
# ─────────────────────────────────────────
SERVER_URL     = "http://150.244.56.149:8888"
POLL_INTERVAL  = 5
MAX_BACKOFF    = 60

# ─────────────────────────────────────────
# ROS
# ─────────────────────────────────────────
CMD_VEL_TOPIC  = "/robot/cmd_vel"
ODOM_TOPIC     = "/robot/robotnik_base_control/odom"
LINEAR_SPEED   = 0.1
ANGULAR_SPEED  = 0.3
MOVE_DURATION  = 1.5

# ─────────────────────────────────────────
# Audio
# ─────────────────────────────────────────
AUDIO_SAVE_DIR      = "received_audio"
BLUETOOTH_SINK_NAME = "bluez_sink.70_21_7D_4D_4A_DF.a2dp_sink"

# ─────────────────────────────────────────
# Posición simulada (solo si SIMULATION_MODE = True)
# ─────────────────────────────────────────
SIMULATED_POSITION = {
    "x": 1.5,
    "y": 3.2
}
