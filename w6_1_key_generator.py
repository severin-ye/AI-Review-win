# key_generator.py
import hashlib
import hmac
import base64
from datetime import datetime

SECRET_KEY = f"severin的第一个编程项目, 使用openai的api审校文档, 今天是{datetime.utcnow().strftime('%Y-%m-%d')}"  # 共享密钥

def generate_key(secret_key):
    current_date = datetime.utcnow().strftime('%Y-%m-%d')  # 获取当前UTC日期
    message = current_date.encode()  # 将日期编码为字节
    key = secret_key.encode()  # 将共享密钥编码为字节
    hash = hmac.new(key, message, hashlib.sha256)  # 使用HMAC-SHA256算法生成哈希
    return base64.urlsafe_b64encode(hash.digest()).decode()  # 返回URL安全的Base64编码密钥

if __name__ == "__main__":
    generated_key = generate_key(SECRET_KEY)
    print(f"生成的密钥: {generated_key}")
