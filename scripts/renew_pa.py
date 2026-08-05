import requests
import os
import sys
import datetime

USERNAME = os.environ.get('PA_USERNAME', '')
API_TOKEN = os.environ.get('PA_API_TOKEN', '')
DOMAIN = os.environ.get('PA_DOMAIN', '')

if not USERNAME or not API_TOKEN or not DOMAIN:
    print("缺少必要环境变量: PA_USERNAME, PA_API_TOKEN, PA_DOMAIN")
    sys.exit(1)

url = f'https://www.pythonanywhere.com/api/v1/user/webapps/{DOMAIN}/renew/'
headers = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

print(f"[{datetime.datetime.now()}] 正在续期 PythonAnywhere 免费版...")
print(f"  用户名: {USERNAME}")
print(f"  域名: {DOMAIN}")

try:
    resp = requests.post(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        print("✅ 续期成功！免费版已延长3个月。")
    elif resp.status_code == 400:
        print(f"⚠️ 请求被拒绝: {resp.text}")
    else:
        print(f"❌ 续期失败，状态码: {resp.status_code}")
        print(f"  响应: {resp.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ 请求异常: {e}")
    sys.exit(1)
