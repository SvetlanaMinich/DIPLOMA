# Быстрый старт для проверки Этапа 1

Этот документ поможет вам быстро проверить, что инфраструктура Этапа 1 работает корректно.

## Предварительные требования

- Docker и Docker Compose установлены
- Git (опционально)

## Шаг 1: Клонирование и настройка

```bash
# Перейти в директорию проекта
cd c:\sem7\практика-преддиплом\диплом\AutoSTP

# Проверить структуру
dir /s /b backend\app
```

Ожидаемый вывод:

```
backend\app\__init__.py
backend\app\api\__init__.py
backend\app\api\v1\__init__.py
backend\app\core\__init__.py
backend\app\core\config.py
backend\app\core\database.py
backend\app\models\__init__.py
backend\app\models\audit.py
backend\app\models\document.py
backend\app\models\session.py
backend\app\models\template.py
backend\app\models\user.py
backend\app\main.py
```

## Шаг 2: Настройка переменных окружения

```bash
# Копировать шаблон .env
copy .env.example .env

# Проверить содержимое (опционально)
type .env
```

## Шаг 3: Запуск с Docker

```bash
ocker-compose --file docker\docker-compose.yml up -d --build
docker-compose ps
```

Ожидаемый статус:

```
NAME              STATUS              PORTS
autostp_backend   Up (healthy)       0.0.0.0:8000->8000/tcp
autostp_postgres  Up (healthy)       0.0.0.0:5432->5432/tcp
```

## Шаг 4: Проверка работоспособности

```bash
curl http://localhost:8000/health
start http://localhost:8000/docs
```

Ожидаемый ответ от /health:

```json
{ "status": "healthy" }
```

## Шаг 5: Проверка базы данных

```bash
# Подключиться к PostgreSQL через Docker
docker exec -it autostp_postgres psql -U autostp -d autostp_db

# В psql выполнить:
\dt

# Ожидаемый вывод:
#                   List of relations
#  Schema |           Name           | Type  |  Owner
# --------+--------------------------+-------+----------
#  public | audit_logs              | table | autostp
#  public | documents               | table | autostp
#  public | sessions                | table | autostp
#  public | templates               | table | autostp
#  public | users                   | table | autostp

# Выйти из psql
\q
```

## Шаг 6: Проверка логов

```bash
# Просмотр логов backend
docker-compose --file docker\docker-compose.yml logs backend

# Следить за логами в реальном времени
docker-compose logs -f backend
```

## Шаг 7: Запуск тестов (локально)

```bash
# Установить Python зависимости локально
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Запустить тесты
pytest -v

# С покрытием
pytest --cov=app --cov-report=term-missing
```

Ожидаемый вывод тестов:

```
tests/test_main.py::test_root_endpoint PASSED
tests/test_main.py::test_health_check PASSED
tests/test_main.py::test_not_found PASSED
tests/test_models.py::test_create_user PASSED
tests/test_models.py::test_user_repr PASSED
tests/test_models.py::test_create_document PASSED
tests/test_models.py::test_document_status_enum PASSED
tests/test_models.py::test_create_template PASSED
tests/test_models.py::test_create_system_template PASSED
tests/test_models.py::test_create_session PASSED
tests/test_models.py::test_create_audit_log PASSED
tests/test_models.py::test_user_documents_relationship PASSED

YYY passed in X.XXs
```
