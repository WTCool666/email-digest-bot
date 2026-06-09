# email-digest-bot

每日自动读取公司邮箱，AI 生成摘要，推送到钉钉群。

## 功能

- 通过 IMAP 协议读取昨日所有邮件
- 调用 AI 大模型（支持智谱GLM/DeepSeek/通义千问/Kimi/OpenAI 等）生成中文摘要
- 按重要程度分类：重要邮件、普通邮件、通知类邮件
- OA 审批提醒自动标记为重要
- 通过钉钉群机器人 Webhook 推送 Markdown 格式消息
- 支持 Linux（cron）和 Windows（任务计划）定时运行

## 效果示例

```
📬 昨日邮件总结 (2026-06-08)

## 重要邮件
- [张三] 关于Q3项目里程碑确认 — 需要在周五前回复确认
- [OA系统] 审批提醒：李四提交了差旅报销单 — 待您审批

## 普通邮件
- [王五] 本周技术分享会通知 — 周四下午3点会议室A

## 通知类邮件
- [系统] 您的密码将在30天后过期
- [HR] 6月考勤数据已生成

---
共 4 封邮件 | 由 AI 自动生成
```

## 文件说明

```
email-digest-bot/
├── email_summary.py       # 主脚本
├── config.example.json    # 配置模板（复制为 config.json 后填写）
├── requirements.txt       # Python 依赖
├── start.sh               # [Linux] 启动定时任务
├── stop.sh                # [Linux] 停止定时任务
├── status.sh              # [Linux] 查看任务状态
├── setup.bat              # [Windows] 创建任务计划
├── .gitignore
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置

```bash
cp config.example.json config.json
vim config.json
```

需要填写三项配置：

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `email` | 邮箱 IMAP 信息 | 邮箱设置中开启 IMAP 并生成授权码 |
| `deepseek` | AI 模型 API | 选择一个模型平台注册获取 API Key |
| `dingtalk` | 钉钉机器人 | 群设置 → 机器人 → 添加自定义机器人（选择加签） |

配置文件内附有 6 种 AI 模型和 7 种邮箱的参数参考，直接复制即可。

### 3. 手动测试

```bash
python3 email_summary.py
```

### 4. 设置定时任务

**Linux：**

```bash
./start.sh          # 启动（每天 9:00）
./stop.sh           # 停止
./status.sh         # 查看状态
```

**Windows：**

右键以管理员身份运行 CMD：

```cmd
setup.bat
```

管理命令：

```cmd
schtasks /query /tn "EmailSummary_9"     :: 查看
schtasks /run /tn "EmailSummary_9"       :: 手动运行
schtasks /delete /tn "EmailSummary_9" /f  :: 删除
```

## 日志

```bash
tail -20 email_summary.log    # Linux
type email_summary.log         # Windows
```

## 常见问题

**Q: 显示"昨日无邮件"？**
A: 可能是周末没人发邮件。确认 IMAP 搜索日期格式正确，手动测试时确保昨天有邮件。

**Q: AI 摘要生成失败？**
A: 检查 `config.json` 中 `deepseek.api_key` 和 `deepseek.base_url` 是否匹配。不同模型的 API 地址不同，配置文件内有参考。

**Q: 钉钉发送失败？**
A: 检查 Webhook URL 是否正确，加签密钥是否以 SEC 开头。

**Q: 如何换 AI 模型？**
A: 修改 `config.json` 中 `deepseek` 的三个字段：`api_key`、`model`、`base_url`。配置文件 `_备注_AI模型配置` 中列出了 6 种模型的参数。

**Q: 服务器重启后定时任务还在吗？**
A: 在。Linux cron 和 Windows 任务计划都是持久化的，重启不影响。
