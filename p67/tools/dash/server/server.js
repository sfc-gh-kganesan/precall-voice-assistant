const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('node:path');
const https = require('node:https');
const http = require('node:http');

const app = express();
const PORT = process.env.PORT || 3001;
const P67_API_URL =
    process.env.P67_API_URL || 'http://controld.ghw6if.svc.spcs.internal:80';

console.log('Starting server with P67_API_URL:', P67_API_URL);

// Test connectivity on startup - use https for https URLs
const testUrl = new URL(P67_API_URL);
const httpModule = testUrl.protocol === 'https:' ? https : http;
const defaultPort = testUrl.protocol === 'https:' ? 443 : 80;
httpModule
    .get(
        {
            hostname: testUrl.hostname,
            port: testUrl.port || defaultPort,
            path: '/api/health',
            timeout: 5000,
        },
        (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () =>
                console.log(
                    'Connectivity test:',
                    res.statusCode,
                    data.substring(0, 200),
                ),
            );
        },
    )
    .on('error', (err) => {
        console.error('Connectivity test failed:', err.message);
    });

app.get('/health', (_req, res) => res.json({ status: 'healthy' }));

app.use((req, _res, next) => {
    console.log('Incoming request:', req.method, req.url);
    if (req.url.startsWith('/api')) {
        const hdrs = Object.keys(req.headers)
            .filter(
                (h) =>
                    h.startsWith('sf-') ||
                    h.startsWith('x-sf') ||
                    h === 'authorization' ||
                    h === 'cookie',
            )
            .join(', ');
        console.log('Auth-related headers:', hdrs || 'none');
    }
    next();
});

// http-proxy-middleware v3.x configuration
const apiProxy = createProxyMiddleware({
    target: P67_API_URL,
    changeOrigin: true,
    logger: console,
    pathRewrite: (pathStr, req) => {
        // When mounted at /api, req.url is stripped (e.g., /workflow/list)
        // req.originalUrl still has full path (e.g., /api/workflow/list)
        // We want to forward to target as /api/workflow/list
        console.log(
            'pathRewrite: pathStr=',
            pathStr,
            'req.url=',
            req.url,
            'req.originalUrl=',
            req.originalUrl,
        );
        return req.originalUrl; // Use the original URL with /api prefix
    },
    on: {
        proxyReq: (proxyReq, req) => {
            console.log(
                'Proxying:',
                req.method,
                req.originalUrl,
                '->',
                P67_API_URL + req.originalUrl,
            );
            const sfUser = req.headers['sf-context-current-user'];
            if (sfUser) {
                proxyReq.setHeader('sf-context-current-user', sfUser);
                console.log('SF user:', sfUser);
            }
            if (req.headers.authorization) {
                proxyReq.setHeader('Authorization', req.headers.authorization);
                console.log('Forwarding Authorization header');
            }
            if (req.headers.cookie) {
                proxyReq.setHeader('Cookie', req.headers.cookie);
                console.log('Forwarding Cookie header');
            }
            Object.keys(req.headers)
                .filter((h) => h.startsWith('sf-') || h.startsWith('x-sf'))
                .forEach((h) => {
                    proxyReq.setHeader(h, req.headers[h]);
                });
        },
        proxyRes: (proxyRes, req) => {
            console.log(
                'Proxy response:',
                proxyRes.statusCode,
                'for',
                req.originalUrl,
            );
        },
        error: (err, _req, res) => {
            console.error('Proxy error:', err.message, err.code);
            res.status(502).json({
                error: 'Proxy error',
                message: err.message,
                code: err.code,
            });
        },
    },
});

app.use('/api', apiProxy);

app.use(express.static(path.join(__dirname, 'dist')));

app.get('/{*splat}', (_req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => console.log(`Dashboard running on port ${PORT}`));
