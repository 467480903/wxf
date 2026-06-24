from robot_controller import RobotController
import math

robot = RobotController()

# 导航到地图第0个点
robot.go_adjusted(23)

# 高精度导航
robot.go_adjusted(25)