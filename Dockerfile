FROM node:22.22.2-alpine AS frontend-build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.30.4-alpine AS web

COPY deployment/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html
EXPOSE 80

FROM python:3.14.3-alpine AS api

WORKDIR /app
RUN apk upgrade --no-cache \
    && apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main 'sqlite-libs>=3.53.4-r0' \
    && adduser --disabled-password --uid 10001 app
COPY --chown=app:app scripts/api_server.py /app/scripts/api_server.py

USER app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=5001

EXPOSE 5001
CMD ["python", "scripts/api_server.py"]

FROM nginx:1.30.4-alpine AS portfolio

USER root
WORKDIR /app
RUN apk del --no-cache \
        nginx-module-acme \
        nginx-module-geoip \
        nginx-module-image-filter \
        nginx-module-njs \
        nginx-module-xslt \
    && apk upgrade --no-cache \
    && apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
        python3 \
        'sqlite-libs>=3.53.4-r0' \
    && mkdir -p /app/data/serving /tmp/client_body /tmp/proxy /tmp/fastcgi /tmp/uwsgi /tmp/scgi \
    && chown -R nginx:nginx /app /tmp/client_body /tmp/proxy /tmp/fastcgi /tmp/uwsgi /tmp/scgi
COPY --chown=nginx:nginx scripts/api_server.py /app/scripts/api_server.py
COPY --chown=nginx:nginx deployment/prepare_serving_cache.py /app/deployment/prepare_serving_cache.py
COPY --chown=nginx:nginx deployment/portfolio_supervisor.py /app/deployment/portfolio_supervisor.py
COPY --chown=nginx:nginx deployment/nginx.portfolio.conf.template /app/deployment/nginx.portfolio.conf.template
COPY --from=frontend-build --chown=nginx:nginx /app/dist /usr/share/nginx/html

USER nginx
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_PORT=5001 \
    PORT=10000

EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python3 -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '10000') + '/api/health', timeout=2)"
CMD ["python3", "deployment/portfolio_supervisor.py"]
