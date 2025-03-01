from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
import requests
from datetime import datetime

last_fetch_time = datetime.now()  # ініціалізація змінної

# Потім можна використовувати last_fetch_time у коді


Base = declarative_base()
DATABASE_URL = "sqlite:///./database.db"  # Використовуємо SQLite для збереження даних
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

ALLOWED_AVATARS = ['avatark1.jpg', 'avatark2.jpg', 'avatark3.jpg', 'avatark4.jpg', 'avatark5.jpg']

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    nickname = Column(String, unique=True, nullable=False)  # Додаємо нік
    avatar = Column(String, nullable=False, default='avatark1.jpg')  # Додаємо аватар
    balance = Column(Float, default=0.0)  # Баланс користувача

    def set_avatar(self, avatar_name):
        if avatar_name in ALLOWED_AVATARS:
            self.avatar = avatar_name
        else:
            raise ValueError("Invalid avatar selection")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "balance": self.balance
        }

# Оновлення логіки реєстрації
from fastapi import FastAPI, Form, HTTPException

app = FastAPI()

def register_user(username: str, email: str, password: str, nickname: str, avatar: str):
    session = SessionLocal()
    if avatar not in ALLOWED_AVATARS:
        raise HTTPException(status_code=400, detail="Invalid avatar selection")
    new_user = User(username=username, email=email, password=password, nickname=nickname, avatar=avatar)
    session.add(new_user)
    session.commit()
    session.close()
    return new_user

# Отримання курсу монет
last_fetch_time = 0
cached_rates = {}

def fetch_coin_rates():
    global last_fetch_time, cached_rates
    if 'last_fetch_time' not in globals():
        last_fetch_time = 0  # Ініціалізація змінної, якщо вона не існує
    current_time = time.time()
    if current_time - last_fetch_time > 300:  # Оновлення кожні 5 хвилин
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd")
            cached_rates = response.json()
            last_fetch_time = current_time
        except Exception as e:
            print(f"Error fetching coin rates: {e}")
    return cached_rates

# Створення таблиць у базі даних
Base.metadata.create_all(bind=engine)
