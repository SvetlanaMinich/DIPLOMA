# Этап 1: Фундамент архитектуры и инфраструктуры

## Обзор

Этап 1 создает базовую инфраструктуру проекта AutoSTP, включая структуру проекта, базу данных, конфигурации и Docker контейнеризацию. Это фундамент для всей системы.

## Содержание этапа

### 1. Структура проекта

Создан монорепозиторий со следующей структурой:

```
AutoSTP/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints (v1/)
│   │   ├── core/        # Configuration, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic (будет добавлено позже)
│   │   ├── utils/        # Utilities (будет добавлено позже)
│   │   └── main.py      # FastAPI application
│   ├── tests/            # Backend tests
│   ├── requirements.txt   # Python dependencies
│   └── pyproject.toml    # Code quality configuration
├── frontend/             # React frontend (будет добавлено в Этапе 3)
├── docker/              # Docker configurations
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docs/                # Documentation
├── .env.example         # Environment variables template
├── .gitignore
├── README.md
└── PLAN.md
```

### 2. Backend Infrastructure

#### Технологический стек

- **Python 3.11+** - основной язык разработки
- **FastAPI 0.109.0** - веб-фреймворк с асинхронной поддержкой
- **SQLAlchemy 2.0.25** - ORM с asyncpg для асинхронной работы с PostgreSQL
- **Pydantic 2.5.3** - валидация данных и настройки
- **Alembic 1.13.1** - миграции базы данных
- **Uvicorn** - ASGI сервер

#### Зависимости

Создан файл `requirements.txt` с основными зависимостями:

**Веб-сервер и фреймворк:**

- fastapi, uvicorn, gunicorn
- python-multipart (для загрузки файлов)

**База данных:**

- sqlalchemy, asyncpg, alembic

**Аутентификация и безопасность:**

- python-jose (JWT токены)
- passlib[bcrypt] (хеширование паролей)
- python-dotenv (переменные окружения)

**OpenRouter API:**

- openai (интеграция с LLM через OpenRouter)

**Обработка документов:**

- python-docx (DOCX файлы)
- PyPDF2 (PDF файлы)
- reportlab (генерация PDF)

**Тестирование:**

- pytest, pytest-asyncio, pytest-cov
- httpx (async HTTP клиент для тестов)

**Качество кода:**

- black (форматирование)
- flake8 (линтинг)
- mypy (type checking)
- isort (сортировка импортов)

#### Конфигурация

Создан модуль `app/core/config.py` с классом `Settings`:

**Настройки приложения:**

- APP_NAME, APP_VERSION, DEBUG
- HOST, PORT

**Настройки базы данных:**

- DATABASE_URL (PostgreSQL connection string)
- DATABASE_POOL_SIZE, DATABASE_MAX_OVERFLOW

**Безопасность:**

- SECRET_KEY (для JWT токенов)
- ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

**CORS:**

- CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS

**OpenRouter API:**

- OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_TEMPERATURE, OPENROUTER_MAX_TOKENS

**Хранилище файлов:**

- UPLOAD_DIR, MAX_UPLOAD_SIZE_MB, ALLOWED_FILE_EXTENSIONS

**Цены (BYN):**

- PRICING_DOCUMENT_SMALL_PAGES, PRICING_DOCUMENT_SMALL_PRICE
- PRICING_DOCUMENT_LARGE_PRICE, PRICING_TEMPLATE_PRICE

#### База данных

Создан модуль `app/core/database.py`:

- Асинхронный движок PostgreSQL
- Фабрика сессий
- Функция-зависимость `get_async_session()`

### 3. Модели данных

Созданы модели в `app/models/`:

#### User (`app/models/user.py`)

Поля:

- id (UUID, primary key)
- email (String, unique)
- hashed_password (String)
- role (Enum: USER, ADMIN)
- created_at, updated_at (DateTime)

Отношения:

- documents (один-ко-многим с Document)

#### Document (`app/models/document.py`)

Поля:

- id (UUID, primary key)
- user_id (UUID, foreign key to users)
- title (String)
- content_json (JSONB - структурированное содержимое)
- original_file_path (String)
- status (Enum: UPLOADED, SEGMENTED, FORMATTED, EXPORTED, ERROR)
- page_count (Integer)
- created_at, updated_at (DateTime)

Отношения:

- user (многие-к-одному с User)

#### Template (`app/models/template.py`)

Поля:

- id (UUID, primary key)
- user_id (UUID, foreign key to users, nullable для системных шаблонов)
- type (Enum: SYSTEM, PERSONAL)
- name (String)
- template_json (JSONB - правила форматирования)
- description (Text)
- created_at, updated_at (DateTime)

#### Session (`app/models/session.py`)

Поля:

- id (UUID, primary key)
- user_id (UUID, foreign key to users)
- refresh_token (String, unique)
- expires_at (DateTime)
- created_at (DateTime)

#### AuditLog (`app/models/audit.py`)

Поля:

- id (UUID, primary key)
- user_id (UUID, foreign key to users, nullable)
- action (Enum: LOGIN, LOGOUT, DOCUMENT_UPLOAD, DOCUMENT_DELETE, etc.)
- details (JSONB - детали действия)
- ip_address (String)
- user_agent (String)
- timestamp (DateTime)

### 4. FastAPI Application

Создан файл `app/main.py`:

**Lifespan контекст:**

- Создание таблиц базы данных при запуске
- Очистка при остановке

**CORS Middleware:**

- Настройка origins из конфигурации
- Разрешение credentials, methods, headers

**Endpoints:**

- GET `/` - информация о приложении
- GET `/health` - проверка работоспособности

**Глобальный обработчик исключений:**

- Перехват всех необработанных исключений
- Возврат 500 ошибки с деталями (в DEBUG режиме)

### 5. Docker Конфигурация

#### docker-compose.yml

Создан файл для оркестрации контейнеров:

**Services:**

1. **postgres**
   - Image: postgres:16-alpine
   - Environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
   - Volumes: postgres_data
   - Ports: 5432
   - Healthcheck: pg_isready

2. **backend**
   - Build: из Dockerfile.backend
   - Environment: DATABASE_URL, DEBUG, SECRET_KEY, OPENROUTER_API_KEY
   - Volumes: mount backend code для hot-reload, uploads
   - Ports: 8000
   - Depends on: postgres (healthcheck)
   - Command: uvicorn с --reload

3. **frontend** (закомментирован, будет добавлен в Этапе 3)
4. **nginx** (закомментирован, будет добавлен для продакшена)

**Volumes:**

- postgres_data
- uploads

**Networks:**

- autostp_network (bridge)

#### Dockerfile.backend

Многоступенчатый Dockerfile для оптимизации:

**Stage 1: Builder**

- Базовый образ: python:3.11-slim
- Установка build dependencies (gcc, postgresql-client)
- Установка Python зависимостей в /root/.local

**Stage 2: Runner**

- Базовый образ: python:3.11-slim
- Установка runtime dependencies
- Копирование .local из builder
- Копирование application code
- Создание пользователя appuser (UID 1000)
- Healthcheck: проверка /health endpoint
- CMD: uvicorn app.main:app

#### Dockerfile.frontend

Многоступенчатый Dockerfile для React:

**Stage 1: Builder**

- Базовый образ: node:18-alpine
- Установка зависимостей (npm ci)
- Копирование source code
- Build: npm run build

**Stage 2: Runner (Nginx)**

- Базовый образ: nginx:alpine
- Копирование build из builder
- Копирование nginx.conf
- Healthcheck: wget /index.html
- CMD: nginx

#### nginx.conf

Конфигурация Nginx для reverse proxy:

- Слушает порт 80
- Gzip compression
- Проксирование /api/ на backend:8000
- Кеширование /static/ (1 год)
- SPA fallback на /index.html

### 6. Тестирование

#### Конфигурация pytest

Создан файл `tests/conftest.py` с fixtures:

**Database fixtures:**

- `event_loop` - event loop для async тестов
- `setup_database` - создание таблиц до тестов, удаление после
- `db_session` - сессия базы данных для каждого теста с rollback

**HTTP client fixture:**

- `client` - AsyncClient для тестирования API

**Mock fixtures:**

- `mock_openai_client` - mock OpenRouter client (OpenAI-compatible)

**Data fixtures:**

- `sample_user_data` - пример данных пользователя
- `sample_document_data` - пример данных документа

#### Тесты

Созданы тесты в `tests/`:

**test_main.py:**

- `test_root_endpoint` - проверка корневого endpoint
- `test_health_check` - проверка health check
- `test_not_found` - проверка 404 ошибки

**test_models.py:**

- `test_create_user` - создание пользователя
- `test_user_repr` - проверка **repr**
- `test_create_document` - создание документа
- `test_document_status_enum` - проверка значений enum
- `test_create_template` - создание персонального шаблона
- `test_create_system_template` - создание системного шаблона
- `test_create_session` - создание сессии
- `test_create_audit_log` - создание audit log
- `test_user_documents_relationship` - проверка отношений User-Document

### 7. Качество кода

#### Black (форматирование)

Конфигурация в `pyproject.toml`:

- line-length: 100
- target-version: py311
- Исключение venv, .git, build и т.д.

#### isort (сортировка импортов)

Конфигурация в `pyproject.toml`:

- profile: black
- line_length: 100
- multi_line_output: 3
- include_trailing_comma: true

#### mypy (type checking)

Конфигурация в `pyproject.toml`:

- python_version: 3.11
- warn_return_any: true
- disallow_untyped_defs: true
- ignore_missing_imports: true

#### pytest (тестирование)

Конфигурация в `pyproject.toml`:

- minversion: 7.0
- testpaths: ["tests"]
- asyncio_mode: "auto"

#### Coverage (покрытие)

Конфигурация в `pyproject.toml`:

- source: ["app"]
- Исключение tests, venv, **init**.py

### 8. Документация

#### README.md

Создан корневой README с:

- Обзором проекта
- Основными возможностями
- Технологическим стеком
- Структурой проекта
- Быстрым стартом
- Инструкциями по локальной разработке
- Ссылками на документацию

#### .env.example

Создан шаблон переменных окружения с:

- Настройками приложения
- Database URL
- Secret key
- CORS origins
- OpenRouter API key
- Параметрами ценообразования

#### .gitignore

Создан .gitignore для Python и Node.js с:

- Python cache (**pycache**, \*.pyc)
- Virtual environments (venv, env, .venv)
- IDE (.idea, .vscode)
- Environment files (.env)
- Database files (_.db, _.sqlite)
- Logs (\*.log)
- Node modules
- Frontend build
- Testing artifacts

## Как использовать

### 1. Клонирование и настройка

```bash
cd AutoSTP

# Копирование шаблона переменных окружения
cp .env.example .env

# Редактирование .env (по желанию)
nano .env
```

### 2. Запуск с Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f backend

# Остановка
docker-compose down
```

### 3. Локальная разработка (без Docker)

#### Backend

```bash
cd backend

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Создание тестовой базы данных (PostgreSQL должен быть запущен)
createdb autostp_test_db

# Запуск в development режиме
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Тесты

```bash
cd backend

# Установка тестовых зависимостей
pip install -r requirements.txt

# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=app --cov-report=html

# Запуск с verbose выводом
pytest -v

# Запуск конкретного теста
pytest tests/test_main.py::test_root_endpoint
```

### 4. Доступ к сервисам

После запуска:

- Backend API: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs
- API Documentation (ReDoc): http://localhost:8000/redoc
- PostgreSQL: localhost:5432

### 5. Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# API Documentation (в браузере)
open http://localhost:8000/docs
```

## Проверки и валидация

### 1. Проверка структуры файлов

```bash
# Проверка структуры
tree -L 3 -I '__pycache__|node_modules|.git'
```

Ожидаемая структура:

```
AutoSTP/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── template.py
│   │   │   ├── session.py
│   │   │   └── audit.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_main.py
│   │   └── test_models.py
│   ├── requirements.txt
│   └── pyproject.toml
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docs/
│   └── STAGE_1_INFRASTRUCTURE.md
├── .env.example
├── .gitignore
├── README.md
└── PLAN.md
```

### 2. Проверка конфигураций

```bash
# Проверка синтаксиса Python
python -m py_compile backend/app/main.py
python -m py_compile backend/app/core/config.py
python -m py_compile backend/app/core/database.py
python -m py_compile backend/app/models/*.py

# Проверка синтаксиса Docker
docker-compose config

# Проверка синтаксиса pytest
python -m pytest backend/tests/ --collect-only
```

### 3. Запуск тестов

```bash
cd backend

# Все тесты
pytest

# С покрытием
pytest --cov=app --cov-report=term-missing

# С verbose
pytest -v

# С конкретным фильтром
pytest tests/test_models.py::test_create_user -v
```

Ожидаемый результат:

- Все тесты должны проходить
- Покрытие >80% для моделей
- Нет ошибок type checking

### 4. Проверка Docker контейнеров

```bash
# Сборка контейнеров
docker-compose build

# Запуск
docker-compose up -d

# Проверка статуса
docker-compose ps

# Логи
docker-compose logs backend

# Проверка health check
docker exec autostp_backend curl http://localhost:8000/health
```

Ожидаемый результат:

- Все контейнеры запущены
- Backend отвечает на /health
- PostgreSQL готов к соединению

### 5. Проверка качества кода

```bash
cd backend

# Форматирование (black)
black --check app/ tests/

# Сортировка импортов (isort)
isort --check-only app/ tests/

# Линтинг (flake8)
flake8 app/ tests/

# Type checking (mypy)
mypy app/
```

Ожидаемый результат:

- Нет ошибок форматирования
- Нет ошибок линтинга
- Нет ошибок type checking

## Требования

### Для локальной разработки

- **Python 3.11+**
- **PostgreSQL 16+** (или можно использовать Docker контейнер)
- **pip** (менеджер пакетов Python)
- **git** (система контроля версий)

### Для Docker развертывания

- **Docker 20.10+**
- **Docker Compose 2.0+**

### Опционально

- **PostgreSQL клиент** (psql) для прямого подключения к базе
- **Docker Desktop** (для удобной работы с контейнерами)

## Известные ограничения и замечания

1. **Frontend еще не реализован** - будет добавлен в Этапе 3
2. **Alembic миграции еще не созданы** - будут добавлены в Этапе 2
3. **Системный шаблон СТП еще не создан** - будет добавлен в Этапе 5
4. **OpenRouter API еще не интегрирован** - будет добавлен в Этапе 4
5. **Nginx для продакшена еще не настроен** - будет добавлен позже

## Следующие шаги

После завершения Этапа 1, переход к **Этапу 2: Система аутентификации и авторизации**:

1. Реализация API аутентификации (register, login)
2. Middleware авторизации (JWT проверка)
3. Обновление токенов (refresh)
4. Тесты аутентификации

## Дополнительные ресурсы

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Pytest Documentation](https://docs.pytest.org/)
