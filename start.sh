#!/bin/bash
# 启动邮件总结定时任务
DIR="$(cd "$(dirname "$0")" && pwd)"

if crontab -l 2>/dev/null | grep -q "email_summary.py"; then
    echo "[已存在] 邮件总结"
else
    (crontab -l 2>/dev/null
     echo "# 邮件总结：每天9:00"
     echo "0 9 * * * cd ${DIR} && /usr/bin/python3 email_summary.py >> email_summary.log 2>&1"
    ) | crontab -
    echo "[已启动] 邮件总结：每天 9:00"
fi

echo ""
echo "当前定时任务："
crontab -l 2>/dev/null | grep -v "^$" | grep -v "^#"
