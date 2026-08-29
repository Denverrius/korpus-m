const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 3001;
const DATA_DIR = path.join(__dirname, '.data', 'orders');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Seed initial demo orders if empty
function seedInitialDataIfEmpty() {
    const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
    if (files.length > 0) return;

    const initialOrders = [
        {
            id: 'ORD-1001',
            number: 1001,
            createdAt: new Date(Date.now() - 4 * 24 * 3600 * 1000 + 11 * 3600 * 1000).toISOString(),
            name: 'Александр Ковалев',
            phone: '+7 (949) 312-44-55',
            date: '2026-08-30',
            time: '19:00',
            guests: 4,
            type: 'Ужин у камина',
            amount: 7500,
            source: 'Яндекс Карты',
            comment: 'Столик поближе к огню, будем праздновать годовщину',
            status: 'оплачено',
            tg_delivered: false
        },
        {
            id: 'ORD-1002',
            number: 1002,
            createdAt: new Date(Date.now() - 3 * 24 * 3600 * 1000 + 14 * 3600 * 1000).toISOString(),
            name: 'Елена Морозова',
            phone: '+7 (949) 554-11-22',
            date: '2026-08-31',
            time: '18:30',
            guests: 15,
            type: 'Банкет / День рождения',
            amount: 68000,
            source: 'Сайт',
            comment: 'Банкетное меню с мясными сетами и винной картой',
            status: 'согласование',
            tg_delivered: false
        },
        {
            id: 'ORD-1003',
            number: 1003,
            createdAt: new Date(Date.now() - 2 * 24 * 3600 * 1000 + 16 * 3600 * 1000).toISOString(),
            name: 'Дмитрий Власов',
            phone: '+7 (949) 712-88-99',
            date: '2026-08-29',
            time: '20:00',
            guests: 2,
            type: 'Романтический ужин',
            amount: 4800,
            source: 'Telegram',
            comment: 'Свечи и десерт с поздравлением',
            status: 'оплачено',
            tg_delivered: false
        },
        {
            id: 'ORD-1004',
            number: 1004,
            createdAt: new Date(Date.now() - 1 * 24 * 3600 * 1000 + 13 * 3600 * 1000).toISOString(),
            name: 'Ольга Васильева',
            phone: '+7 (949) 623-77-11',
            date: '2026-09-01',
            time: '17:00',
            guests: 6,
            type: 'Дегустация & Вино',
            amount: 14500,
            source: 'Рекомендации',
            comment: 'Сет авторских десертов и подбор французских вин',
            status: 'связались',
            tg_delivered: false
        },
        {
            id: 'ORD-1005',
            number: 1005,
            createdAt: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
            name: 'Сергей Попов',
            phone: '+7 (949) 490-33-88',
            date: '2026-08-29',
            time: '21:00',
            guests: 2,
            type: 'Столик на вечер',
            amount: 3500,
            source: 'Яндекс Карты',
            comment: 'Просто зарезервировать стол на двоих',
            status: 'новая',
            tg_delivered: false
        },
        {
            id: 'ORD-1006',
            number: 1006,
            createdAt: new Date(Date.now() - 1 * 3600 * 1000).toISOString(),
            name: 'Марина Громова',
            phone: '+7 (949) 811-90-40',
            date: '2026-09-05',
            time: '19:00',
            guests: 20,
            type: 'Корпоративный банкет',
            amount: 92000,
            source: 'Telegram',
            comment: 'Закрытие малого зала, индивидуальный расчет с шеф-поваром',
            status: 'новая',
            tg_delivered: false
        },
        {
            id: 'ORD-1007',
            number: 1007,
            createdAt: new Date(Date.now() - 5 * 24 * 3600 * 1000 + 19 * 3600 * 1000).toISOString(),
            name: 'Игорь Кравцов',
            phone: '+7 (949) 234-99-01',
            date: '2026-08-27',
            time: '18:00',
            guests: 2,
            type: 'Столик на вечер',
            amount: 3200,
            source: 'Сайт',
            comment: 'Отменил из-за переноса поездки',
            status: 'отказ',
            tg_delivered: false
        }
    ];

    initialOrders.forEach(ord => {
        const filePath = path.join(DATA_DIR, 'order_' + new Date(ord.createdAt).getTime() + '_' + ord.id + '.json');
        fs.writeFileSync(filePath, JSON.stringify(ord, null, 2), 'utf-8');
    });
}

seedInitialDataIfEmpty();

// Safe Mock Telegram sender fallback
async function dispatchTelegramNotification(order) {
    const token = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.TELEGRAM_CHAT_ID;

    if (!token || !chatId) {
        // Safe mode: No token provided, mark as not delivered without crashing
        return false;
    }

    try {
        const text = '🔔 Новая бронь в ресторане «На Бульваре»!\n' +
                     '№: #' + order.number + '\n' +
                     'Гость: ' + order.name + '\n' +
                     'Тел: ' + order.phone + '\n' +
                     'Дата/Время: ' + order.date + ' в ' + order.time + '\n' +
                     'Персон: ' + order.guests + '\n' +
                     'Формат: ' + order.type + '\n' +
                     'Сумма: ' + order.amount + ' ₽\n' +
                     'Источник: ' + order.source + '\n' +
                     'Пожелания: ' + (order.comment || '—');

        const res = await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: chatId,
                text: text,
                parse_mode: 'Markdown'
            })
        });
        return res.ok;
    } catch (err) {
        console.warn('[Telegram Dispatch Warning] Failed to send to telegram:', err.message);
        return false;
    }
}

// MIME types dictionary
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
    const pathname = parsedUrl.pathname;

    // Helper response functions
    const sendJson = (statusCode, data) => {
        res.writeHead(statusCode, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        });
        res.end(JSON.stringify(data));
    };

    // CORS preflight
    if (req.method === 'OPTIONS') {
        res.writeHead(204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        });
        return res.end();
    }

    // API: POST /api/lead (Submit reservation)
    if (pathname === '/api/lead' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body || '{}');

                if (!data.name || !data.phone) {
                    return sendJson(400, { error: 'Пожалуйста, укажите имя и номер телефона.' });
                }

                // Determine next order number
                const existingFiles = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
                const nextNum = 1000 + existingFiles.length + 1;
                const orderId = 'ORD-' + nextNum;
                const now = new Date();

                const order = {
                    id: orderId,
                    number: nextNum,
                    createdAt: now.toISOString(),
                    name: String(data.name).trim(),
                    phone: String(data.phone).trim(),
                    date: data.date || now.toISOString().split('T')[0],
                    time: data.time || '19:00',
                    guests: Number(data.guests) || 2,
                    type: data.type || 'Столик на вечер',
                    amount: Number(data.amount) || (data.type && data.type.includes('Банкет') ? 45000 : 3500),
                    source: data.source || 'Сайт',
                    comment: String(data.comment || '').trim(),
                    status: 'новая',
                    tg_delivered: false
                };

                // 1. Reliability first: save to local disk file
                const timestamp = now.getTime();
                const filename = 'order_' + timestamp + '_' + orderId + '.json';
                const filePath = path.join(DATA_DIR, filename);
                fs.writeFileSync(filePath, JSON.stringify(order, null, 2), 'utf-8');

                // 2. Safe Telegram notification dispatch
                const tgSuccess = await dispatchTelegramNotification(order);
                if (tgSuccess) {
                    order.tg_delivered = true;
                    fs.writeFileSync(filePath, JSON.stringify(order, null, 2), 'utf-8');
                }

                return sendJson(200, {
                    success: true,
                    message: 'Заявка на бронь успешно принята и сохранена!',
                    order: order
                });
            } catch (err) {
                console.error('Error handling /api/lead:', err);
                return sendJson(500, { error: 'Внутренняя ошибка сервера при обработке заявки.' });
            }
        });
        return;
    }

    // API: GET /api/crm/orders (List all orders)
    if (pathname === '/api/crm/orders' && req.method === 'GET') {
        try {
            const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
            const orders = files.map(file => {
                try {
                    const content = fs.readFileSync(path.join(DATA_DIR, file), 'utf-8');
                    return JSON.parse(content);
                } catch (e) {
                    return null;
                }
            }).filter(Boolean);

            // Sort newest first
            orders.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

            return sendJson(200, { success: true, orders });
        } catch (err) {
            console.error('Error reading orders:', err);
            return sendJson(500, { error: 'Не удалось прочитать список заявок.' });
        }
    }

    // API: PATCH /api/crm/orders/:id (Update status)
    if (pathname.startsWith('/api/crm/orders/') && req.method === 'PATCH') {
        const id = pathname.replace('/api/crm/orders/', '').trim();
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            try {
                const { status } = JSON.parse(body || '{}');
                const validStatuses = ['новая', 'связались', 'согласование', 'оплачено', 'отказ'];
                if (!validStatuses.includes(status)) {
                    return sendJson(400, { error: 'Недопустимый статус заявки.' });
                }

                const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
                let targetFile = null;
                let orderData = null;

                for (const file of files) {
                    try {
                        const content = fs.readFileSync(path.join(DATA_DIR, file), 'utf-8');
                        const parsed = JSON.parse(content);
                        if (parsed.id === id || String(parsed.number) === id) {
                            targetFile = path.join(DATA_DIR, file);
                            orderData = parsed;
                            break;
                        }
                    } catch (e) {}
                }

                if (!targetFile || !orderData) {
                    return sendJson(404, { error: 'Заявка с таким ID не найдена.' });
                }

                orderData.status = status;
                orderData.updatedAt = new Date().toISOString();
                fs.writeFileSync(targetFile, JSON.stringify(orderData, null, 2), 'utf-8');

                return sendJson(200, { success: true, order: orderData });
            } catch (err) {
                console.error('Error updating order:', err);
                return sendJson(500, { error: 'Ошибка обновления статуса заявки.' });
            }
        });
        return;
    }

    // API: GET /api/crm/stats (Analytics aggregation)
    if (pathname === '/api/crm/stats' && req.method === 'GET') {
        try {
            const files = fs.readdirSync(DATA_DIR).filter(f => f.endsWith('.json'));
            const orders = files.map(file => {
                try {
                    return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf-8'));
                } catch (e) {
                    return null;
                }
            }).filter(Boolean);

            const totalOrders = orders.length;
            const paidOrders = orders.filter(o => o.status === 'оплачено');
            const totalRevenue = orders.reduce((sum, o) => sum + (o.status !== 'отказ' ? (Number(o.amount) || 0) : 0), 0);
            const paidRevenue = paidOrders.reduce((sum, o) => sum + (Number(o.amount) || 0), 0);
            const conversionRate = totalOrders > 0 ? Math.round((paidOrders.length / totalOrders) * 100) : 0;
            const averageCheck = totalOrders > 0 ? Math.round(totalRevenue / (totalOrders - orders.filter(o => o.status === 'отказ').length || 1)) : 0;

            // Rating by Category/Type
            const typeMap = {};
            orders.forEach(o => {
                const t = o.type || 'Столик на вечер';
                if (!typeMap[t]) typeMap[t] = { count: 0, revenue: 0 };
                typeMap[t].count += 1;
                if (o.status !== 'отказ') typeMap[t].revenue += (Number(o.amount) || 0);
            });
            const byType = Object.keys(typeMap).map(k => ({
                name: k,
                count: typeMap[k].count,
                revenue: typeMap[k].revenue
            })).sort((a, b) => b.revenue - a.revenue);

            // Channel comparison
            const channelMap = {};
            orders.forEach(o => {
                const ch = o.source || 'Сайт';
                if (!channelMap[ch]) channelMap[ch] = { count: 0, revenue: 0 };
                channelMap[ch].count += 1;
                if (o.status !== 'отказ') channelMap[ch].revenue += (Number(o.amount) || 0);
            });
            const byChannel = Object.keys(channelMap).map(k => ({
                name: k,
                count: channelMap[k].count,
                revenue: channelMap[k].revenue
            })).sort((a, b) => b.count - a.count);

            // Status Funnel
            const funnel = {
                'новая': orders.filter(o => o.status === 'новая').length,
                'связались': orders.filter(o => o.status === 'связались').length,
                'согласование': orders.filter(o => o.status === 'согласование').length,
                'оплачено': orders.filter(o => o.status === 'оплачено').length,
                'отказ': orders.filter(o => o.status === 'отказ').length
            };

            // Heatmap by day of week (Пн-Вс) and hour (11:00 to 23:00)
            const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
            const hours = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23];
            const heatmap = {};

            days.forEach(d => {
                heatmap[d] = {};
                hours.forEach(h => { heatmap[d][h] = 0; });
            });

            orders.forEach(o => {
                const date = new Date(o.createdAt);
                const dayIndex = (date.getDay() + 6) % 7; // Convert 0=Sun to 0=Mon
                const dayName = days[dayIndex];
                const hour = date.getHours();
                const matchedHour = hours.find(h => h === hour) || 19;
                if (heatmap[dayName] && heatmap[dayName][matchedHour] !== undefined) {
                    heatmap[dayName][matchedHour] += 1;
                }
            });

            return sendJson(200, {
                success: true,
                kpi: {
                    totalOrders,
                    paidOrders: paidOrders.length,
                    conversionRate,
                    totalRevenue,
                    paidRevenue,
                    averageCheck
                },
                byType,
                byChannel,
                funnel,
                heatmap,
                days,
                hours
            });
        } catch (err) {
            console.error('Error computing stats:', err);
            return sendJson(500, { error: 'Ошибка подсчета аналитики.' });
        }
    }

    // Static Routes Routing
    const cleanPath = pathname.replace(/\/+$/, '') || '/';
    let filePath = '';
    if (cleanPath === '/' || cleanPath === '/index.html') {
        filePath = path.join(__dirname, 'index.html');
    } else if (cleanPath === '/crm' || cleanPath === '/crm.html') {
        filePath = path.join(__dirname, 'crm.html');
    } else if (cleanPath === '/crm/analytics' || cleanPath === '/analytics' || cleanPath === '/analytics.html') {
        filePath = path.join(__dirname, 'analytics.html');
    } else {
        filePath = path.join(__dirname, decodeURIComponent(pathname));
    }

    // Security check to avoid path traversal
    if (!filePath.startsWith(__dirname)) {
        res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
        return res.end('Forbidden');
    }

    fs.stat(filePath, (err, stats) => {
        if (err || !stats.isFile()) {
            res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
            return res.end('404 Not Found');
        }

        const ext = path.extname(filePath).toLowerCase();
        const contentType = MIME_TYPES[ext] || 'application/octet-stream';

        res.writeHead(200, { 'Content-Type': contentType });
        const stream = fs.createReadStream(filePath);
        stream.pipe(res);
    });
});

if (require.main === module) {
    server.listen(PORT, () => {
        console.log('=======================================================');
        console.log('🍽️  Ресторан «На Бульваре» успешно запущен!');
        console.log('🌐  Главная страница:   http://localhost:' + PORT);
        console.log('🔒  Скрытая CRM-панель: http://localhost:' + PORT + '/crm');
        console.log('📊  Дашборд аналитики:  http://localhost:' + PORT + '/crm/analytics');
        console.log('=======================================================');
    });
}

module.exports = { server, PORT, DATA_DIR };
