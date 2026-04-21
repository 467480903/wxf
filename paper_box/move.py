from robot_controller import RobotController
import math

robot = RobotController()

# 导航到地图第0个点
robot.go(0)

# 高精度导航
# robot.go(8, high_precision=True)