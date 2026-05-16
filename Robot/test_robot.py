#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
from geometry_msgs.msg import Twist

rospy.init_node("test_move")
pub = rospy.Publisher("/robot/robotnik_base_control/cmd_vel", Twist, queue_size=10)
rospy.sleep(1)

msg = Twist()
msg.linear.x = -0.05

rate = rospy.Rate(10)  # 10Hz
print("Publicando... Ctrl+C para parar")

while not rospy.is_shutdown():
    pub.publish(msg)
    rate.sleep()
