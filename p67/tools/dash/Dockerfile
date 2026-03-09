FROM node:20-alpine

WORKDIR /app

RUN npm install express http-proxy-middleware

COPY dist/ ./dist/
COPY server/server.js ./server.js

EXPOSE 3001

CMD ["node", "server.js"]
