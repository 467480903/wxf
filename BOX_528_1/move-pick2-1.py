from robot_controller import RobotController
import math

robot = RobotController()

# 导航到地图第0个点
robot.go(0)

robot.go(1)
robot.crab_walk(0.5)
# 高精度导航
# robot.go(5, high_precision=True)
