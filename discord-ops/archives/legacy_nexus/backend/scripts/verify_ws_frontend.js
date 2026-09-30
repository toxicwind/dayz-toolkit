const WebSocket = require('ws');

const WS_URL = 'ws://localhost:19101/ws/logs';

console.log(`[TEST] Connecting to ${WS_URL}...`);
const ws = new WebSocket(WS_URL);

ws.on('open', function open() {
    console.log('[TEST] ✅ Connected to WebSocket');

    // Wait for a message or timeout
    setTimeout(() => {
        console.log('[TEST] no message received after 5s (expected if quiet)');
        process.exit(0);
    }, 5000);
});

ws.on('message', function incoming(data) {
    console.log('[TEST] 📩 Message Received:', data.toString());
    try {
        const json = JSON.parse(data);
        if (json.level === 'combat' || json.type === 'killfeed.kill') {
            console.log('      -> ✅ Combat Event Detected!');
        }
    } catch (e) {
        console.log('      -> ⚠️ Non-JSON message');
    }
});

ws.on('error', function error(err) {
    console.error('[TEST] ❌ WebSocket Error:', err.message);
    process.exit(1);
});
