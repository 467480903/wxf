from robot_controller import RobotController
import math

robot = RobotController()

# 使用导航点索引进行导航（整数索引）
robot.go(19)
robot.go(20)
robot.go(21)
robot.go(22)
robot.go_adjusted(23)
robot.go_adjusted(25)