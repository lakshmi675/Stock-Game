from pydantic import BaseModel
from typing import List
from datetime import datetime

class RoomCreate(BaseModel):
    id: str
    host: str
    max_players: int
    initial_cash: float
    end_time: datetime

class JoinRoom(BaseModel):
    room_id: str
    name: str

class BuyStock(BaseModel):
    player_id: int
    ticker: str
    quantity: int

class Holding(BaseModel):
    ticker: str
    quantity: int
    purchase_price: float
    current_price: float
    profit: float

class PortfolioResponse(BaseModel):
    name: str
    cash: float
    holdings: List[Holding]
    total_profit: float
