FROM node:22-alpine AS frontend-build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS web

COPY deployment/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html
EXPOSE 80

FROM python:3.14-slim AS api

WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app scripts/api_server.py /app/scripts/api_server.py

USER app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=5001

EXPOSE 5001
CMD ["python", "scripts/api_server.py"]
