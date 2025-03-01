from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.models import SessionLocal, User, engine
from pydantic import BaseModel
import asyncio
import requests
import time
import logging
from typing import List
import random
import string
from datetime import datetime
import time
from datetime import datetime, timedelta
from pydantic import BaseModel

class LoginRequest(BaseModel):
    nickname_or_email: str
    password: str

class UserCreate(BaseModel):
    nickname: str
    email: str
    password: str
    referral_code: str = None

last_fetch_time = datetime.now()  # ініціалізація змінної
cached_prices = {}  # ініціалізація змінної для кешування цін

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class Account(BaseModel):
    email: str
    password: str
    referralCode: str = None

class Position(BaseModel):
    trade_type: str
    entry_price: float
    quantity: float
    leverage: int
    stop_loss: float = None
    take_profit: float = None

open_positions: List[Position] = []
spot_balance = 200.0
futures_balance = 0
user_balance = spot_balance + futures_balance

# Функція для генерації випадкового рядка з літерами та цифрами
def generate_random_string(length=6):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

# Підключення до бази даних
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/login")
async def login(login_request: LoginRequest):
    db = SessionLocal()
    user = db.query(User).filter(
        (User.nickname == login_request.nickname_or_email) | (User.email == login_request.nickname_or_email),
        User.password == login_request.password
    ).first()
    db.close()

    if user:
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=400, detail="Невірний нікнейм/електронна пошта або пароль")
    
@app.post("/save-account")
async def save_account(user: UserCreate):
    db = SessionLocal()
    db_user = User(nickname=user.nickname, email=user.email, password=user.password, referral_code=user.referral_code)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return {"message": "Account created successfully"}
# Реєстрація користувача
@app.post("/register")
async def register(account: Account, db: Session = Depends(get_db)):
    own_referral_code = generate_random_string()
    new_user = User(email=account.email, password=account.password, referral_code=account.referralCode, own_referral_code=own_referral_code)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Registration successful", "email": new_user.email, "referralCode": new_user.referral_code, "ownReferralCode": new_user.own_referral_code}

# Логінізація користувача
@app.post("/login")
async def login(account: Account, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == account.email, User.password == account.password).first()
    if user:
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=400, detail="Invalid email or password")

# Отримання реферального коду
@app.post("/ownReferalcode")
async def ownReferalcode(db: Session = Depends(get_db)):
    random_string = generate_random_string()
    return {"ownReferralCode": random_string}

# Депозит криптовалюти
@app.post("/depositCrypto")
async def depositCrypto(db: Session = Depends(get_db)):
    random_string = generate_random_string()
    return {"depositCrypto": random_string}

# Сторінка аккаунту
@app.post("/account")
async def get_futures_page(request: Request):
    return templates.TemplateResponse("account.html", {"request": request, "balance": user_balance})

# Виведення криптовалюти
@app.post("/withdrawCrypto")
async def withdrawCrypto(db: Session = Depends(get_db)):
    return {"withdrawCrypto": "ok"}

# Купівля на споті
@app.post("/buy-spot")
async def buy_spot(db: Session = Depends(get_db)):  
    return {"buy-spot": "success"}

# Продаж на споті
@app.post("/sell-spot")
async def sell_spot(db: Session = Depends(get_db)):
    return {"sell-spot": "success"}

# Вихід з акаунту
@app.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}

# Створення акаунту
@app.post("/create-account")
async def create_account(account: Account):
    db = SessionLocal()
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"message": "Account created successfully"}

# Оновлення акаунту
@app.post("/update-account")
async def update_account(account: Account):
    db = SessionLocal()
    user = db.query(User).filter(User.email == account.email).first()
    if user:
        user.name = account.name
        user.email = account.email
        user.password = account.password
        db.commit()
        db.refresh(user)
        return {"message": "Account updated successfully"}
    return {"message": "Account not found"}

# Видалення акаунту
@app.post("/delete-account")
async def delete_account(account: Account):
    db = SessionLocal()
    user = db.query(User).filter(User.email == account.email).first()
    if user:
        db.delete(user)
        db.commit()
        return {"message": "Account deleted successfully"}
    return {"message": "Account not found"}

# Збереження акаунту
@app.post("/save-account")
async def save_account(account: Account):
    logger.info(f"Received account data: {account}")
    response = {
        "message": "Account successfully created",
        "email": account.email,
        "password": account.password,
        "referralCode": account.referralCode if account.referralCode else None,
        "ownReferralCode": account.referralCode,
        "depositCrypto": depositCrypto()
    }
    return response

# Сторінка ф'ючерсів
@app.get("/futures")
async def get_futures_page(request: Request):
    return templates.TemplateResponse("futures.html", {"request": request, "balance": user_balance})    

# Сторінка фінансів
@app.get("/finance")
async def get_main_page(request: Request):
    return templates.TemplateResponse("finance.html", {"request": request, "balance": user_balance})

# Сторінка SPOT
@app.get("/SPOT")
async def get_index_page(request: Request):
    return templates.TemplateResponse("spot.html", {"request": request})

# Головна сторінка
@app.get("/")
async def get_main_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

# Сторінка реєстрації
@app.get("/register")
async def get_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Сторінка логінізації
@app.get("/login")
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Функція для отримання цін криптовалют
last_fetch_time = time.time()  # Або datetime.now()
cached_prices = {}

async def get_crypto_prices():
    global last_fetch_time, cached_prices
    current_time = time.time()

    # Перевірка, чи минуло більше 10 секунд з останнього запиту
    if current_time - last_fetch_time < 10:
        return cached_prices

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "TONUSDT", "BNBUSDT", "XRPUSDT", "TRUMPUSDT"]
    prices = {}

    for symbol in symbols:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        params = {"symbol": symbol}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if "lastPrice" in data and "priceChangePercent" in data:
                prices[symbol] = {
                    "price": format_price(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"])  # Зміна ціни за 24 години у відсотках
                }
            else:
                logger.error(f"Error: Missing data for {symbol} in API response.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Error processing the response for {symbol}: {e}")

    if prices:
        cached_prices = prices
        last_fetch_time = current_time

    return prices if prices else {"Error": "Failed to retrieve prices"}



# Форматування ціни
def format_price(price):
    return "{:,.2f}".format(float(price))

# Розрахунок PnL
def calculate_pnl(position: Position, current_price: float):
    if position.trade_type == "long":
        pnl = (current_price - position.entry_price) * position.quantity * position.leverage
    else:
        pnl = (position.entry_price - current_price) * position.quantity * position.leverage
    return pnl

# Розрахунок ціни ліквідації
def calculate_liquidation_price(position: Position):
    if position.trade_type == "long":
        liquidation_price = position.entry_price * (1 - 1 / position.leverage)
    else:
        liquidation_price = position.entry_price * (1 + 1 / position.leverage)
    return liquidation_price

# WebSocket для головної сторінки
@app.websocket("/ws")
async def websocket_index(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            prices = await get_crypto_prices()
            await websocket.send_json(prices)
            await asyncio.sleep(7)
        except WebSocketDisconnect:
            print("Client disconnected from index")
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(7)

# WebSocket для основних монет
@app.websocket("/ws/main")
async def websocket_main(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            prices = await get_crypto_prices()
            main_prices = {key: prices[key] for key in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"] if key in prices}
            await websocket.send_json(main_prices)
            await asyncio.sleep(7)
        except WebSocketDisconnect:
            print("Client disconnected from main")
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(7)

# WebSocket для ф'ючерсів
@app.websocket("/ws/futures")
async def websocket_futures(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            prices = await get_crypto_prices()
            await websocket.send_json(prices)
            await asyncio.sleep(7)

            for index, position in enumerate(open_positions):
                if position.stop_loss and prices["BTCUSDT"] <= position.stop_loss:
                    await close_position(index, position.stop_loss, websocket)
                elif position.take_profit and prices["BTCUSDT"] >= position.take_profit:
                    await close_position(index, position.take_profit, websocket)

        except WebSocketDisconnect:
            logger.info("Client disconnected from futures")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            await asyncio.sleep(7)

# Закриття позиції
async def close_position(index: int, close_price: float, websocket: WebSocket):
    global user_balance
    position = open_positions.pop(index)
    pnl = calculate_pnl(position, close_price)
    initial_capital = position.entry_price * position.quantity
    user_balance += (initial_capital + pnl) * 0.999
    await websocket.send_json({"message": "Trade closed automatically", "balance": user_balance})
    logger.info(f"Trade closed automatically. New balance: {user_balance}")


# Створення позиції
@app.post("/trade")
async def place_trade(position: Position):
    global user_balance
    logger.info(f"Received trade request: {position}")

    max_quantity = user_balance / position.entry_price
    if position.quantity > max_quantity:
        raise HTTPException(status_code=400, detail=f"Недостатньо коштів. Максимальна кількість: {max_quantity:.6f} BTC")

    user_balance -= position.entry_price * position.quantity
    open_positions.append(position)
    logger.info(f"Trade placed successfully. New balance: {user_balance}")
    return {"message": "Trade placed successfully", "balance": user_balance}

# Закриття позиції
@app.post("/close_trade")
async def close_trade(request: Request):
    global user_balance
    data = await request.json()
    index = data.get('index')

    if index is None or index < 0 or index >= len(open_positions):
        raise HTTPException(status_code=422, detail="Невірний індекс позиції")
    
    position = open_positions.pop(index)
    current_price = (await get_crypto_prices())["BTCUSDT"]

    if position.stop_loss and current_price <= position.stop_loss:
        pnl = calculate_pnl(position, position.stop_loss)
    elif position.take_profit and current_price >= position.take_profit:
        pnl = calculate_pnl(position, position.take_profit)
    else:
        pnl = calculate_pnl(position, current_price)
    
    initial_capital = position.entry_price * position.quantity
    user_balance += (initial_capital + pnl) * 0.999
    logger.info(f"Trade closed successfully. New balance: {user_balance}")
    return {"message": "Trade closed successfully", "balance": user_balance}

# Отримання відкритих позицій
@app.get("/positions")
async def get_positions():
    current_price = (await get_crypto_prices())["BTCUSDT"]
    positions_with_pnl = []
    for position in open_positions:
        pnl = calculate_pnl(position, current_price)
        liquidation_price = calculate_liquidation_price(position)
        positions_with_pnl.append({
            **position.dict(),
            "pnl": pnl,
            "liquidation_price": liquidation_price
        })
    return {"positions": positions_with_pnl}

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)