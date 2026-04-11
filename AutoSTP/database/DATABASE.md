# База данных AutoSTP

Один документ: схема, связь с DFD, запуск PostgreSQL, тесты ORM.

---

## 1. Соответствие DFD (уровень 1) и таблиц

| Хранилище DFD                     | Таблицы SQLAlchemy                                  |
| --------------------------------- | --------------------------------------------------- |
| **DB1** БД пользователей          | `roles`, `users`                                    |
| **DB2** БД документов             | `documents`, `document_versions`                    |
| **DB3** БД текстовых элементов    | `sections`, `text_elements`                         |
| **DB4** БД таблиц и изображений   | `document_tables`, `table_cells`, `document_images` |
| **DB5** БД подсказок              | `ai_suggestions`                                    |
| **DB6** БД логов                  | `audit_logs`                                        |
| Дополнительно (не на DFD, этап 1) | `templates`, `sessions`                             |

Процессы DFD (аутентификация, загрузка, сегментация, форматирование, редактирование, ИИ, экспорт) читают и пишут в эти таблицы; детальный поток данных см. в `DataFlowDiagramLevel0.png` / `DataFlowDiagramLevel1.png`.

---

## 2. Схема таблиц (ORM)

### 2.1 `roles`

| Поле        | Тип                | Описание                     |
| ----------- | ------------------ | ---------------------------- |
| id          | UUID PK            |                              |
| title       | VARCHAR(64) UNIQUE | Код роли: `student`, `admin` |
| description | TEXT NULL          |                              |

### 2.2 `users`

| Поле                   | Тип                 | Описание                             |
| ---------------------- | ------------------- | ------------------------------------ |
| id                     | UUID PK             |                                      |
| email                  | VARCHAR(255) UNIQUE |                                      |
| password_hash          | VARCHAR(255)        | Хеш пароля (bcrypt в сервисном слое) |
| full_name              | VARCHAR(255)        |                                      |
| role_id                | UUID FK → roles     |                                      |
| created_at, updated_at | TIMESTAMPTZ         |                                      |

### 2.3 `documents`

| Поле                   | Тип                                           | Описание                                                |
| ---------------------- | --------------------------------------------- | ------------------------------------------------------- |
| id                     | UUID PK                                       |                                                         |
| user_id                | UUID FK → users ON DELETE CASCADE             |                                                         |
| current_version_id     | UUID FK → document_versions NULL, `use_alter` | Указатель на актуальную версию                          |
| title                  | VARCHAR(512)                                  |                                                         |
| document_type          | VARCHAR(16)                                   | `ku` \| `di` (курсовая / диплом)                        |
| status                 | VARCHAR(16)                                   | `draft` \| `inpr` \| `com`                              |
| metadata               | JSONB NULL                                    | Произвольные метаданные (путь к файлу, страницы и т.д.) |
| created_at, updated_at | TIMESTAMPTZ                                   |                                                         |

### 2.4 `document_versions`

| Поле           | Тип                                   | Описание                              |
| -------------- | ------------------------------------- | ------------------------------------- |
| id             | UUID PK                               |                                       |
| document_id    | UUID FK → documents ON DELETE CASCADE |                                       |
| version_string | VARCHAR(64)                           | Версия, напр. `2026-04-11-v1`         |
| created_at     | TIMESTAMPTZ                           |                                       |
| snapshot       | JSONB NULL                            | Снимок структуры/состояния для отката |
| content_hash   | VARCHAR(128) NULL                     | Контроль целостности                  |

Связь «документ ↔ текущая версия» циклическая: при создании сначала вставляется `documents` без `current_version_id`, затем `document_versions`, затем обновляется `documents.current_version_id`.

### 2.5 `sections`

| Поле         | Тип                                   | Описание              |
| ------------ | ------------------------------------- | --------------------- |
| id           | UUID PK                               |                       |
| document_id  | UUID FK → documents ON DELETE CASCADE |                       |
| parent_id    | UUID FK → sections NULL               | Подразделы            |
| section_type | VARCHAR(64)                           | introduction, body, … |
| title        | VARCHAR(512)                          |                       |
| order_number | INTEGER                               | Порядок среди соседей |
| level        | INTEGER                               | Уровень вложенности   |

### 2.6 `text_elements`

| Поле         | Тип                                  | Описание                 |
| ------------ | ------------------------------------ | ------------------------ |
| id           | UUID PK                              |                          |
| section_id   | UUID FK → sections ON DELETE CASCADE |                          |
| element_type | VARCHAR(64)                          | paragraph, heading, …    |
| content      | TEXT                                 |                          |
| formatting   | JSONB NULL                           | Локальное форматирование |
| order_number | INTEGER                              |                          |

### 2.7 `document_tables` (класс ORM `DocumentTable`)

| Поле                        | Тип                | Описание               |
| --------------------------- | ------------------ | ---------------------- |
| id                          | UUID PK            |                        |
| section_id                  | UUID FK → sections |                        |
| caption                     | VARCHAR(512) NULL  |                        |
| table_number                | INTEGER NULL       |                        |
| order_number                | INTEGER            |                        |
| rows_number, columns_number | INTEGER            | Ожидаемый размер сетки |

### 2.8 `table_cells`

| Поле                    | Тип                                         | Описание |
| ----------------------- | ------------------------------------------- | -------- |
| id                      | UUID PK                                     |          |
| table_id                | UUID FK → document_tables ON DELETE CASCADE |          |
| is_header               | BOOLEAN                                     |          |
| row_index, column_index | INTEGER                                     |          |
| content                 | TEXT                                        |          |

### 2.9 `document_images` (класс ORM `DocumentImage`)

| Поле         | Тип                | Описание                        |
| ------------ | ------------------ | ------------------------------- |
| id           | UUID PK            |                                 |
| section_id   | UUID FK → sections |                                 |
| file_bytes   | BYTEA NULL         | Бинарные данные (как в draw.io) |
| caption, alt | VARCHAR(512) NULL  |                                 |
| image_number | INTEGER NULL       |                                 |
| order_number | INTEGER            |                                 |

### 2.10 `ai_suggestions`

| Поле            | Тип                | Описание |
| --------------- | ------------------ | -------- |
| id              | UUID PK            |          |
| section_id      | UUID FK → sections |          |
| suggestion_text | TEXT               |          |
| generated_at    | TIMESTAMPTZ        |          |

### 2.11 `bibliographic_references`

| Поле          | Тип                 | Описание       |
| ------------- | ------------------- | -------------- |
| id            | UUID PK             |                |
| document_id   | UUID FK → documents |                |
| reference_num | INTEGER NULL        | Номер в списке |
| source_title  | VARCHAR(1024) NULL  |                |
| authors       | TEXT NULL           |                |
| source_type   | VARCHAR(128) NULL   |                |
| source_link   | VARCHAR(2048) NULL  |                |
| order_number  | INTEGER             |                |

### 2.12 `citations`

| Поле                       | Тип                                | Описание              |
| -------------------------- | ---------------------------------- | --------------------- |
| id                         | UUID PK                            |                       |
| text_element_id            | UUID FK → text_elements            |                       |
| bibliographic_reference_id | UUID FK → bibliographic_references |                       |
| content                    | TEXT NULL                          | Текст ссылки в тексте |

### 2.13 `templates`, `sessions`, `audit_logs`

- **templates** — шаблоны оформления (системные / персональные), JSON правил.
- **sessions** — refresh-токены.
- **audit_logs** — действия пользователей: `action`, `log_msg`, `details` (JSONB), IP, user-agent, `timestamp`.

---

## 3. Файлы кода

| Модуль                                             | Назначение                                                                                                                    |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `app/models/role.py`                               | `Role`                                                                                                                        |
| `app/models/user.py`                               | `User`                                                                                                                        |
| `app/models/document.py`                           | `Document`, `DocumentVersion`, перечисления типа/статуса                                                                      |
| `app/models/document_content.py`                   | `Section`, `TextElement`, `DocumentTable`, `TableCell`, `DocumentImage`, `AISuggestion`, `BibliographicReference`, `Citation` |
| `app/models/template.py`, `session.py`, `audit.py` | как выше                                                                                                                      |
| `app/main.py`                                      | `create_all` при старте (lifespan)                                                                                            |
| `app/core/database.py`                             | `Base`, движок                                                                                                                |

---

## 4. Запуск PostgreSQL и создание тестовой БД

Строка подключения по умолчанию (см. `.env.example`):  
`postgresql+asyncpg://autostp:autostp_password@localhost:5432/autostp_db`

Тесты ожидают отдельную БД с тем же пользователем/паролем:

```sql
CREATE DATABASE autostp_test_db;
```

Через Docker (пример):

```bash
docker compose -f docker/docker-compose.yml up -d postgres
docker exec -it autostp_postgres psql -U autostp -d autostp_db -c "CREATE DATABASE autostp_test_db;"
```

Приложение при старте создаёт таблицы через `Base.metadata.create_all` (для разработки; для продакшена позже — Alembic).

---

## 5. Тесты

Каталог: `backend/tests/`.

Переменная окружения `DATABASE_URL` должна указывать на **основную** БД (`…/autostp_db`); фикстура сама подменяет имя на `autostp_test_db`.

```powershell
$env:DATABASE_URL="postgresql+asyncpg://autostp:autostp_password@127.0.0.1:5432/autostp_db"
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

Особенности `conftest.py`:

- `NullPool` у тестового движка — стабильная работа asyncpg + pytest-asyncio на Windows.
- Перед каждым тестом: `drop_all` + `create_all` на `autostp_test_db`.
- HTTP-клиент: `httpx.ASGITransport` + `AsyncClient` (импорт `app.models` до `from app.main import app as fastapi_app`, иначе имя `app` перезапишется пакетом `app`).

### Список тест-кейсов (`test_models.py`)

| Тест                                    | Проверка                                              |
| --------------------------------------- | ----------------------------------------------------- |
| `test_role_and_user`                    | Роли, пользователь, связь с `Role`                    |
| `test_document_version_current_pointer` | Документ, версия, `current_version_id`, `metadata`    |
| `test_section_hierarchy_and_content`    | Иерархия `Section`, `TextElement`                     |
| `test_table_and_cells`                  | `DocumentTable`, `TableCell`                          |
| `test_image_ai_suggestion`              | `DocumentImage`, `AISuggestion`                       |
| `test_bibliography_and_citation`        | `BibliographicReference`, `Citation`, загрузка связей |
| `test_template_session_audit`           | `Template`, `Session`, `AuditLog.log_msg`             |
| `test_cascade_delete_document`          | CASCADE при удалении документа                        |

`test_main.py` — smoke-тесты FastAPI (`/`, `/health`, 404).

---

## 6. Диаграммы

- Логическая структура и атрибуты сущностей: `database/DiplomaDatabase (2).drawio`.
- DFD: `DataFlowDiagramLevel0.png`, `DataFlowDiagramLevel1.png` (разместите в `database/` или рядом с отчётом по ТЗ).
- ER / IDEF1X: `ERDCrowsFoot.png`, `IDEF1X.png` — визуальное согласование с таблицами выше.

---

## 7. Результат прогона (пример)

Последний успешный прогон в среде разработки:

```text
tests/test_main.py ...
tests/test_models.py ........
11 passed
```

Требуется доступный PostgreSQL 16+ и созданная `autostp_test_db`.
