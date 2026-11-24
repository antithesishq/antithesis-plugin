# JavaScript, instrumented by Antithesis from /opt/antithesis/catalog.
FROM node:22-slim
WORKDIR /app
COPY package.json worker.js ./
RUN npm install --omit=dev --no-audit --no-fund && mkdir -p /opt/antithesis && ln -s /app /opt/antithesis/catalog
CMD ["node", "/app/worker.js"]
