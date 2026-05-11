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

### Уже реализовано в backend

- **Аутентификация JWT**: регистрация и вход, access-токен (срок по умолчанию 1 час) и refresh-токен (30 дней), хранение refresh-сессий в таблице `sessions`.
- **Выход (logout)**: отзыв refresh-сессии по телу запроса с `refresh_token`.
- **Защита маршрутов**: зависимости FastAPI (`get_current_user`, `require_admin`), заголовок `Authorization: Bearer <access_token>`.
- **Пароли**: хеширование **bcrypt** (напрямую через пакет `bcrypt`).
- **Документы (CRUD)**: загрузка **DOCX** и **TXT** (`multipart/form-data`); на диске **всегда сохраняется DOCX** (TXT конвертируется в минимальный DOCX по строкам → абзацы; загруженный DOCX хранится как есть). Извлечённый текст и `snapshot` — для редактора и дальнейшего форматирования СТП. Список с пагинацией и фильтром; `PUT` создаёт новые версии; удаление сносит каталог файлов. Доступ только владельцу (`404` для чужих id).
- **OpenRouter (этап 4.1)**: асинхронный клиент `app/services/openrouter_service.py` — `chat.completions`, таймаут, экспоненциальный **retry** при 429 / 5xx / сетевых ошибках; модель и лимиты из `.env`. Заготовки промптов в `app/prompts/`. Проверка ключа: `python scripts/verify_openrouter.py` из каталога `backend`.

## Технологический стек

### Backend

- FastAPI (Python 3.11+; локально проверялся также Python 3.13)
- PostgreSQL с типом JSONB
- SQLAlchemy с asyncpg
- JWT: `python-jose` (access / refresh), пароли: `bcrypt`
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
│   │   ├── api/      # API endpoints (v1: auth, admin, documents)
│   │   ├── core/     # Configuration, security (JWT, bcrypt)
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic-схемы запросов/ответов
│   │   ├── services/ # Бизнес-логика (auth, documents)
│   │   └── utils/    # Утилиты (хранилище файлов, извлечение текста)
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

Файл compose лежит в каталоге `docker/`, поэтому указывайте его явно (из корня `AutoSTP`):

```bash
# Клонирование репозитория
git clone <repository-url>
cd AutoSTP

# Запуск PostgreSQL и backend
docker compose --file docker/docker-compose.yml up -d

# Проверка статуса
docker compose --file docker/docker-compose.yml ps
```

Для старых установок Docker допустима команда `docker-compose` вместо `docker compose`.

После запуска сервисы будут доступны по адресам:

- Backend API: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs
- PostgreSQL: localhost:5432 (пользователь `autostp`, БД `autostp_db`, пароль см. `docker/docker-compose.yml`)
- Frontend в compose на этапе 1 не поднимается (будет добавлен позже)

### Переменные окружения backend

| Переменная | Назначение |
|------------|------------|
| `DATABASE_URL` | Строка подключения SQLAlchemy async, например `postgresql+asyncpg://autostp:autostp_password@localhost:5432/autostp_db` |
| `SECRET_KEY` | Секрет подписи JWT (в production задать надёжное значение) |
| `DEBUG` | `true` / `false` |
| `OPENROUTER_API_KEY` | Ключ [OpenRouter](https://openrouter.ai/) (совместим с OpenAI SDK, база `https://openrouter.ai/api/v1`) |
| `OPENROUTER_BASE_URL` | Обычно не менять |
| `OPENROUTER_MODEL` | Id модели, например `google/gemma-4-31b-it:free` |
| `OPENROUTER_TEMPERATURE`, `OPENROUTER_MAX_TOKENS` | Параметры генерации по умолчанию |
| `OPENROUTER_TIMEOUT_SECONDS` | Таймаут HTTP-запроса к API |
| `OPENROUTER_MAX_RETRIES`, `OPENROUTER_RETRY_BASE_SECONDS` | Число повторов и начальная задержка (экспоненциальный рост, потолок 60 с) |
| `OPENROUTER_HTTP_REFERER`, `OPENROUTER_APP_TITLE` | Опциональные заголовки для OpenRouter ([документация](https://openrouter.ai/docs)) |
| `UPLOAD_DIR` | Каталог для оригиналов загруженных документов (по умолчанию `./uploads`) |
| `MAX_UPLOAD_SIZE_MB` | Максимальный размер файла при загрузке (по умолчанию 30) |

Файл `.env` подхватывается из `backend/.env` или из **`AutoSTP/.env`** (оба пути в `Settings`). Сроки JWT и прочие параметры — в `app/core/config.py`. Интервал автосохранения на фронте: `AUTO_SAVE_INTERVAL_SECONDS`.

### API аутентификации (`/api/v1`)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/register` | Регистрация (роль по умолчанию `student`; пароль: ≥8 символов, заглавная, строчная, цифра) |
| POST | `/api/v1/auth/login` | Вход, в ответе `access_token` и `refresh_token` |
| POST | `/api/v1/auth/refresh` | Новая пара токенов по действительному `refresh_token` (ротация сессии в БД) |
| POST | `/api/v1/auth/logout` | Отзыв сессии по `refresh_token` (ответ `204 No Content`) |
| GET | `/api/v1/auth/me` | Профиль текущего пользователя (нужен `Authorization: Bearer`) |
| GET | `/api/v1/admin/ping` | Проверка роли администратора (`403`, если не `admin`) |

### API документов (`/api/v1/documents`)

Все запросы с заголовком `Authorization: Bearer <access_token>`.

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/documents/upload` | `multipart/form-data`: поле `file` (`.docx` / `.txt`), опционально `title`, `document_type` (`ku` / `di`). На диск пишется **только `.docx`** (TXT пересобирается через python-docx). В `metadata`: `original_filename`, `upload_extension`, `stored_filename`, `stored_file_format`, пути. |
| GET | `/api/v1/documents` | Список документов текущего пользователя. Query: `skip` (≥0), `limit` (1–100, по умолчанию 20), `title_contains` (подстрока в названии, без учёта регистра). В ответе `items`, `total`, `skip`, `limit`. |
| GET | `/api/v1/documents/{id}` | Полный объект документа, текущая версия (`current_version`), `versions_count`. |
| PUT | `/api/v1/documents/{id}` | JSON: `snapshot` (обязательный объект — JSON содержимого для редактора), опционально `title`. Создаётся новая версия (`v2`, …), обновляется `current_version_id`. |
| DELETE | `/api/v1/documents/{id}` | Удаление записи и каталога файлов на диске (`204`). |

Ошибки: `400` (формат / пустой файл), `401` (нет токена), `404` (нет документа или не ваш), `413` (превышен размер файла).

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

Тесты используют **отдельную базу** `autostp_test_db` на том же сервере PostgreSQL, что и основная `autostp_db`. Убедитесь, что Postgres запущен (например, через Docker), и **один раз создайте** тестовую БД:

```bash
docker exec autostp_postgres psql -U autostp -d postgres -c "CREATE DATABASE autostp_test_db;"
```

Если контейнер называется иначе, подставьте своё имя. При ошибке «уже существует» ничего делать не нужно.

В `tests/conftest.py` перед импортом приложения в `DATABASE_URL` имя базы `autostp_db` заменяется на `autostp_test_db`, чтобы и фикстура БД, и движок FastAPI в тестах использовали одну и ту же тестовую базу.

```bash
cd backend

# Виртуальное окружение (пример пути под Windows)
# ..\venv\Scripts\activate

pip install -r requirements.txt

# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=app --cov-report=html

# Только аутентификация
pytest tests/test_auth.py

# Только документы
pytest tests/test_documents.py

# Клиент OpenRouter (моки, без сети)
pytest tests/test_openrouter_service.py
```

Проверка реального ключа и модели (один короткий запрос к API):

```bash
cd backend
python scripts/verify_openrouter.py
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
