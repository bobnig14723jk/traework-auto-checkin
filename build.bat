@echo off
chcp 65001 >nul
echo ========================================
echo   TraeWork CN 自动签到 - 一键打包脚本
echo ========================================
echo.

pip install pyinstaller -q

echo 正在打包签到程序...
if exist orange.ico (
    echo   使用橙子图标 🍊
    pyinstaller --onefile --windowed --icon=orange.ico --name=OrangeCheckin checkin.py -y
) else (
    echo   未找到orange.ico，使用默认图标
    pyinstaller --onefile --windowed --name=OrangeCheckin checkin.py -y
)

echo.
echo 正在打包坐标校准工具...
pyinstaller --onefile --name=CalibrateCoords calibrate.py -y

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 生成的文件在 dist 目录下：
echo   - dist\OrangeCheckin.exe    （签到程序，双击运行）
echo   - dist\CalibrateCoords.exe  （坐标校准工具）
echo.
echo 首次使用请先运行 CalibrateCoords.exe 校准坐标！
echo.
pause
