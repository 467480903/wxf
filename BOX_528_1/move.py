from robot_controller import RobotController
import math

robot = RobotController()

# 导航到地图第0个点
robot.go(15)
robot.go_adjusted(32)