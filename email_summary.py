#!/usr/bin/env python3
"""个人公司邮箱每日总结 - 读取昨日邮件，AI 摘要，发送到钉钉"""

import json
import imaplib
import email
import logging
import sys
import time
import hashlib
import hmac
import base64
import urllib.parse
from datetime import datetime, timedelta
from email.header import decode_header

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("email_summary.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _decode_str(s):
    """解码邮件头部字段（Subject, From 等）"""
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for data, charset in parts:
        if isinstance(data, bytes):
            result.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(data)
    return "".join(result)


def _get_text_body(msg, max_chars=2000):
    """从邮件中提取纯文本正文，截取前 max_chars 字符"""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    return text[:max_chars]
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                return text[:max_chars]
    return ""


def fetch_yesterday_emails(config):
    """通过 IMAP 拉取昨日所有邮件，返回列表 [{from, subject, date, body}]"""
    email_cfg = config["email"]
    imap_server = email_cfg["imap_server"]
    imap_port = email_cfg["imap_port"]
    username = email_cfg["username"]
    password = email_cfg["password"]

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
    today = datetime.now().strftime("%d-%b-%Y")

    logger.info("连接 IMAP 服务器 %s:%d ...", imap_server, imap_port)
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    try:
        mail.login(username, password)
        mail.select("INBOX")

        search_criteria = f'(SINCE {yesterday} BEFORE {today})'
        logger.info("搜索条件: %s", search_criteria)
        status, message_ids = mail.search(None, search_criteria)

        if status != "OK":
            logger.error("邮件搜索失败")
            return []

        id_list = message_ids[0].split()
        if not id_list:
            logger.info("昨日无邮件")
            return []

        # 最多处理 50 封
        id_list = id_list[-50:]
        logger.info("找到 %d 封邮件，开始处理...", len(id_list))

        emails = []
        for i, msg_id in enumerate(id_list):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                logger.warning("邮件 %d 获取失败", i + 1)
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            emails.append({
                "from": _decode_str(msg.get("From")),
                "subject": _decode_str(msg.get("Subject")),
                "date": msg.get("Date", ""),
                "body": _get_text_body(msg),
            })

        logger.info("成功读取 %d 封邮件", len(emails))
        return emails
    finally:
        mail.logout()


def summarize_emails(config, emails):
    """调用 DeepSeek API 生成邮件摘要，返回 Markdown 文本"""
    if not emails:
        return "昨日无邮件。"

    ds_cfg = config["deepseek"]
    api_key = ds_cfg["api_key"]
    model = ds_cfg["model"]
    base_url = ds_cfg["base_url"]

    # 构造邮件列表文本
    email_list = []
    for i, e in enumerate(emails, 1):
        email_list.append(
            f"邮件{i}:\n"
            f"  发件人: {e['from']}\n"
            f"  主题: {e['subject']}\n"
            f"  日期: {e['date']}\n"
            f"  正文: {e['body'][:500]}\n"
        )

    email_text = "\n".join(email_list)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    prompt = (
        f"以下是 {yesterday} 收到的 {len(emails)} 封邮件信息，请生成一份中文邮件摘要报告。\n\n"
        "要求：\n"
        "1. 按重要程度分为三类：重要邮件、普通邮件、通知类邮件\n"
        '   重要邮件判定规则：OA审批提醒、带"审批""urgent""紧急"关键词的邮件一律归为重要邮件\n'
        "2. 每封邮件用一句话概括摘要\n"
        "3. 最后列出「需关注事项」总结\n"
        "4. 使用 Markdown 格式\n"
        f"5. 标题格式为：# 📬 昨日邮件总结 ({yesterday})\n"
        "6. 末尾加上：共 N 封邮件 | 由 AI 自动生成\n"
        "7. 控制在 2000 字以内\n\n"
        f"邮件内容：\n{email_text}"
    )

    logger.info("调用 AI API 生成摘要...")
    url = f"{base_url}/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.3,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        summary = result["choices"][0]["message"]["content"]
        logger.info("摘要生成成功，长度: %d 字", len(summary))
        return summary
    except requests.RequestException as e:
        logger.error("DeepSeek API 调用失败: %s", e)
        raise


def _generate_sign(secret):
    """生成钉钉机器人加签"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_to_dingtalk(config, markdown_text):
    """通过钉钉群机器人 Webhook 发送 Markdown 消息"""
    dt_cfg = config["dingtalk"]
    webhook_url = dt_cfg["webhook_url"]
    secret = dt_cfg.get("secret", "")

    if secret:
        timestamp, sign = _generate_sign(secret)
        webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    title = "昨日邮件总结"
    for line in markdown_text.split("\n"):
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            break

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": markdown_text,
        },
    }

    logger.info("发送消息到钉钉...")
    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info("钉钉消息发送成功")
        else:
            logger.error("钉钉返回错误: %s", result)
            raise RuntimeError(f"钉钉发送失败: {result}")
    except requests.RequestException as e:
        logger.error("钉钉 Webhook 请求失败: %s", e)
        raise


def main():
    """主流程：读取邮件 → AI 摘要 → 发送钉钉"""
    try:
        config = load_config()
        logger.info("===== 邮件总结任务开始 =====")

        emails = fetch_yesterday_emails(config)
        if not emails:
            logger.info("昨日无邮件，跳过摘要")
            return 0

        summary = summarize_emails(config, emails)
        send_to_dingtalk(config, summary)

        logger.info("===== 邮件总结任务完成 =====")
        return 0
    except Exception:
        logger.exception("任务执行失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
