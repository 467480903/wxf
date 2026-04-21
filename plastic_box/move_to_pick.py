from robot_controller import RobotController
import math
import time

robot = RobotController()


robot.go(0)

# 高精度导航
robot.go(0, high_precision=True)