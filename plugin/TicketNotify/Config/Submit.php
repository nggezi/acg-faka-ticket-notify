<?php
declare (strict_types=1);

return [
    [
        "title" => "请求方式",
        "name" => "request_type",
        "type" => "select",
        "dict" => [
            ["id" => 0, "name" => "POST"],
            ["id" => 1, "name" => "GET"]
        ],
        "default" => 0,
        "placeholder" => "请选择"
    ],
    [
        "title" => "通信密钥",
        "name" => "key",
        "type" => "input",
        "placeholder" => "工单接口独立密钥，与订单接口的 key 请分开设置",
        "default" => \App\Util\Str::generateRandStr(16)
    ],
    [
        "title" => "签名方式",
        "name" => "sign_type",
        "type" => "select",
        "dict" => [
            ["id" => 0, "name" => "MD5"]
        ],
        "default" => 0,
        "placeholder" => "请选择"
    ],
    [
        "title" => "签名说明",
        "name" => "explain2",
        "type" => "explain",
        "placeholder" => "签名算法详见/app/Util/Str.php类中的generateSignature方法。"
    ],
    [
        "title" => "API地址",
        "name" => "url",
        "type" => "input",
        "placeholder" => "请输入API地址"
    ],
    [
        "title" => "记录日志",
        "name" => "log",
        "type" => "switch",
        "text" => "开启"
    ],
    [
        "title" => "附加头",
        "name" => "headers",
        "type" => "json"
    ],
    [
        "title" => "附加参数",
        "name" => "param",
        "type" => "json"
    ],
    [
        "title" => "用户创建工单时提醒",
        "name" => "notify_create",
        "type" => "switch",
        "text" => "开启"
    ],
    [
        "title" => "用户回复工单时提醒",
        "name" => "notify_reply",
        "type" => "switch",
        "text" => "开启"
    ],
    [
        "title" => "说明",
        "name" => "explain3",
        "type" => "explain",
        "placeholder" => "本插件启用后，用户创建工单或回复工单时，将工单信息与消息内容发送至你填写的API。\n\n与订单通知插件相互独立：请使用单独的API地址（如 /ticket）与单独的通信密钥。\n\nPOST方式：以 form_params 提交，字段 data 为 JSON 字符串，sign 为签名，另含附加参数。\nGET方式：以 query 提交相同字段。\n\ndata 结构：{\"type\":\"ticket\",\"event\":\"create|reply\",\"ticket\":{...},\"message\":{...},\"time\":\"...\"}\n其中 type 固定为 ticket，用于与订单通知 (type=order) 区分。"
    ],
];
