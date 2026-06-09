#!/bin/bash
# 查看定时任务状态

if crontab -l 2>/dev/null | grep -q "email_summary.py"; then
    echo "[运行中] 邮件总结 (9:00)"
else
    echo "[已停止] 邮件总结"
fi

echo ""
crontab -l 2>/dev/null | grep -v "^$" | grep -v "^#"
