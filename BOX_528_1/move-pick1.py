from robot_controller import RobotController
import math

robot = RobotController()

# 使用导航点索引进行导航（整数索引）
# robot.go(1)
robot.go_adjusted(2)
robot.go(3)