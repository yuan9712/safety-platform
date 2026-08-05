import requests
import os
import sys
import re
import datetime

USERNAME = os.environ.get('PA_USERNAME', '').strip()
PASSWORD = os.environ.get('PA_PASSWORD', '').strip()
DOMAIN = os.environ.get('PA_DOMAIN', '').strip()

print(f"[{datetime.datetime.now()}] PythonAnywhere 续期脚本启动")

if not USERNAME or not PASSWORD or not DOMAIN:
    print("❌ 缺少环境变量！需要：PA_USERNAME, PA_PASSWORD, PA_DOMAIN")
    sys.exit(1)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

login_url = 'https://www.pythonanywhere.com/login/'

print(f"\n1. 获取登录页面...")
try:
    resp = session.get(login_url, timeout=30)
    print(f"   状态码: {resp.status_code}")
    
    csrf_match = re.search(r'name="csrfmiddlewaretoken"[^>]*value="([^"]+)"', resp.text)
    if not csrf_match:
        print("   ❌ 找不到 CSRF Token")
        sys.exit(1)
    csrf_token = csrf_match.group(1)
    print(f"   ✅ 获取 CSRF Token: {csrf_token[:8]}...")
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n2. 登录...")
try:
    login_data = {
        'auth-username': USERNAME,
        'auth-password': PASSWORD,
        'csrfmiddlewaretoken': csrf_token,
        'login_view-current_step': 'auth'
    }
    resp = session.post(login_url, data=login_data, timeout=30,
                       headers={'Referer': login_url})
    print(f"   状态码: {resp.status_code}")
    
    if 'logout' in resp.text.lower() or 'dashboard' in resp.text.lower() or '/user/' in resp.url:
        print("   ✅ 登录成功")
    elif resp.url != login_url:
        print(f"   ✅ 登录成功（跳转到: {resp.url}）")
    else:
        print("   ❌ 登录失败，请检查用户名和密码")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n3. 访问 Web 页面获取续期 CSRF Token...")
try:
    web_url = f'https://www.pythonanywhere.com/user/{USERNAME}/webapps/'
    resp = session.get(web_url, timeout=30)
    print(f"   状态码: {resp.status_code}")
    
    csrf_match = re.search(r'name="csrfmiddlewaretoken"[^>]*value="([^"]+)"', resp.text)
    if not csrf_match:
        print("   ❌ 找不到 CSRF Token")
        sys.exit(1)
    renew_csrf = csrf_match.group(1)
    print(f"   ✅ 获取续期 CSRF Token: {renew_csrf[:8]}...")
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n4. 执行续期...")
try:
    renew_url = f'https://www.pythonanywhere.com/user/{USERNAME}/webapps/{DOMAIN}/renew/'
    resp = session.post(renew_url, data={
        'csrfmiddlewaretoken': renew_csrf
    }, timeout=30, headers={'Referer': web_url})
    print(f"   状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        if 'error' in resp.text.lower():
            print("   ⚠️ 页面返回错误")
        else:
            print("   ✅ 续期成功！")
    elif resp.status_code == 302:
        print("   ✅ 续期成功（302 重定向）")
    else:
        print(f"   响应前300字符: {resp.text[:300]}")
        print("   ⚠️ 不确定是否成功")
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)
