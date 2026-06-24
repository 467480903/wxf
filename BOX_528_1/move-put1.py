from robot_controller import RobotController
import math

robot = RobotController()

# 使用导航点索引进行导航（整数索引）
robot.go(7)
robot.go(8)
robot.go(9)
robot.go(10)
robot.go_adjusted(11)

# 高精度导航
robot.go_adjusted(12)