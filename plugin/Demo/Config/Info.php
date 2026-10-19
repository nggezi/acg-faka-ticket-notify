<?php
declare(strict_types=1);

use App\Consts\Plugin;

return [
    Plugin::NAME => '工单提醒',
    Plugin::AUTHOR => 'opencode',
    Plugin::WEB_SITE => '#',
    Plugin::DESCRIPTION => '用户创建工单或回复工单后，带上工单与消息信息向你设置的API发送提醒请求。',
    Plugin::VERSION => '1.0.0'
];
