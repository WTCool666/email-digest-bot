#!/bin/bash
# 停止邮件总结定时任务

crontab -l 2>/dev/null | grep -v "email_summary" | crontab -
echo "邮件总结定时任务已停止"
