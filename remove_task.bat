@echo off
chcp 65001 >nul
echo 正在删除自动签到定时任务...
schtasks /delete /tn "TraeWork 每日自动签到" /f
echo.
echo 定时任务已删除！
pause
