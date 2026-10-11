# acg-faka 工单提醒插件

异次元发卡系统（acg-faka）插件：当**用户创建工单**或**用户回复工单**时，自动将工单与消息内容带上 MD5 签名，POST 到站长自定义的 API 地址，用于推送到 Telegram 等渠道。

本仓库同时包含配套的 Flask 接收端示例（`flask/app.py`），可直接复用店内已有的订单通知服务，仅新增 `/ticket` 路由。

## 为什么插件目录叫 `Demo` 而不是 `TicketNotify`

> 这一段很关键，请先读完再安装。

acg-faka 的插件启用入口 `_plugin_start()` 是 **kernel/Plugin.php 内的专有加密函数**，它只允许**官方商店授权过**的插件被启用：
- 商店插件（如 `Demo`、`ApiNotification`）点「启用」会正常写入 STATUS 并注册钩子缓存；
- 纯本地手写的插件名（如 `TicketNotify`）点「启用」会**静默失败**（后台闪一下仍是「未启用」），因为该函数会拒绝未经商店授权的插件名。

因此本插件的做法是：**借用一个商店插件目录名（`Demo`）作为载体**，把工单通知逻辑放进该目录的 `Hook/` 里。
由于钩子注册是**整个 `Hook/` 目录扫描**的，系统会把我们新增的钩子类一并注册，并且后台「启用 / 停用」按钮能正常维护它——不再需要任何手工干预。

- 后台插件列表中显示的插件名由 `Config/Info.php` 的 `Plugin::NAME` 决定，本项目已改为 **工单提醒**。
- 目录名保留为 `Demo` 只是为了通过商店授权校验，**请勿改回 `TicketNotify` 之类的本地名**，否则启用会再次失败。

If you are on a build where local plugins *are* authorized, you can rename the directory freely and adjust namespaces accordingly.

## 目录结构

```
plugin/Demo/                   # 放到发卡系统 app/Plugin/ 下（目录名必须为 Demo）
├── Config/Info.php            # 插件信息（显示名「工单提醒」）
├── Config/Config.php          # 默认配置（含 API 地址 / 密钥 / 开关）
├── Config/Submit.php          # 后台配置表单
├── Hook/TicketNotify.php      # 工单钩子实现（本项目的核心）
├── Hook/Demo.php              # 商店插件原有的菜单钩子（保留，用于左侧菜单）
├── Controller/Demo.php        # 菜单页控制器
└── View/Menu.html, Demo.html  # 左侧菜单与说明页

flask/app.py                   # 配套 Flask 接收端（含订单 /recharge + 工单 /ticket）
```

## 工作原理

插件订阅两个钩子点位（在数据库事务提交后触发，钩子内的异常不会影响接口结果）：

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

1. 将 `plugin/Demo` 整个目录复制到发卡系统 `app/Plugin/` 下（**保持目录名为 `Demo`**）。
2. 修正属主与权限（站点一般以 `www` 运行）：
   ```bash
   chown -R www:www app/Plugin/Demo
   find app/Plugin/Demo -type d -exec chmod 755 {} +
   find app/Plugin/Demo -type f -exec chmod 644 {} +
   ```
3. 后台「插件」页面找到 **工单提醒**，点击启用，并在配置页填写：
   - **API 地址**：如 `http://127.0.0.1:8000/ticket`
   - **通信密钥**：与接收端约定的独立密钥（勿与订单插件共用）
   - 请求方式、附加参数、请求头（可选）、是否记录日志、事件开关
4. 保存配置。若之后修改了 `Hook/` 文件，需**先停用再启用**插件以重建钩子缓存。

## 配套 Flask 接收端

`flask/app.py` 基于原订单通知服务扩展，新增 `POST /ticket`：

- 使用独立密钥 `TICKET_KEY` 校验签名（与订单的 `RECHARGE_KEY` 分开）。
- 校验 `data.type == "ticket"`，非工单内容直接拒绝，避免与订单混流。
- 推送格式为工单专用样式（含工单号、标题、类型、优先级、状态、关联商品/订单、发送人、内容）。
- 对标题/发送人/内容做 HTML 清洗（去除富文本标签、转义实体），避免推送里出现 `<p>...</p>`。
- 日志写入 `ticket.txt`。

### 配置方式

敏感信息**不要写死在代码里**。`app.py` 的读取顺序是：**同目录的 `config.json` → 环境变量**。

推荐用 `config.json`（最简单，不用改 systemd）：

1. 在 `app.py` 同目录新建 `config.json`（已加入 `.gitignore`，**不要提交**）：

   ```json
   {
     "RECHARGE_KEY": "你的订单密钥",
     "TICKET_KEY": "你的工单密钥",
     "TG_BOT_TOKEN": "你的Bot Token",
     "TG_CHAT_ID": "你的Chat ID"
   }
   ```

2. 收紧权限（只有运行用户可读）：

   ```bash
   chmod 600 config.json
   ```

3. 启动：

   ```bash
   pip install flask requests
   python app.py            # 监听 0.0.0.0:8000
   ```

也可以改用环境变量（`config.json` 不存在时生效），适合 systemd `Environment=` 或容器部署：

```bash
export RECHARGE_KEY="你的订单密钥"
export TICKET_KEY="你的工单密钥"
export TG_BOT_TOKEN="你的Bot Token"
export TG_CHAT_ID="你的Chat ID"
```

| 键 | 说明 |
| --- | --- |
| `RECHARGE_KEY` | 订单接口 `/recharge` 的通信密钥（与订单插件一致） |
| `TICKET_KEY` | 工单接口 `/ticket` 的通信密钥（与本插件配置页里填的密钥一致） |
| `TG_BOT_TOKEN` | Telegram Bot Token |
| `TG_CHAT_ID` | Telegram 接收消息的 Chat ID |

> 修改 `config.json` 后需重启服务（Flask 的 `debug=True` 会自动重载，但生产环境请手动重启）。

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
