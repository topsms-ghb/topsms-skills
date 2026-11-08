<?php
// Send one SMS with the TopSMS REST API (PHP 7.4+ with ext-curl).
// For a full client use the library: composer require topsms/topsms-php
//
// Usage:
//   export TOPSMS_CLIENT_ID=...  TOPSMS_SECRET=...   # use a TEST key while developing
//   php send_sms.php +4915112345678 "Your order 1024 has shipped."

function topsms_send(string $to, string $text, ?string $from = null): array
{
    $base = rtrim(getenv('TOPSMS_BASE_URL') ?: 'https://www.topsms.cz', '/');
    $body = ['to' => $to, 'text' => $text];
    if ($from !== null) {
        $body['from'] = $from;
    }
    $ch = curl_init($base . '/api/sms/send');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . getenv('TOPSMS_CLIENT_ID') . ':' . getenv('TOPSMS_SECRET'),
            'Content-Type: application/json',
            'Idempotency-Key: ' . bin2hex(random_bytes(16)), // reuse the same key when retrying
        ],
        CURLOPT_POSTFIELDS => json_encode($body, JSON_UNESCAPED_UNICODE),
    ]);
    $raw = curl_exec($ch);
    if ($raw === false) {
        throw new RuntimeException('Network error: ' . curl_error($ch));
    }
    $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
    $data = json_decode($raw, true) ?: [];
    if ($status >= 400) {
        throw new RuntimeException("TopSMS $status " . ($data['code'] ?? '') . ': ' . ($data['error'] ?? 'error'));
    }
    return $data;
}

if (PHP_SAPI === 'cli' && realpath($argv[0]) === __FILE__) {
    if ($argc < 3) {
        fwrite(STDERR, "Usage: php send_sms.php <+E164 number> \"<text>\"\n");
        exit(2);
    }
    try {
        echo json_encode(topsms_send($argv[1], $argv[2]), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), "\n";
    } catch (RuntimeException $e) {
        fwrite(STDERR, $e->getMessage() . "\n");
        exit(1);
    }
}
