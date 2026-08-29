/**
 * KorpusM — Мебельное производство (Мариуполь)
 * Standalone Backend Server & REST API
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 3001;
const DATA_DIR = path.join(__dirname, '.data', 'orders');

if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Safe Telegram Dispatcher
async function dispatchTelegramNotification(order) {
    const token = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.TELEGRAM_CHAT_ID;
    if (!token || !chatId) return false;

    try {
        const text = '🪵 *Новая заявка на мебель • Корпус М (Мариуполь)*\n' +
                     '📋 *Заказ:* #' + (order.id || order.number) + '\n' +
                     '👤 *Клиент:* ' + order.name + '\n' +
                     '📞 *Тел:* ' + order.phone + '\n' +
                     '📍 *Адрес:* ' + (order.address || 'Мариуполь') + '\n' +
                     '🪑 *Изделие:* ' + order.type + '\n' +
                     '🔩 *Материалы:* ' + (order.material || 'По согласованию') + '\n' +
                     '💰 *Оценка:* ' + (Number(order.amount)||0).toLocaleString('ru-RU') + ' ₽\n' +
                     '🌐 *Источник:* ' + order.source + '\n' +
                     '💬 *Заметка:* ' + (order.comment || '—');

        const res = await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' })
        });
        return res.ok;
    } catch (e) {
        console.warn('Telegram notification warning:', e.message);
        return false;
    }
}

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

const server = http.createServer(async (req, res) => {
    const parsedUrl = url.parse(req.url, true);
    let pathname = parsedUrl.pathname;

    const sendJson = (statusCode, data) => {
        res.writeHead(statusCode, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        });
        res.end(JSON.stringify(data));
    };

    if (req.method === 'OPTIONS') {
        res.writeHead(204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        });
        return res.end();
    }

    // POST /api/lead
    if (pathname === '/api/lead' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body || '{}');
                if (!data.name || !data.phone) {
                    return sendJson(400, { error: 'Укажите имя и номер телефона.' });
                }

                const existingFiles = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
                const nextNum = 1000 + existingFiles.length + 1;
                const orderId = 'KM-' + nextNum;
                const now = new Date();

                const order = {
                    id: orderId,
                    number: nextNum,
                    createdAt: now.toISOString(),
                    name: String(data.name).trim(),
                    phone: String(data.phone).trim(),
                    address: String(data.address || 'г. Мариуполь').trim(),
                    date: data.date || now.toISOString().split('T')[0],
                    time: data.time || '10:00',
                    type: data.type || 'Кухня на заказ (МДФ Эмаль)',
                    material: data.material || 'ЛДСП Egger + Фурнитура Blum',
                    amount: Number(data.amount) || 165000,
                    source: data.source || 'Сайт (Калькулятор)',
                    comment: String(data.comment || '').trim(),
                    status: 'новая',
                    tg_delivered: false
                };

                const filename = 'order_' + now.getTime() + '_' + orderId + '.json';
                const filePath = path.join(DATA_DIR, filename);
                fs.writeFileSync(filePath, JSON.stringify(order, null, 2), 'utf-8');

                const tgOk = await dispatchTelegramNotification(order);
                if (tgOk) {
                    order.tg_delivered = true;
                    fs.writeFileSync(filePath, JSON.stringify(order, null, 2), 'utf-8');
                }

                return sendJson(200, { success: true, message: 'Заявка принята!', order });
            } catch (err) {
                return sendJson(500, { error: 'Ошибка сервера при сохранении заявки.' });
            }
        });
        return;
    }

    // GET /api/crm/orders
    if (pathname === '/api/crm/orders' && req.method === 'GET') {
        try {
            const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
            const list = files.map(f => {
                try { return JSON.parse(fs.readFileSync(path.join(DATA_DIR, f), 'utf-8')); }
                catch(e) { return null; }
            }).filter(Boolean);

            list.sort((a, b) => new Date(b.createdAt || b.date) - new Date(a.createdAt || a.date));
            return sendJson(200, { success: true, orders: list });
        } catch (err) {
            return sendJson(500, { error: 'Не удалось прочитать заказы.' });
        }
    }

    // PATCH /api/crm/orders/:id
    if (pathname.startsWith('/api/crm/orders/') && req.method === 'PATCH') {
        const orderId = pathname.replace('/api/crm/orders/', '').trim();
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            try {
                const patchData = JSON.parse(body || '{}');
                const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
                let foundFile = null;
                let orderObj = null;

                for (const f of files) {
                    try {
                        const content = JSON.parse(fs.readFileSync(path.join(DATA_DIR, f), 'utf-8'));
                        if (content.id === orderId || String(content.number) === orderId) {
                            foundFile = f;
                            orderObj = content;
                            break;
                        }
                    } catch(e) {}
                }

                if (!foundFile || !orderObj) {
                    return sendJson(404, { error: 'Заказ #' + orderId + ' не найден.' });
                }

                if (patchData.status) orderObj.status = patchData.status;
                if (patchData.comment) orderObj.comment = patchData.comment;

                fs.writeFileSync(path.join(DATA_DIR, foundFile), JSON.stringify(orderObj, null, 2), 'utf-8');
                return sendJson(200, { success: true, order: orderObj });
            } catch (err) {
                return sendJson(500, { error: 'Ошибка обновления заказа.' });
            }
        });
        return;
    }

    // GET /api/crm/stats
    if (pathname === '/api/crm/stats' && req.method === 'GET') {
        try {
            const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
            const list = files.map(f => {
                try { return JSON.parse(fs.readFileSync(path.join(DATA_DIR, f), 'utf-8')); }
                catch(e) { return null; }
            }).filter(Boolean);

            let inShop = 0;
            let inFunnel = 0;
            let completed = 0;
            let rejected = 0;
            let completedRevenue = 0;
            let inShopRevenue = 0;
            const categories = {};
            const sources = {};
            const materials = {};
            const heatmap = {};

            const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
            days.forEach(d => {
                heatmap[d] = {};
                for (let h = 9; h <= 21; h++) heatmap[d][h] = 0;
            });

            list.forEach(o => {
                const amt = Number(o.amount) || 0;
                const st = (o.status || '').toLowerCase();

                if (st.includes('цех')) {
                    inShop++;
                    inShopRevenue += amt;
                } else if (st.includes('сдан') || st.includes('оплач') || st.includes('договор')) {
                    completed++;
                    completedRevenue += amt;
                } else if (st.includes('отказ')) {
                    rejected++;
                } else {
                    inFunnel++;
                }

                const cat = o.type || 'Корпусная мебель';
                if (!categories[cat]) categories[cat] = { count: 0, revenue: 0 };
                categories[cat].count++;
                categories[cat].revenue += amt;

                const src = o.source || 'Сайт';
                sources[src] = (sources[src] || 0) + 1;

                const mat = o.material || 'ЛДСП Egger + Blum';
                materials[mat] = (materials[mat] || 0) + 1;

                const dt = new Date(o.createdAt || o.date);
                let dayIdx = dt.getDay();
                const dayMap = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
                const dayName = dayMap[dayIdx];
                let hour = dt.getHours();
                if (hour >= 9 && hour <= 21 && heatmap[dayName]) {
                    heatmap[dayName][hour] = (heatmap[dayName][hour] || 0) + 1;
                }
            });

            const avgCheck = (completed + inShop) > 0 ? Math.round((completedRevenue + inShopRevenue) / (completed + inShop)) : 165000;

            return sendJson(200, {
                success: true,
                kpi: {
                    totalOrders: list.length,
                    inShop,
                    inFunnel,
                    completed,
                    rejected,
                    completedRevenue,
                    inShopRevenue,
                    avgCheck
                },
                categories,
                sources,
                materials,
                heatmap
            });
        } catch (err) {
            return sendJson(500, { error: 'Ошибка расчета аналитики.' });
        }
    }

    // Static Files
    let filePath = path.join(__dirname, pathname);
    if (pathname === '/' || pathname === '') filePath = path.join(__dirname, 'index.html');
    else if (pathname === '/crm' || pathname === '/crm/') filePath = path.join(__dirname, 'crm.html');
    else if (pathname === '/crm/analytics' || pathname === '/crm/analytics/' || pathname === '/analytics') filePath = path.join(__dirname, 'analytics.html');
    else if (pathname === '/gallery' || pathname === '/gallery/') filePath = path.join(__dirname, 'gallery.html');

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
                return res.end('<h1>404 — Страница не найдена</h1>');
            }
            res.writeHead(500);
            return res.end('Server Error: ' + err.code);
        }
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content, 'utf-8');
    });
});

if (require.main === module) {
    server.listen(PORT, () => {
        console.log('🪵 KorpusM Server listening on http://localhost:' + PORT);
        console.log('📋 CRM:       http://localhost:' + PORT + '/crm');
        console.log('📊 Analytics: http://localhost:' + PORT + '/crm/analytics');
    });
}

module.exports = { server };
