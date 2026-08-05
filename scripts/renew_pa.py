import requests
import os
import sys
import datetime

USERNAME = os.environ.get('PA_USERNAME', '').strip()
API_TOKEN = os.environ.get('PA_API_TOKEN', '').strip()
DOMAIN = os.environ.get('PA_DOMAIN', '').strip()

print(f"[{datetime.datetime.now()}] PythonAnywhere 续期脚本启动")
print(f"  PA_USERNAME: {'✅ 已设置' if USERNAME else '❌ 未设置'}")
print(f"  PA_API_TOKEN: {'✅ 已设置' if API_TOKEN else '❌ 未设置'}")
print(f"  PA_DOMAIN: {'✅ 已设置' if DOMAIN else '❌ 未设置'}")

if not USERNAME or not API_TOKEN or not DOMAIN:
    print("\n❌ 缺少密钥！请到 GitHub 仓库 Settings → Secrets → Actions 添加：")
    print("   PA_USERNAME = yuanpf")
    print("   PA_API_TOKEN = 你的PythonAnywhere API Token")
    print("   PA_DOMAIN = yuanpf.pythonanywhere.com")
    sys.exit(1)

url = f'https://www.pythonanywhere.com/api/v1/user/webapps/{DOMAIN}/renew/'
headers = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

print(f"\n请求 URL: {url}")
print(f"请求头: Authorization: Token {API_TOKEN[:4]}...{API_TOKEN[-4:]}")

try:
    resp = requests.post(url, headers=headers, timeout=30, allow_redirects=True)
    print(f"响应状态码: {resp.status_code}")
    print(f"响应头 Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"响应前200字符: {resp.text[:200]}")

    if resp.status_code == 200:
        if '<html' in resp.text.lower():
            print("\n⚠️ 返回了 HTML 页面而非 JSON，可能 API 地址有误或 Token 无效")
            print("  请确认:")
            print("  1. PA_API_TOKEN 是否为 PythonAnywhere 的 API Token（不是登录密码）")
            print("  2. PA_DOMAIN 是否为 yuanpf.pythonanywhere.com")
            sys.exit(1)
        print("\n✅ 续期成功！免费版已延长3个月。")
    elif resp.status_code == 401:
        print("\n❌ API Token 无效！请到 PythonAnywhere → Account → API Token 重新生成。")
        sys.exit(1)
    elif resp.status_code == 404:
        print(f"\n❌ 域名不存在！请检查 PA_DOMAIN: {DOMAIN}")
        sys.exit(1)
    elif resp.status_code == 400:
        print("\n⚠️ 请求被拒绝，可能已在有效期内，无需续期。")
    else:
        print(f"\n❌ 续期失败，状态码: {resp.status_code}")
        sys.exit(1)
except requests.exceptions.Timeout:
    print("❌ 请求超时")
    sys.exit(1)
except Exception as e:
    print(f"❌ 请求异常: {e}")
    sys.exit(1)
