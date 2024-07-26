# key_verifier.py
import hashlib
import hmac
import base64
from datetime import datetime
from w6_1_key_generator import SECRET_KEY # 导入共享密钥

def verify_key(input_key, secret_key):
    current_date = datetime.utcnow().strftime('%Y-%m-%d')  # 获取当前UTC日期
    message = current_date.encode()
    key = secret_key.encode()
    hash = hmac.new(key, message, hashlib.sha256)
    generated_key = base64.urlsafe_b64encode(hash.digest()).decode()
    return generated_key == input_key

def main():
    user_input_key = input("请输入密钥：")
    if verify_key(user_input_key, SECRET_KEY):
        print("密钥有效，允许访问。")
    else:
        print("密钥无效，拒绝访问。")
        exit(1)

if __name__ == "__main__":
    main()

