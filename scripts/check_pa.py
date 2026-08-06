import requests
import os
import sys
import datetime
import json

PA_USERNAME = os.environ.get('PA_USERNAME', '').strip()
PA_API_TOKEN = os.environ.get('PA_API_TOKEN', '').strip()
PA_DOMAIN = os.environ.get('PA_DOMAIN', '').strip()
DINGTALK_WEBHOOK = os.environ.get('DINGTALK_WEBHOOK', '').strip()
WECOM_WEBHOOK = os.environ.get('WECOM_WEBHOOK', '').strip()
THRESHOLD_DAYS = int(os.environ.get('THRESHOLD_DAYS', '7'))

BASE_URL = 'https://www.pythonanywhere.com'
NOW = datetime.datetime.now(datetime.timezone.utc)

print(f"[{NOW}] PythonAnywhere 到期监控启动")

if not PA_USERNAME or not PA_API_TOKEN or not PA_DOMAIN:
    print("❌ 缺少必要环境变量：PA_USERNAME, PA_API_TOKEN, PA_DOMAIN")
    sys.exit(1)

headers = {
    'Authorization': f'Token {PA_API_TOKEN}',
    'Accept': 'application/json'
}

print(f"\n1. 查询 WebApp 信息...")
try:
    resp = requests.get(
        f'{BASE_URL}/api/v1/user/{PA_USERNAME}/webapps/',
        headers=headers,
        timeout=30
    )
    print(f"   URL: {BASE_URL}/api/v1/user/{PA_USERNAME}/webapps/")
    print(f"   状态码: {resp.status_code}")
    
    if resp.status_code == 401:
        print("   ❌ API Token 无效")
        sys.exit(1)
    elif resp.status_code == 404:
        print(f"   ❌ 域名 {PA_DOMAIN} 不存在")
        sys.exit(1)
    elif resp.status_code != 200:
        print(f"   ❌ 查询失败: {resp.text[:300]}")
        sys.exit(1)
    
    data = resp.json()
    print(f"   响应类型: {type(data).__name__}")
    print(f"   响应内容: {str(data)[:500]}")
    
    webapp = None
    if isinstance(data, list):
        for app in data:
            if app.get('domain') == PA_DOMAIN or PA_DOMAIN in app.get('domain', ''):
                webapp = app
                break
        if not webapp and len(data) > 0:
            webapp = data[0]
            print(f"   ⚠️ 未精确匹配域名，使用第一个 WebApp")
    elif isinstance(data, dict):
        webapp = data
    
    if not webapp:
        print(f"   ❌ 未找到 WebApp")
        sys.exit(1)
        
    print(f"   域名: {webapp.get('domain')}")
    print(f"   状态: {webapp.get('status')}")
    expiry_str = webapp.get('expiry', '')
    print(f"   到期时间: {expiry_str}")
    
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n2. 计算剩余天数...")
try:
    if not expiry_str:
        print("   ❌ 到期时间为空")
        sys.exit(1)
    
    if expiry_str.endswith('Z'):
        expiry_str = expiry_str[:-1] + '+00:00'
    
    expiry = datetime.datetime.fromisoformat(expiry_str)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=datetime.timezone.utc)
    
    days_left = (expiry - NOW).days
    print(f"   到期时间: {expiry.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   当前时间: {NOW.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   剩余天数: {days_left} 天")
    
except Exception as e:
    print(f"   ❌ 异常: {e}")
    sys.exit(1)

print(f"\n3. 发送通知...")
need_alert = days_left <= THRESHOLD_DAYS
alert_messages = []

if need_alert:
    title = f"⚠️ PythonAnywhere 到期告警"
    message = (
        f"您的 PythonAnywhere 免费版即将到期！\n"
        f"域名: {PA_DOMAIN}\n"
        f"到期时间: {expiry.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"剩余天数: {days_left} 天\n"
        f"请尽快登录 https://www.pythonanywhere.com 手动续期。"
    )
    print(f"  ⚠️ 剩余 {days_left} 天 ≤ {THRESHOLD_DAYS} 天阈值，触发告警！")
    print(f"\n{message}")
    
    if DINGTALK_WEBHOOK:
        try:
            dingtalk_data = {
                "msgtype": "text",
                "text": {"content": f"{title}\n\n{message}"}
            }
            resp = requests.post(DINGTALK_WEBHOOK, json=dingtalk_data, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("\n   ✅ 钉钉通知发送成功")
            else:
                print(f"\n   ❌ 钉钉通知失败: {result}")
        except Exception as e:
            print(f"\n   ❌ 钉钉通知异常: {e}")
    
    if WECOM_WEBHOOK:
        try:
            wecom_data = {
                "msgtype": "text",
                "text": {"content": f"{title}\n\n{message}"}
            }
            resp = requests.post(WECOM_WEBHOOK, json=wecom_data, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("\n   ✅ 企业微信通知发送成功")
            else:
                print(f"\n   ❌ 企业微信通知失败: {result}")
        except Exception as e:
            print(f"\n   ❌ 企业微信通知异常: {e}")
    
    alert_messages.append(message)
    
    github_summary = f"## ⚠️ PythonAnywhere 到期告警\n\n"
    github_summary += f"- **域名**: `{PA_DOMAIN}`\n"
    github_summary += f"- **到期时间**: `{expiry.strftime('%Y-%m-%d %H:%M UTC')}`\n"
    github_summary += f"- **剩余天数**: **{days_left} 天**\n\n"
    github_summary += f"请尽快登录 [PythonAnywhere](https://www.pythonanywhere.com) 手动续期。"
    
    with open(os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null'), 'a', encoding='utf-8') as f:
        f.write(github_summary + '\n')
    
    print(f"\n   📧 GitHub Issue/邮件通知将由 Workflow 失败触发")
    sys.exit(1)
else:
    print(f"  ✅ 剩余 {days_left} 天 > {THRESHOLD_DAYS} 天阈值，无需告警")
    
    github_summary = f"## ✅ PythonAnywhere 状态正常\n\n"
    github_summary += f"- **域名**: `{PA_DOMAIN}`\n"
    github_summary += f"- **到期时间**: `{expiry.strftime('%Y-%m-%d %H:%M UTC')}`\n"
    github_summary += f"- **剩余天数**: **{days_left} 天**\n\n"
    github_summary += f"下次检查: 每月4号"
    
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY', '')
    if summary_path:
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write(github_summary + '\n')
    
    sys.exit(0)
