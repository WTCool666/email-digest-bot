@echo off
chcp 65001 >nul
echo ===== 邮件总结 - Windows 任务计划设置 =====
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%email_summary.py

echo 将创建每天 9:00 运行的定时任务...
echo 脚本路径: %PYTHON_SCRIPT%
echo.

schtasks /create /tn "EmailSummary_9" /tr "python \"%PYTHON_SCRIPT%\"" /sc daily /st 09:00 /f

if %errorlevel% == 0 (
    echo.
    echo [成功] 已创建定时任务：
    echo   EmailSummary_9 - 每天 9:00
    echo.
    echo 如需删除: schtasks /delete /tn "EmailSummary_9" /f
) else (
    echo.
    echo [失败] 请尝试以管理员身份运行此脚本。
)

pause
