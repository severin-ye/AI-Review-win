import datetime
import time
import sys
import os

# 试用期检查
def check_date():
    # 检查是否已通过密钥验证
    if os.environ.get('AI_REVIEW_VERIFIED') == 'TRUE':
        return True
        
    deadline = datetime.datetime(2034, 3, 1, 0, 0, 0)  # 截止时间
    # 获取当前时间
    current_time = datetime.datetime.now()
    
    # 检查当前时间是否超过截止时间
    if current_time >= deadline:
        print("试用期已过，请联系管理员")
        time.sleep(5)
        sys.exit() # 终止整个程序
    else:
        return True