# SRE Prep

Учебный SRE-проект на Python, демонстрирующий контейнеризацию, мониторинг, алертинг, CI и автоматизацию инфраструктуры.

## Архитектура

```text
Client
  |
  | localhost:8080
  v
Nginx :80
  |
  | app:8000
  v
Flask API
  |
  | redis:6379
  v
Redis

Prometheus :9090 ---> Flask /metrics
Grafana :3000 ------> Prometheus
```

В Docker Compose используются две сети:

- `frontend` - Nginx, Flask, Prometheus, Grafana.
- `backend` - Flask и Redis.

Redis не публикует порт на хосте. Flask доступен другим контейнерам через Docker DNS.

## Технологии

Python 3.12, Flask, Gunicorn, Redis, Nginx, Docker Compose, Prometheus, Grafana, pytest, GitHub Actions и Ansible.

## Требования

- Ubuntu 22.04/24.04 или совместимая Linux-среда
- Docker Engine
- Docker Compose V2
- Git
- Python 3 для локального запуска тестов

## Запуск

Клонировать репозиторий:

```bash
git clone https://github.com/am-i-right/sre_prep.git
cd sre_prep/compose-network-demo
```

Проверить конфигурацию:

```bash
docker compose config -q
```

Собрать и запустить:

```bash
docker compose up -d --build
```

Проверить сервисы:

```bash
docker compose ps
```

Посмотреть логи:

```bash
docker compose logs -f app
```

Остановить стек:

```bash
docker compose down
```

Не использовать `docker compose down -v` без необходимости: это удалит именованные volumes проекта, включая сохранённые данные.

## HTTP API

| Метод | Endpoint | Назначение |
|---|---|---|
| GET | `/` | Информация о сервисе |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness, проверка Redis |
| GET | `/counter` | Получение счётчика |
| POST | `/increment` | Увеличение счётчика |
| GET | `/metrics` | Метрики Prometheus, внутренний endpoint |
| GET | `/slow?seconds=1` | Учебная задержка |
| GET | `/lab/error` | Учебная HTTP 503 |

Последние два маршрута доступны только при `ENABLE_LAB_ENDPOINTS=true`.

Примеры:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/ready
curl http://127.0.0.1:8080/counter
curl -X POST http://127.0.0.1:8080/increment
```

`/metrics` намеренно не предоставляется через внешний Nginx. Prometheus обращается к Flask по внутреннему адресу `app:8000/metrics`.

## Мониторинг

Prometheus: `http://127.0.0.1:9090`

Grafana: `http://127.0.0.1:3000`

Основные метрики:

- `app_http_requests_total`
- `app_http_errors_total`
- `app_http_request_duration_seconds`
- `app_http_requests_in_progress`
- `app_redis_available`

Alert rules:

- `FlaskAppDown`
- `HighHttpErrorRate`
- `HighHttpLatency`

Если Docker работает в отдельной Ubuntu VM, для доступа к интерфейсам с Windows нужно использовать IP виртуальной машины и корректную публикацию портов либо SSH port forwarding.

## Тестирование

```bash
cd compose-network-demo/app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -v
```

## CI

GitHub Actions выполняет:

```text
push / pull_request
        |
        v
     pytest
        |
        v
   Docker build
```

Используются кеширование pip и Docker Buildx, а XML-отчёт pytest загружается как artifact.

## Автоматизация Ansible

Директория `ansible/` содержит inventory и playbook для настройки второй Ubuntu VM и развёртывания Nginx, Flask и Redis через Docker Compose.

Подробные команды запуска приведены в директории `ansible/`.

## Диагностика

Состояние контейнеров:

```bash
docker compose ps -a
```

Логи приложения:

```bash
docker compose logs --tail=100 app
```

Проверка Redis:

```bash
docker compose exec redis redis-cli ping
```

Проверка Prometheus:

```bash
curl http://127.0.0.1:9090/-/ready
```

Проект предназначен для учебной среды, а не для развёртывания в production без дополнительного усиления безопасности и отказоустойчивости.
