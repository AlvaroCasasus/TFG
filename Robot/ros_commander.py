# -*- coding: utf-8 -*-
"""
ros_commander.py
Controla el movimiento del robot y lee su posición vía ROS 1.
Solo se importa cuando SIMULATION_MODE = False.
"""

import time
import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from config_robot import CMD_VEL_TOPIC, ODOM_TOPIC, LINEAR_SPEED, ANGULAR_SPEED, MOVE_DURATION

_pub = None


def init_ros():
    global _pub
    rospy.init_node("summit_xl_client", anonymous=True)
    _pub = rospy.Publisher(CMD_VEL_TOPIC, Twist, queue_size=10)
    rospy.sleep(0.5)
    print("[ROS] Nodo iniciado.")
    print("[ROS] cmd_vel  → {}".format(CMD_VEL_TOPIC))
    print("[ROS] odom     → {}".format(ODOM_TOPIC))


# ── Movimiento ────────────────────────────────────────────

def _send_twist(linear_x=0.0, angular_z=0.0, duration=MOVE_DURATION):
    """Publica un Twist durante 'duration' segundos y luego para."""
    if _pub is None:
        raise RuntimeError("ROS no inicializado. Llama a init_ros() primero.")

    msg = Twist()
    msg.linear.x  = linear_x
    msg.angular.z = angular_z

    rate = rospy.Rate(10)
    end  = time.time() + duration
    while time.time() < end and not rospy.is_shutdown():
        _pub.publish(msg)
        rate.sleep()

    _pub.publish(Twist())   # para el robot


def execute_action(action):
    """
    Recibe un string como 'MOVE:adelante' y publica en /cmd_vel.
    Devuelve True si la acción fue reconocida y ejecutada.
    """
    if action is None:
        return False

    moves = {
        "MOVE:adelante":  lambda: _send_twist(linear_x=LINEAR_SPEED),
        "MOVE:atras":     lambda: _send_twist(linear_x=-LINEAR_SPEED),
        "MOVE:derecha":   lambda: _send_twist(angular_z=-ANGULAR_SPEED),
        "MOVE:izquierda": lambda: _send_twist(angular_z=ANGULAR_SPEED),
    }

    if action in moves:
        print("[ROS] Ejecutando: {}".format(action))
        moves[action]()
        print("[ROS] {} → OK".format(action))
        return True

    if action in ("QUERY:POSITION", "QUERY:INFO"):
        return True     # no requiere acción física

    print("[ROS] Acción desconocida: {}".format(action))
    return False


# ── Posición ─────────────────────────────────────────────

def get_position():
    """
    Lee la posición actual del robot desde el topic de odometría.
    Devuelve dict con x, y, sector o None si falla.
    """
    try:
        msg = rospy.wait_for_message(ODOM_TOPIC, Odometry, timeout=2.0)
        return {
            "x": round(msg.pose.pose.position.x, 2),
            "y": round(msg.pose.pose.position.y, 2)
        }
    except rospy.ROSException:
        print("[ROS] Timeout leyendo odometría.")
        return None
    except Exception as e:
        print("[ROS] Error leyendo posición: {}".format(e))
        return None
