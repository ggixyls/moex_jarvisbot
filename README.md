# RedOps Telegram Bot

Telegram-бот для автоматизации диагностики аутентификации и настройки АРМ на RedOS (хакатон Московская Биржа).

## Быстрый старт

### 1. Создайте бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather).
2. Команда `/newbot` → получите `BOT_TOKEN`.
3. Узнайте свой `user_id` через [@userinfobot](https://t.me/userinfobot).

### 2. Настройка окружения

```bash
cp .env.example .env
# Заполните BOT_TOKEN и WHITELIST_USER_IDS в .env
```

### 3. Установка зависимостей

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Запуск Kafka (локально)

```bashЫ
docker compose up -d zookeeper kafka
```

### 5. Запуск бота

```bash
python -m bot.main
```

Или всё через Docker:

```bash
docker compose up --build
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/help` | Справка |
| `/diagnose` | Диагностика аутентификации (FSM: username → domain) |
| `/setup` | Настройка АРМ (FSM: hostname, IP, маска, шлюз, DNS, домен, учётные данные) |
| `/status` | Статус активных запросов |

## Архитектура

```
Пользователь → Telegram Bot → Kafka (tg.requests) → Orchestrator → Kafka (worker.responses) → Bot → Пользователь
```

## Kafka-топики

- `tg.requests` — запросы от бота
- `worker.responses` — ответы от Orchestrator
- `worker.dlq` — dead letter queue (обрабатывается Orchestrator)

## Метрики Prometheus

Порт `9090`: `messages_received_total`, `kafka_publish_errors_total`, `response_latency_seconds`.

## Тесты

```bash
pytest
```
