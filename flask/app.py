from flask import Flask, request
import hashlib
import urllib.parse
import json
import re
import html
import requests

app = Flask(__name__)

# ===== 配置（根据你提供的信息） =====
APP_KEY = "bda90f8358af139b"          # 订单接口密钥（/recharge），保持不变
TICKET_KEY = "tk_9f3c7a1e5b2d8460"    # 工单接口独立密钥（/ticket），与订单分开
TG_BOT_TOKEN = "8020346768:AAE4iTCYNPhxanT-A2Gc22FEphEpdXbJSfo"
TG_CHAT_ID = "1275674390"


# ===== 发送 Telegram 消息 =====
def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": TG_CHAT_ID,
            "text": text
        })
    except Exception as e:
        print("Telegram error:", e)


# ===== 最终正确的签名算法（100% 等价插件 PHP） =====
def generate_signature(post_data: dict, app_key: str) -> str:
    # 克隆数据
    data = dict(post_data)

    # 删除 sign
    data.pop("sign", None)

    # 删除空字段
    data = {k: v for k, v in data.items() if v not in ("", None)}

    # 按 key 排序
    items = sorted(data.items(), key=lambda x: x[0])

    # 手工构建 query_string（关键：data 必须原样保留）
    encoded_items = []
    for k, v in items:
        if k == "data":
            # ⚠ 保持原样（包含 %7B%22 编码）
            encoded_items.append(f"{k}={v}")
        else:
            # 其他字段 urlencode 再参与
            encoded_items.append(f"{k}={urllib.parse.quote(str(v))}")

    # 拼接成 http_build_query 效果
    query_string = "&".join(encoded_items)

    # PHP: urldecode
    query_string = urllib.parse.unquote(query_string)

    # 拼接 key
    final_str = f"{query_string}&key={app_key}"

    # 计算 md5（返回小写）
    return hashlib.md5(final_str.encode("utf-8")).hexdigest()


# ===== 清洗 HTML：工单内容/标题可能带富文本标签 =====
def clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ===== 写日志 =====
def write_log(filename, content):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content + "\n")


# ===== 主接口：插件的 API 通知发送到这里 =====
@app.route("/recharge", methods=["POST"])
def recharge():

    print("======= NEW POST =======")
    raw = request.get_data().decode()
    print("RAW POST:", raw)

    # 自动识别 JSON / form-data
    if request.is_json:
        post_data = request.get_json()
    else:
        post_data = request.form.to_dict()

    if not post_data:
        return "no data", 400

    print("PARSED POST DATA:", post_data)

    # ===== 验证签名 =====
    client_sign = post_data.get("sign", "")
    server_sign = generate_signature(post_data, APP_KEY)

    print("client_sign =", client_sign)
    print("server_sign =", server_sign)

    if client_sign != server_sign:
        print("SIGN ERROR !!!!!")
        return "sign error", 400

    # ===== 解析 data 内容 =====
    try:
        payload = json.loads(post_data.get("data", "{}"))
    except:
        return "data json error", 400

    commodity = payload.get("commodity", {})    # 商品
    order = payload.get("order", {})            # 订单

    # extend 可能为 null，这里做兼容
    try:
        extend = json.loads(commodity.get("extend", "{}") or "{}")
    except:
        extend = {}

    # widget（玩家字段）
    try:
        widget = json.loads(order.get("widget", "{}") or "{}")
    except:
        widget = {}

    # 玩家账号（如果有控件）
    game_account = ""
    if isinstance(widget, dict) and "game_account" in widget:
        game_account = widget["game_account"].get("value", "")

    # 附加字段（可能为空）
    good_id = extend.get("good_id", "")
    num = extend.get("num", "")

    # 写日志
    write_log("data.txt", json.dumps(payload, ensure_ascii=False))
    write_log("recharge.txt", json.dumps({
        "gameAccount": game_account,
        "goodId": good_id,
        "num": num
    }, ensure_ascii=False))

    # ===== 推送 Telegram =====
    msg = (
        "📦 异次元发卡 · 新订单\n"
        f"商品：{commodity.get('name', '')}\n"
        f"金额：{order.get('amount', '')} 元\n"
        f"订单号：{order.get('trade_no', '')}\n"
        f"联系方式：{order.get('contact', '')}\n"
        f"玩家账号：{game_account}\n"
        f"道具ID：{good_id}\n"
        f"数量：{num}\n"
        f"支付时间：{order.get('pay_time', '')}\n"
    )

    send_telegram_message(msg)

    return "success"


# ===== 工单接口：工单提醒插件 (TicketNotify) 发送到这里 =====
@app.route("/ticket", methods=["POST"])
def ticket():

    print("======= NEW TICKET =======")
    raw = request.get_data().decode()
    print("RAW POST:", raw)

    if request.is_json:
        post_data = request.get_json()
    else:
        post_data = request.form.to_dict()

    if not post_data:
        return "no data", 400

    print("PARSED POST DATA:", post_data)

    # ===== 验证签名（使用工单独立密钥） =====
    client_sign = post_data.get("sign", "")
    server_sign = generate_signature(post_data, TICKET_KEY)

    print("client_sign =", client_sign)
    print("server_sign =", server_sign)

    if client_sign != server_sign:
        print("TICKET SIGN ERROR !!!!!")
        return "sign error", 400

    # ===== 解析 data 内容 =====
    try:
        payload = json.loads(post_data.get("data", "{}"))
    except:
        return "data json error", 400

    # 必须确认这是工单事件，避免混入其他来源
    if payload.get("type") != "ticket":
        return "not a ticket payload", 400

    event = payload.get("event", "")            # create / reply
    ticket_info = payload.get("ticket", {})     # 工单
    message = payload.get("message", {})        # 消息
    notify_time = payload.get("time", "")

    # 状态 / 优先级 中文化
    status_map = {0: "待处理", 1: "待用户回复", 2: "已解决", 3: "已关闭"}
    priority_map = {0: "低", 1: "中", 2: "高"}
    type_map = {0: "售前", 1: "售后"}

    status = status_map.get(ticket_info.get("status"), ticket_info.get("status", ""))
    priority = priority_map.get(ticket_info.get("priority"), ticket_info.get("priority", ""))
    ticket_type = type_map.get(ticket_info.get("type"), ticket_info.get("type", ""))

    event_text = "新建工单" if event == "create" else "工单回复"

    # 写日志
    write_log("ticket.txt", json.dumps(payload, ensure_ascii=False))

    # ===== 推送 Telegram =====
    msg = (
        f"🎫 异次元发卡 · {event_text}\n"
        f"工单号：{ticket_info.get('ticket_no', '')}\n"
        f"标题：{clean_text(ticket_info.get('title', ''))}\n"
        f"类型：{ticket_type}　优先级：{priority}\n"
        f"状态：{status}\n"
        f"关联商品：{ticket_info.get('commodity_name', '') or '无'}\n"
        f"关联订单：{ticket_info.get('order_trade_no', '') or '无'}\n"
        f"发送人：{clean_text(message.get('sender_name', ''))}\n"
        f"内容：{clean_text(message.get('content', ''))}\n"
        f"时间：{notify_time}\n"
    )

    send_telegram_message(msg)

    return "success"


# ===== 启动服务 =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
