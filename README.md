# acg-faka 工单提醒插件 (TicketNotify)

异次元发卡系统（acg-faka）插件：当**用户创建工单**或**用户回复工单**时，自动将工单与消息内容带上 MD5 签名，POST 到站长自定义的 API 地址，用于推送到 Telegram 等渠道。

本仓库同时包含配套的 Flask 接收端示例（`flask/app.py`），可直接复用店内已有的订单通知服务，仅新增 `/ticket` 路由。

## 目录结构

```
plugin/TicketNotify/          # 发卡系统插件（放到 app/Plugin/ 下）
├── Config/Info.php           # 插件信息（必填）
├── Config/Config.php         # 默认配置
├── Config/Submit.php         # 后台配置表单
└── Hook/Main.php             # 钩子实现

flask/app.py                  # 配套 Flask 接收端（含订单 /recharge + 工单 /ticket）
```

## 工作原理

插件订阅两个钩子点位（在事务提交后触发，钩子异常不会影响接口结果）：

| 点位 | 常量 | 触发时机 |
| --- | --- | --- |
| `0x2100` | `USER_API_TICKET_CREATE_AFTER` | 用户创建工单后 |
| `0x2101` | `USER_API_TICKET_REPLY_AFTER` | 用户回复工单后 |

发送的请求体（POST `form_params`）：

| 字段 | 说明 |
| --- | --- |
| `data` | JSON 字符串，结构见下 |
| `sign` | 签名，`md5(urldecode(http_build_query($data)."&key=".$key))` |
| 其他 | 通过 `param` 配置追加的自定义字段 |

`data` 结构：

```json
{
  "type": "ticket",
  "event": "create 或 reply",
  "ticket": { "ticket_no": "...", "title": "...", "status": 0, "priority": 1, "type": 1, "...": "..." },
  "message": { "sender_name": "...", "content": "...", "...": "..." },
  "time": "2026-10-11 10:00:00"
}
```

`type` 固定为 `ticket`，用于与订单通知（订单为其他类型）区分。

## 安装

1. 将 `plugin/TicketNotify` 整个目录复制到发卡系统 `app/Plugin/` 下。
2. 确保目录属主与站点一致（如 `www:www`），并具备读权限。
3. 后台「插件」页面找到 **工单提醒**，点击启用，并在配置页填写：
   - **API 地址**：如 `http://127.0.0.1:8000/ticket`
   - **通信密钥**：与接收端约定的独立密钥（勿与订单插件共用）
   - 请求方式、附加参数、请求头（可选）、是否记录日志
4. 保存配置。若之后修改了 `Hook` 文件，需**先禁用再启用**插件以重建钩子缓存。

## 配套 Flask 接收端

`flask/app.py` 基于原订单通知服务扩展，新增 `POST /ticket`：

- 使用独立密钥 `TICKET_KEY` 校验签名（与订单的 `APP_KEY` 分开）。
- 校验 `data.type == "ticket"`，非工单内容直接拒绝，避免与订单混流。
- 推送格式为工单专用样式（含工单号、标题、类型、优先级、状态、关联商品/订单、发送人、内容）。
- 日志写入 `ticket.txt`。

启动（示例，使用 systemd 或直接运行）：

```bash
pip install flask requests
python app.py            # 监听 0.0.0.0:8000
```

> 生产环境建议用 gunicorn/uwsgi 替代 Flask 内置的开发服务器，并关闭 `debug=True`。

## 签名算法

插件 `App\Util\Str::generateSignature` 与 Flask 端实现等价：

```
1. 去掉 sign 字段
2. 按 key 字典序排序
3. 去掉值为空字符串的字段
4. query = http_build_query($data) 后再 urldecode
5. sign = md5(query + "&key=" + appKey)
```

Flask 端对 `data` 字段特殊处理（保持原样后整体 `unquote`），以保证与 PHP 的 `http_build_query` + `urldecode` 行为一致。
