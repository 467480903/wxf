from robot_controller import RobotController
import math

robot = RobotController()

# 导航到地图第0个点
robot.go(0)
robot.go(5)

robot.go(1)
robot.go(2)

robot.go(4)
robot.go(3)


# 高精度导航
# robot.go(8, high_precision=True)