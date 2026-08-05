@echo off
chcp 65001 >nul
echo ========================================
echo   安全隐患上报系统 - 本地启动
echo   铁路运营公司电务段
echo ========================================
echo.

if not exist "venv" (
    echo [1/2] 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo [2/2] 启动服务...
echo.
echo ========================================
echo   系统已启动！（本地测试用）
echo   上报页面: http://localhost:5000
echo   管理后台: http://localhost:5000/login
echo   二维码:   http://localhost:5000/qrcode
echo.
echo   管理员账号: admin / 密码: admin123
echo ========================================
echo.
echo   注意：本地启动仅用于测试
echo   正式使用请部署到 PythonAnywhere（永久免费公网）
echo.

python app.py
pause
