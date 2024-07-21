import hashlib
import json

# 유저네임과 비밀번호
username = "kmu9842"
password = "kwon0625_"

# SHA-512 해시 생성
hashed_username = hashlib.sha512(username.encode()).hexdigest()
hashed_password = hashlib.sha512(password.encode()).hexdigest()

# 해시된 데이터 저장
config_data = {
    "USERNAME": hashed_username,
    "PASSWORD": hashed_password
}

with open('user.json', 'w') as config_file:
    json.dump(config_data, config_file)

print("해시된 유저네임과 비밀번호가 저장되었습니다.")