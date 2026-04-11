# AutoSTP - Автоматическое форматирование курсовых и дипломных работ

Веб-платформа для автоматизации оформления курсовых и дипломных работ студентов БГУИР в соответствии со стандартами СТП 01-2024.

## Обзор проекта

AutoSTP принимает неоформленный текстовый документ и формирует полностью отформатированный документ, готовый к сдаче, используя языковые модели для семантической сегментации и декларативные шаблоны для форматирования.

## Основные возможности

- Автоматическая семантическая сегментация документов
- Форматирование по стандартам СТП 01-2024 БГУИР
- Интерактивный редактор с визуальным отображением
- Генерация подсказок по дополнению контента на базе LLM
- Экспорт в форматы PDF и DOCX
- Загрузка персональных шаблонов оформления
- Транзакционная модель оплаты

## Технологический стек

### Backend

- FastAPI (Python 3.11+)
- PostgreSQL с типом JSONB
- SQLAlchemy с asyncpg
- OpenRouter API (LLaMA 3 8B, GPT-4o и другие модели)

### Frontend

- React 18 с TypeScript
- Slate.js для редактора
- PDF.js для предпросмотра

### Infrastructure

- Docker + Docker Compose
- Nginx (reverse proxy)
- Let's Encrypt (HTTPS)

## Структура проекта

```
AutoSTP/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── core/     # Configuration, security
│   │   ├── models/   # SQLAlchemy models
│   │   ├── services/ # Business logic
│   │   └── utils/    # Utilities
│   ├── tests/        # Backend tests
│   └── requirements.txt
├── frontend/         # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── public/
│   └── package.json
├── docker/          # Docker configurations
├── docs/            # Documentation
├── .gitignore
└── README.md
```

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Node.js 18+ (для локальной разработки)

### Запуск с Docker

```bash
# Клонирование репозитория
git clone <repository-url>
cd AutoSTP

# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps
```

После запуска сервисы будут доступны по адресам:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs
- PostgreSQL: localhost:5432

### Локальная разработка

#### Backend

```bash
cd backend

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск в development режиме
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск development сервера
npm start
```

## Тестирование

### Backend тесты

```bash
cd backend

# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=app --cov-report=html

# Запуск конкретного тестового файла
pytest tests/test_api.py
```

### Frontend тесты

```bash
cd frontend

# Запуск всех тестов
npm test

# Запуск с покрытием
npm test -- --coverage
```

## Документация

- [План разработки](PLAN.md) — план реализации
- [База данных: схема, запуск, тесты](database/DATABASE.md) — единый документ по PostgreSQL и ORM
