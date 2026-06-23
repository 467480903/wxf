from turtle import distance
from robot_controller import RobotController
import math

robot = RobotController()

# 导航到地图第0个点
robot.move_forward(dist_m=2.0, speed=1.0)