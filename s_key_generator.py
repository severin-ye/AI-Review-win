from w6_1_key_generator import generate_key, SECRET_KEY


if __name__ == "__main__":
    generated_key = generate_key(SECRET_KEY)
    print(f"生成的密钥: {generated_key}")
    input("按任意键退出...")