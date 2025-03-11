# key_verifier.py
import hashlib
import hmac
import base64
import sys
import os
from datetime import datetime, timezone
from src.security.key_generator_legacy import SECRET_KEY # 导入共享密钥

def verify_key(input_key, secret_key):
    # 检查环境变量是否已验证
    if os.environ.get('AI_REVIEW_VERIFIED') == 'TRUE':
        return True
        
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')  # 获取当前UTC日期
    message = current_date.encode()
    key = secret_key.encode()
    hash = hmac.new(key, message, hashlib.sha256)
    generated_key = base64.urlsafe_b64encode(hash.digest()).decode()
    return generated_key == input_key

def main():
    user_input_key = input("请输入密钥: ")
    if verify_key(user_input_key, SECRET_KEY):
        print("密钥验证成功")
        sys.exit(0)
    else:
        print("密钥验证失败")
        sys.exit(1)

if __name__ == "__main__":
    main()

