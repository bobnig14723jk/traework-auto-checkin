@echo off
chcp 65001 >nul
echo ========================================
echo   TraeWork CN 自动签到 - 设置定时任务
echo ========================================
echo.
echo 此脚本将创建Windows计划任务，每天早上9:00自动签到。
echo 如果9点时电脑未开机，下次开机后会自动补签。
echo.
pause

:: 获取当前目录
set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%dist\OrangeCheckin.exe"

if not exist "%EXE_PATH%" (
    set "EXE_PATH=%SCRIPT_DIR%OrangeCheckin.exe"
)

if not exist "%EXE_PATH%" (
    echo 错误：找不到 OrangeCheckin.exe！
    echo 请先运行 build.bat 打包，或者将exe放在同一目录下。
    pause
    exit /b 1
)

echo 正在创建计划任务...
schtasks /create /tn "TraeWork 每日自动签到" /tr "\"%EXE_PATH%\"" /sc daily /st 09:00 /f /rl highest

echo.
echo ========================================
echo   定时任务创建成功！
echo ========================================
echo.
echo 任务名称：TraeWork 每日自动签到
echo 执行时间：每天 09:00
echo 执行程序：%EXE_PATH%
echo.
echo 如果想删除定时任务，请运行 remove_task.bat
echo.
pause
