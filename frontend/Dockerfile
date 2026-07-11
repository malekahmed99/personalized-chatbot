# =========================================================
# frontend/Dockerfile
# =========================================================

# --- مرحلة 1: البناء ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
# الناتج: /app/dist (ملفات static: html/js/css)

# --- مرحلة 2: التشغيل ---
# بعد الـ build، مش محتاجين Node تاني - Nginx خفيف جداً (~40MB)
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/ || exit 1
