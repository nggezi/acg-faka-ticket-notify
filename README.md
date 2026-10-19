# acg-faka 工单提醒插件

异次元发卡系统（acg-faka）插件：当**用户创建工单**或**用户回复工单**时，自动将工单与消息内容带上 MD5 签名，POST 到站长自定义的 API 地址，用于推送到 Telegram 等渠道。

本仓库同时包含配套的 Flask 接收端示例（`flask/app.py`），可直接复用店内已有的订单通知服务，仅新增 `/ticket` 路由。

## 为什么插件目录叫 `Demo`（借壳机制）

> 这一段很关键，请先读完再安装。

### 现象

发卡系统（acg-faka）里，**纯本地手写的插件名无法启用**：在后台点「启用」会**静默失败**（状态仍是「未启用」）。而**从应用商店安装过的插件名**可以正常启用。

### 实测结论（控制变量）

在**同一环境、同一请求**下做对照，三个插件**代码内容完全相同**，唯一差异是「名字是否为本机已安装的商店插件」：

| 目录名 | 内容 | 名字是否为「已安装的商店插件」 | 启用结果 |
| --- | --- | --- | --- |
| `Demo` | 商店插件本体 | ✅ 是 | `STATUS 0 → 1` ✅ 钩子注册 |
| `DemoCopy` | 与 `Demo` 逐字节相同，仅改名 | ❌ 否 | `STATUS 0 → 0` ❌ |
| `Blog` | 与 `Demo` 相同 | ❌ 否（在商店目录里，但本机未安装） | `STATUS 0 → 0` ❌ |

**放行条件 = 插件名 ∈ 本机「已安装的商店插件」名单**。它看的**不是**文件内容，也**不是**「商店里有没有这个商品」，而是**你这台机器装没装过**。

> `kernel/Plugin.php` 是整个开源项目里**唯一的闭源文件**，其头部声明自述唯一用途为「应用商店插件授权校验，不含任何业务逻辑」，且**允许整文件删除**（删后应用商店与付费插件失效、其余照常）。本项目**未删除它**，因此需要借壳。

### 借壳的做法

**借用一个本机已安装、但你没在用的商店插件目录名**作为载体，把工单通知逻辑放进该目录的 `Hook/` 里。钩子注册是**整个 `Hook/` 目录扫描**的，系统会把我们新增的钩子类一并注册，后台「启用 / 停用」按钮能正常维护它。

- 后台列表显示的插件名由 `Config/Info.php` 的 `Plugin::NAME` 决定，本项目已改为 **工单提醒**。
- 目录名保留为 `Demo` 只是为了通过授权校验，**请勿改成 `TicketNotify` 之类的本地名**，否则启用会再次失败。

### 借壳的代价（务必知悉）

借壳**会顶掉该商店插件原有的功能**，因为同一个插件名只能对应一套 Hook。所以只能借**你确定不用的**名字。

- 本项目占用的是 `Demo`——它是商店里的**演示插件**（仅有后台菜单，无实际业务），因此**没有实际功能损失**。
- 想换壳：把本目录改名成另一个「已安装的商店插件名」并同步改命名空间即可（会顶掉那个插件）。
- 也可以在应用商店**免费安装几个用不到的小插件**，每个都成为一个新「壳位」。

### 一壳多逻辑：能装多个插件，但只有**一个总开关**

一个「壳」（插件名）下可以放**任意多个** Hook 类，各自订阅不同的钩子点，**同时生效**。本项目自身就是例子——`Demo/Hook/` 下同时有：

```
Demo/Hook/Demo.php         → 订阅 ADMIN_VIEW_MENU（后台菜单）
Demo/Hook/TicketNotify.php → 订阅 0x2100 / 0x2101（工单通知）
```

但**系统级的启用 / 停用粒度是「插件名」，不是「Hook 类」**：

- 后台**只列出插件名**（`Demo`，显示名「工单提醒」），**只有一个开关**，你点它 = 操作整个壳。
- **一开全开、一关全关**：关掉 `Demo` → 后台菜单和工单通知**一起失效**。
- 所有可见处（插件列表状态、左侧菜单入口）读的是**同一个 `STATUS`**，因此状态永远同步，不会出现「列表说启用、菜单却没出来」。

### 壳内单独控制某一部分

系统级做不到「单独停用某个 Hook 类」，但可以在**代码层**给各逻辑配自己的开关。本项目已经在用这个模式：

| 配置项 | 作用 |
| --- | --- |
| `notify_create` | 是否推「创建工单」通知 |
| `notify_reply` | 是否推「回复工单」通知 |

> 即：**一个壳 = 一个系统级总开关 + 每个逻辑自带的代码级小开关**。

If you are on a build **without** the licensing component (i.e. `kernel/Plugin.php` removed), local plugins work with any name, and you can rename the directory freely and adjust namespaces accordingly.

## 目录结构

```
plugin/Demo/                   # 放到发卡系统 app/Plugin/ 下（目录名必须是「已安装的商店插件名」）
├── Config/Info.php            # 插件信息（显示名「工单提醒」）
├── Config/Config.php          # 默认配置（含 API 地址 / 密钥 / 开关）
├── Config/Submit.php          # 后台配置表单
├── Hook/TicketNotify.php      # 工单钩子实现（本项目的核心）
├── Hook/Demo.php              # 商店插件原有的菜单钩子（保留，用于左侧菜单）
├── Controller/Demo.php        # 菜单页控制器
└── View/Menu.html, Demo.html  # 左侧菜单与说明页

flask/app.py                   # 配套 Flask 接收端（含订单 /recharge + 工单 /ticket）
```

> ⚠️ **借壳提醒**：本仓库目录名用 `Demo`，是因为 `Demo` 是「已安装的商店演示插件」。该目录一旦部署，会**顶掉原 Demo 插件**（原插件仅有一个后台菜单，无实际功能）。若你的机器上 `Demo` 另有用途，请把目录改成**另一个你已安装且不用的商店插件名**，并同步修改三个文件里的命名空间（`App\Plugin\Demo\...`）。

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

1. 将 `plugin/Demo` 整个目录复制到发卡系统 `app/Plugin/` 下（**目录名必须是本机已安装的商店插件名**，默认用 `Demo`；换名时同步改命名空间）。
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
