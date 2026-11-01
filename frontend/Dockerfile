FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Defaults target docker-compose; override on Cloud Run (see nginx.conf.template).
ENV BACKEND_URL=http://backend:8000 \
    BACKEND_HOST=backend \
    DNS_RESOLVER=127.0.0.11

EXPOSE 80
