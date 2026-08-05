import requests
import os
import sys
import datetime

USERNAME = os.environ.get('PA_USERNAME', '').strip()
API_TOKEN = os.environ.get('PA_API_TOKEN', '').strip()
DOMAIN = os.environ.get('PA_DOMAIN', '').strip()

print(f"[{datetime.datetime.now()}] PythonAnywhere 续期脚本启动")

if not USERNAME or not API_TOKEN or not DOMAIN:
    print("❌ 缺少环境变量！")
    sys.exit(1)

session = requests.Session()
session.headers.update({
    'Authorization': f'Token {API_TOKEN}',
    'Accept': 'application/json'
})

base_url = 'https://www.pythonanywhere.com/api/v1/user'

print(f"\n1. 验证 Token 有效性...")
try:
    resp = session.get(f'{base_url}/webapps/', timeout=30)
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        print("   ✅ Token 有效")
        print(f"   返回内容前200字符: {resp.text[:200]}")
    elif resp.status_code == 401:
        print("   ❌ Token 无效！请重新生成")
        sys.exit(1)
    else:
        print(f"   ❌ 验证失败: {resp.text[:300]}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n2. 查找域名 {DOMAIN}...")
try:
    resp = session.get(f'{base_url}/webapps/?domain={DOMAIN}', timeout=30)
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            webapp = data[0]
            print(f"   ✅ 找到: {webapp.get('domain')}")
            print(f"   状态: {webapp.get('status')}")
            print(f"   到期时间: {webapp.get('expiry', 'N/A')}")
        else:
            print("   ❌ 未找到该域名的 Web App")
            sys.exit(1)
    else:
        print(f"   ❌ 查询失败: {resp.text[:300]}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n3. 执行续期...")
try:
    resp = session.post(f'{base_url}/webapps/{DOMAIN}/renew/', timeout=30)
    print(f"   状态码: {resp.status_code}")
    print(f"   响应: {resp.text[:300]}")
    if resp.status_code == 200:
        print("\n✅ 续期成功！")
    elif resp.status_code == 400:
        print("\n⚠️ 可能已在有效期内，无需续期")
    else:
        print("\n❌ 续期失败")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)
