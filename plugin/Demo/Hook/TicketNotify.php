<?php
declare(strict_types=1);

namespace App\Plugin\Demo\Hook;

use App\Model\Ticket;
use App\Model\TicketMessage;
use App\Util\Http;
use App\Util\Plugin;
use App\Util\Str;
use Kernel\Annotation\Hook;

/**
 * 工单提醒（挂载于 Demo 插件身份下，以通过商店授权校验）
 */
class TicketNotify
{
    #[Hook(point: 0x2100)]
    public function OnCreate(Ticket $ticket, TicketMessage $message): void
    {
        $this->notify('create', $ticket, $message);
    }

    #[Hook(point: 0x2101)]
    public function OnReply(Ticket $ticket, TicketMessage $message): void
    {
        $this->notify('reply', $ticket, $message);
    }

    private function notify(string $event, Ticket $ticket, TicketMessage $message): void
    {
        $config = Plugin::getConfig("Demo");
        $isLog = isset($config['log']) && (bool)$config['log'];

        if ($event === 'create' && (!isset($config['notify_create']) || !(bool)$config['notify_create'])) {
            return;
        }
        if ($event === 'reply' && (!isset($config['notify_reply']) || !(bool)$config['notify_reply'])) {
            return;
        }

        $url = isset($config['url']) ? trim((string)$config['url']) : '';
        if ($url === '') {
            if ($isLog) {
                Plugin::log("Demo", "未配置 API 地址，跳过工单提醒（事件：{$event}）");
            }
            return;
        }

        try {
            if ($isLog) {
                Plugin::log("Demo", "捕获到工单事件：{$event}，工单号：{$ticket->ticket_no}，准备请求API：{$url}");
            }

            $headers = [];
            if (!empty($config['headers'])) {
                $decoded = json_decode((string)$config['headers'], true);
                if (is_array($decoded)) {
                    $headers = $decoded;
                }
            }

            $client = Http::make(['timeout' => 5, 'headers' => $headers]);

            $payload = [
                'type' => 'ticket',
                'event' => $event,
                'ticket' => $ticket->toArray(),
                'message' => $message->toArray(),
                'time' => date('Y-m-d H:i:s')
            ];

            $data = [
                'data' => json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
            ];

            if (!empty($config['param'])) {
                $param = json_decode((string)$config['param'], true);
                if (is_array($param)) {
                    foreach ($param as $k => $v) {
                        $data[$k] = $v;
                    }
                }
            }

            $data['sign'] = Str::generateSignature($data, (string)($config['key'] ?? ''));

            if ($isLog) {
                Plugin::log("Demo", "本地生成签名：" . $data['sign']);
            }

            if ((int)($config['request_type'] ?? 0) === 0) {
                $response = $client->post($url, ["form_params" => $data]);
            } else {
                $response = $client->get($url, ["query" => $data]);
            }

            if ($isLog) {
                Plugin::log("Demo", "请求完成，返回结果：" . $response->getBody()->getContents());
            }
        } catch (\Error | \Exception $e) {
            if ($isLog) {
                Plugin::log("Demo", "请求失败，错误原因：" . $e->getMessage());
            }
        }
    }
}
