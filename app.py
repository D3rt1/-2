from fastapi import FastAPI, Cookie, Request, HTTPException, Response, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, Annotated
from itsdangerous import URLSafeSerializer, BadSignature
import uuid
import time
import re
from datetime import datetime

app = FastAPI(title="Контрольная работа №2", version="1.0.0")

SECRET_KEY = "super-secret-key-kr2"
signer = URLSafeSerializer(SECRET_KEY)

# ─────────────────────────────────────────────
# Задание 3.1 — POST /create_user
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None
    is_subscribed: Optional[bool] = None

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("age must be a positive integer")
        return v

@app.post("/create_user", tags=["3.1 — Create User"])
def create_user(user: UserCreate):
    return user.model_dump()


# ─────────────────────────────────────────────
# Задание 3.2 — Products
# ─────────────────────────────────────────────

sample_product_1 = {"product_id": 123, "name": "Smartphone",  "category": "Electronics",  "price": 599.99}
sample_product_2 = {"product_id": 456, "name": "Phone Case",  "category": "Accessories",  "price": 19.99}
sample_product_3 = {"product_id": 789, "name": "Iphone",      "category": "Electronics",  "price": 1299.99}
sample_product_4 = {"product_id": 101, "name": "Headphones",  "category": "Accessories",  "price": 99.99}
sample_product_5 = {"product_id": 202, "name": "Smartwatch",  "category": "Electronics",  "price": 299.99}
sample_products  = [sample_product_1, sample_product_2, sample_product_3,
                    sample_product_4, sample_product_5]

@app.get("/products/search", tags=["3.2 — Products"])
def search_products(keyword: str, category: Optional[str] = None, limit: int = 10):
    results = []
    for p in sample_products:
        if keyword.lower() in p["name"].lower():
            if category is None or p["category"].lower() == category.lower():
                results.append(p)
    return results[:limit]

@app.get("/product/{product_id}", tags=["3.2 — Products"])
def get_product(product_id: int):
    for p in sample_products:
        if p["product_id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")


# ─────────────────────────────────────────────
# Задание 5.1 & 5.2 — Cookie auth (simple + signed)
# ─────────────────────────────────────────────

FAKE_USERS = {
    "user123": {"password": "password123", "username": "user123", "email": "user123@example.com"},
    "admin":   {"password": "admin123",    "username": "admin",   "email": "admin@example.com"},
}

# сессии: token -> username  (для задания 5.1 — plain UUID)
sessions_51: dict[str, str] = {}

class LoginData(BaseModel):
    username: str
    password: str

@app.post("/login", tags=["5.1 — Cookie auth"])
def login(data: LoginData, response: Response):
    user = FAKE_USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = str(uuid.uuid4())
    sessions_51[token] = data.username
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=1800)
    return {"message": "Login successful", "session_token": token}

@app.get("/user", tags=["5.1 — Cookie auth"])
def get_user(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if not session_token or session_token not in sessions_51:
        response.status_code = 401
        return {"message": "Unauthorized"}
    username = sessions_51[session_token]
    user = FAKE_USERS[username]
    return {"username": user["username"], "email": user["email"]}


# ─────────────────────────────────────────────
# Задание 5.2 — Signed cookie  /login2  /profile
# ─────────────────────────────────────────────

# user_id map: username -> uuid
user_ids: dict[str, str] = {u: str(uuid.uuid4()) for u in FAKE_USERS}

@app.post("/login2", tags=["5.2 — Signed cookie"])
def login2(data: LoginData, response: Response):
    user = FAKE_USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = user_ids[data.username]
    signed_token = signer.dumps(user_id)          # <user_id>.<signature>
    response.set_cookie(key="session_token", value=signed_token,
                        httponly=True, max_age=1800)
    return {"message": "Login successful", "session_token": signed_token}

@app.get("/profile", tags=["5.2 — Signed cookie"])
def profile(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if not session_token:
        response.status_code = 401
        return {"message": "Unauthorized"}
    try:
        user_id = signer.loads(session_token)
    except BadSignature:
        response.status_code = 401
        return {"message": "Unauthorized"}

    # найти пользователя по user_id
    username = next((u for u, uid in user_ids.items() if uid == user_id), None)
    if not username:
        response.status_code = 401
        return {"message": "Unauthorized"}

    user = FAKE_USERS[username]
    return {"user_id": user_id, "username": user["username"], "email": user["email"]}


# ─────────────────────────────────────────────
# Задание 5.3 — Dynamic session lifetime
# ─────────────────────────────────────────────

SESSION_LIFETIME   = 300   # 5 минут
SESSION_RENEW_FROM = 180   # >= 3 минуты → продлять

def _make_token_53(user_id: str, timestamp: float) -> str:
    payload = f"{user_id}.{int(timestamp)}"
    signature = signer.dumps(payload)
    return signature  # itsdangerous хранит payload+sig вместе

def _parse_token_53(token: str):
    """Возвращает (user_id, timestamp) или поднимает исключение."""
    try:
        payload: str = signer.loads(token)
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")
    parts = payload.split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid session")
    return parts[0], int(parts[1])

@app.post("/login3", tags=["5.3 — Dynamic session"])
def login3(data: LoginData, response: Response):
    user = FAKE_USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id  = user_ids[data.username]
    now      = time.time()
    token    = _make_token_53(user_id, now)
    response.set_cookie(key="session_token", value=token,
                        httponly=True, secure=False, max_age=SESSION_LIFETIME)
    return {"message": "Login successful"}

@app.get("/profile3", tags=["5.3 — Dynamic session"])
def profile3(response: Response, session_token: Optional[str] = Cookie(default=None)):
    if not session_token:
        response.status_code = 401
        return {"message": "Session expired"}

    user_id, last_active = _parse_token_53(session_token)
    now     = time.time()
    elapsed = now - last_active

    if elapsed >= SESSION_LIFETIME:
        response.status_code = 401
        response.delete_cookie("session_token")
        return {"message": "Session expired"}

    # найти пользователя
    username = next((u for u, uid in user_ids.items() if uid == user_id), None)
    if not username:
        response.status_code = 401
        return {"message": "Invalid session"}

    user = FAKE_USERS[username]
    result = {"user_id": user_id, "username": user["username"], "email": user["email"]}

    # обновить куки если >= 3 и < 5 минут
    if SESSION_RENEW_FROM <= elapsed < SESSION_LIFETIME:
        new_token = _make_token_53(user_id, now)
        response.set_cookie(key="session_token", value=new_token,
                            httponly=True, secure=False, max_age=SESSION_LIFETIME)
        result["session_renewed"] = True

    return result


# ─────────────────────────────────────────────
# Задание 5.4 — Request headers
# ─────────────────────────────────────────────

ACCEPT_LANG_RE = re.compile(
    r'^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})?(,[a-zA-Z\-]{1,10}(;q=\d(\.\d)?)?)*$'
)

@app.get("/headers", tags=["5.4 & 5.5 — Headers"])
def get_headers(request: Request):
    user_agent      = request.headers.get("user-agent")
    accept_language = request.headers.get("accept-language")

    if not user_agent:
        raise HTTPException(status_code=400, detail="Missing User-Agent header")
    if not accept_language:
        raise HTTPException(status_code=400, detail="Missing Accept-Language header")
    if not ACCEPT_LANG_RE.match(accept_language):
        raise HTTPException(status_code=400, detail="Invalid Accept-Language format")

    return {"User-Agent": user_agent, "Accept-Language": accept_language}


# ─────────────────────────────────────────────
# Задание 5.5 — CommonHeaders model + /info
# ─────────────────────────────────────────────

from fastapi import Header

class CommonHeaders(BaseModel):
    user_agent:      str = ""
    accept_language: str = ""

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def check_required(cls, values):
        if not values.get("user_agent"):
            raise ValueError("User-Agent header is required")
        if not values.get("accept_language"):
            raise ValueError("Accept-Language header is required")
        al = values.get("accept_language", "")
        if not ACCEPT_LANG_RE.match(al):
            raise ValueError("Invalid Accept-Language format")
        return values

def common_headers(
    user_agent:      str = Header(..., alias="user-agent"),
    accept_language: str = Header(..., alias="accept-language"),
) -> CommonHeaders:
    return CommonHeaders(user_agent=user_agent, accept_language=accept_language)

@app.get("/headers", tags=["5.4 & 5.5 — Headers"], include_in_schema=False)
def get_headers_v2(headers: Annotated[CommonHeaders, Depends(common_headers)]):
    return {"User-Agent": headers.user_agent, "Accept-Language": headers.accept_language}

@app.get("/info", tags=["5.4 & 5.5 — Headers"])
def get_info(
    response: Response,
    headers:  Annotated[CommonHeaders, Depends(common_headers)],
):
    response.headers["X-Server-Time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent":      headers.user_agent,
            "Accept-Language": headers.accept_language,
        },
    }
