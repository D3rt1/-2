# Контрольная работа №2 — FastAPI

## Структура
```
fastapi_kr2/
├── app.py            # Все задания в одном файле
├── requirements.txt
└── README.md
```

## Запуск
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Документация Swagger: http://127.0.0.1:8000/docs

---

## Задание 3.1 — POST /create_user
Создание пользователя с валидацией через Pydantic.

```bash
curl -X POST http://localhost:8000/create_user \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","age":30,"is_subscribed":true}'
```

---

## Задание 3.2 — Products

```bash
# Получить продукт по ID
curl http://localhost:8000/product/123

# Поиск продуктов
curl "http://localhost:8000/products/search?keyword=phone&category=Electronics&limit=5"
```

---

## Задание 5.1 — Cookie-аутентификация (plain UUID)

```bash
# Логин
curl -c cookies.txt -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user123","password":"password123"}'

# Получить профиль
curl -b cookies.txt http://localhost:8000/user

# Неверный токен
curl -b "session_token=invalid" http://localhost:8000/user
```

---

## Задание 5.2 — Подписанный cookie (itsdangerous)

```bash
curl -c cookies2.txt -X POST http://localhost:8000/login2 \
  -H "Content-Type: application/json" \
  -d '{"username":"user123","password":"password123"}'

curl -b cookies2.txt http://localhost:8000/profile
```

---

## Задание 5.3 — Динамическое время жизни сессии

```bash
curl -c cookies3.txt -X POST http://localhost:8000/login3 \
  -H "Content-Type: application/json" \
  -d '{"username":"user123","password":"password123"}'

curl -b cookies3.txt http://localhost:8000/profile3
```

Логика продления:
- < 3 мин с последней активности → кука НЕ обновляется
- 3–5 мин → кука обновляется (session_renewed: true в ответе)
- > 5 мин → 401 Session expired

---

## Задание 5.4 — Заголовки запроса

```bash
curl http://localhost:8000/headers \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  -H "Accept-Language: en-US,en;q=0.9,es;q=0.8"

# Ошибка — нет заголовка
curl http://localhost:8000/headers
```

---

## Задание 5.5 — CommonHeaders model + /info

```bash
curl http://localhost:8000/info \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  -H "Accept-Language: en-US,en;q=0.9,es;q=0.8" -v
```

В заголовках ответа будет `X-Server-Time`.
