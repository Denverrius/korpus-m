const http = require('http');
const assert = require('assert');
const { server } = require('../server');

const TEST_PORT = 3998;

function runRequest(options, postData) {
    return new Promise((resolve, reject) => {
        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => { data += chunk; });
            res.on('end', () => {
                resolve({ status: res.statusCode, headers: res.headers, body: data });
            });
        });
        req.on('error', reject);
        if (postData) req.write(postData);
        req.end();
    });
}

async function runTests() {
    console.log('Testing Korpus M Complete System...\n');
    let passed = 0;
    await new Promise(r => server.listen(TEST_PORT, r));

    try {
        // 1. GET /
        const res1 = await runRequest({ hostname: 'localhost', port: TEST_PORT, path: '/', method: 'GET' });
        assert.strictEqual(res1.status, 200);
        console.log('  PASS: GET / serves index.html');
        passed++;

        // 2. GET /crm
        const res2 = await runRequest({ hostname: 'localhost', port: TEST_PORT, path: '/crm', method: 'GET' });
        assert.strictEqual(res2.status, 200);
        console.log('  PASS: GET /crm serves CRM dashboard');
        passed++;

        // 3. GET /crm/analytics
        const res3 = await runRequest({ hostname: 'localhost', port: TEST_PORT, path: '/crm/analytics', method: 'GET' });
        assert.strictEqual(res3.status, 200);
        console.log('  PASS: GET /crm/analytics serves Analytics dashboard');
        passed++;

        // 4. POST /api/lead
        const payload = JSON.stringify({
            name: 'Иван Кузнецов (Тест)',
            phone: '+7 (949) 710-52-78',
            type: 'Кухня на заказ (МДФ Эмаль)',
            amount: 220000,
            address: 'пр. Мира, 84',
            source: 'Сайт (Калькулятор стоимости)'
        });
        const res4 = await runRequest({
            hostname: 'localhost',
            port: TEST_PORT,
            path: '/api/lead',
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
        }, payload);
        assert.strictEqual(res4.status, 200);
        const json4 = JSON.parse(res4.body);
        assert.strictEqual(json4.success, true);
        console.log('  PASS: POST /api/lead persists lead to server database');
        passed++;

        // 5. GET /api/crm/orders
        const res5 = await runRequest({ hostname: 'localhost', port: TEST_PORT, path: '/api/crm/orders', method: 'GET' });
        assert.strictEqual(res5.status, 200);
        const json5 = JSON.parse(res5.body);
        assert.ok(Array.isArray(json5.orders));
        assert.ok(json5.orders.length >= 200);
        console.log('  PASS: GET /api/crm/orders returns full orders list');
        passed++;

        // 6. PATCH /api/crm/orders/:id
        const patchPayload = JSON.stringify({ status: 'оплачено' });
        const res6 = await runRequest({
            hostname: 'localhost',
            port: TEST_PORT,
            path: '/api/crm/orders/' + json4.order.id,
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(patchPayload) }
        }, patchPayload);
        assert.strictEqual(res6.status, 200);
        console.log('  PASS: PATCH /api/crm/orders/:id updates status to "оплачено"');
        passed++;

        // 7. GET /api/crm/stats
        const res7 = await runRequest({ hostname: 'localhost', port: TEST_PORT, path: '/api/crm/stats', method: 'GET' });
        assert.strictEqual(res7.status, 200);
        const json7 = JSON.parse(res7.body);
        assert.ok(json7.kpi.totalOrders > 0);
        assert.ok(json7.heatmap);
        console.log('  PASS: GET /api/crm/stats returns complete aggregated metrics');
        passed++;

        console.log('\n========================================');
        console.log('Results: ' + passed + ' passed, 0 failed.');
        console.log('========================================\n');
    } finally {
        server.close();
    }
}

if (require.main === module) {
    runTests().catch(err => { console.error('Test error:', err); process.exit(1); });
}
