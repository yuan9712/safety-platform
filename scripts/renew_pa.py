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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

BASE_URL = 'https://www.pythonanywhere.com'

print(f"\n1. 获取登录页面...")
try:
    resp = session.get(f'{BASE_URL}/login/', timeout=30)
    csrf_match = re.search(r'name="csrfmiddlewaretoken"[^>]*value="([^"]+)"', resp.text)
    if not csrf_match:
        print("   ❌ 找不到 CSRF Token")
        sys.exit(1)
    login_csrf = csrf_match.group(1)
    print(f"   ✅ CSRF Token: {login_csrf[:8]}...")
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n2. 登录...")
try:
    resp = session.post(f'{BASE_URL}/login/', data={
        'auth-username': USERNAME,
        'auth-password': PASSWORD,
        'csrfmiddlewaretoken': login_csrf,
        'login_view-current_step': 'auth'
    }, timeout=30, headers={'Referer': f'{BASE_URL}/login/'})
    
    if resp.url != f'{BASE_URL}/login/':
        print(f"   ✅ 登录成功，跳转到: {resp.url}")
    elif 'logout' in resp.text.lower() or 'dashboard' in resp.text.lower():
        print("   ✅ 登录成功")
    else:
        print("   ❌ 登录失败")
        print(f"   响应前200字符: {resp.text[:200]}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n3. 访问 Webapps 页面...")
try:
    web_url = f'{BASE_URL}/user/{USERNAME}/webapps/'
    resp = session.get(web_url, timeout=30)
    print(f"   状态码: {resp.status_code}")
    print(f"   页面大小: {len(resp.text)} 字符")
    
    with open('/tmp/webapps.html', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    
    renew_forms = re.findall(r'<form[^>]*action="([^"]*)"[^>]*>', resp.text)
    print(f"   找到 {len(renew_forms)} 个表单:")
    for form_action in renew_forms:
        print(f"     - {form_action}")
    
    renew_urls = re.findall(r'action="([^"]*renew[^"]*)"', resp.text)
    print(f"   包含 renew 的表单: {renew_urls}")
    
    if not renew_urls:
        print("   ❌ 找不到续期表单，保存了页面到 /tmp/webapps.html")
        print("   请检查页面内容")
        sys.exit(1)
    
    renew_path = renew_urls[0]
    if not renew_path.startswith('http'):
        if renew_path.startswith('/'):
            renew_url = f'{BASE_URL}{renew_path}'
        else:
            renew_url = f'{web_url}{renew_path}'
    else:
        renew_url = renew_path
    print(f"   ✅ 续期 URL: {renew_url}")
    
    csrf_match = re.search(r'name="csrfmiddlewaretoken"[^>]*value="([^"]+)"', resp.text)
    if not csrf_match:
        print("   ❌ 找不到页面 CSRF Token")
        sys.exit(1)
    renew_csrf = csrf_match.group(1)
    print(f"   ✅ 页面 CSRF Token: {renew_csrf[:8]}...")
    
    domain_field = re.findall(r'<input[^>]*name="([^"]*domain[^"]*)"[^>]*>', resp.text, re.IGNORECASE)
    print(f"   与 domain 相关的输入字段: {domain_field}")
    
    hidden_inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"[^>]*>', resp.text)
    print(f"   隐藏表单字段:")
    for name, value in hidden_inputs:
        print(f"     {name} = {value[:50] if len(value) > 50 else value}")
        
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n4. 执行续期...")
try:
    form_data = {'csrfmiddlewaretoken': renew_csrf}
    
    domain_inputs = re.findall(r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"[^>]*>', resp.text)
    for name, value in domain_inputs:
        if name not in form_data and name != 'csrfmiddlewaretoken':
            form_data[name] = value
    
    print(f"   提交表单字段: {list(form_data.keys())}")
    
    resp = session.post(renew_url, data=form_data, timeout=30,
                       headers={'Referer': web_url, 'X-Requested-With': 'XMLHttpRequest'})
    print(f"   状态码: {resp.status_code}")
    print(f"   响应前500字符: {resp.text[:500]}")
    
    if resp.status_code == 200:
        if 'success' in resp.text.lower() or 'renew' in resp.text.lower():
            print("\n✅ 续期成功！")
        elif 'error' in resp.text.lower():
            print("\n⚠️ 页面返回错误")
        else:
            print("\n✅ 请求完成（状态码200）")
    elif resp.status_code == 302:
        print("\n✅ 续期成功（302重定向）")
    else:
        print("\n⚠️ 不确定是否成功，请检查上方响应")
        
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)
