# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List
import yfinance as yf
from . import models, schemas, database
import requests


app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=database.engine)

#currency exchange function

def get_usd_to_inr():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
        rate = response.json()["rates"]["INR"]
        return rate
    except:
        return 85

@app.post("/create_room/")
def create_room(room: schemas.RoomCreate):
    db = database.SessionLocal()
    db_room = models.Room(
        id=room.id,
        host=room.host,
        max_players=room.max_players,
        initial_cash=room.initial_cash,
        end_time=room.end_time
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return {"message": "Room created successfully"}

@app.post("/join_room/")
def join_room(join: schemas.JoinRoom):
    db = database.SessionLocal()
    room = db.query(models.Room).filter(models.Room.id == join.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    player = models.Player(name=join.name, room_id=join.room_id, cash=room.initial_cash)
    db.add(player)
    db.commit()
    db.refresh(player)
    return {"player_id": player.id}

@app.post("/buy_stock/")
def buy_stock(purchase: schemas.BuyStock):
    db = database.SessionLocal()
    rate = get_usd_to_inr()
    try:
        player = db.query(models.Player).filter(models.Player.id == purchase.player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        stock = yf.Ticker(purchase.ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]

        if purchase.ticker.upper().endswith(".NS"):
            total_cost_inr = price * purchase.quantity
            total_cost_usd = total_cost_inr / rate
        else:
            total_cost_usd = price * purchase.quantity

        if player.cash < total_cost_usd:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        holding = db.query(models.StockHolding).filter_by(player_id=player.id, ticker=purchase.ticker).first()
        if holding:
            total_quantity = holding.quantity + purchase.quantity
            holding.purchase_price = (
                (holding.purchase_price * holding.quantity) + (price * purchase.quantity)
            ) / total_quantity
            holding.quantity = total_quantity
        else:
            holding = models.StockHolding(
                player_id=player.id,
                ticker=purchase.ticker,
                quantity=purchase.quantity,
                purchase_price=price
            )
            db.add(holding)

        player.cash -= total_cost_usd
        db.commit()
        return {"message": "Stock purchased successfully"}
    finally:
        db.close()
#SELL STOCK
@app.post("/sell_stock/")
def sell_stock(purchase: schemas.BuyStock):
    db = database.SessionLocal()
    try:
        player = db.query(models.Player).filter(models.Player.id == purchase.player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        holding = db.query(models.StockHolding).filter_by(player_id=player.id, ticker=purchase.ticker).first()
        if not holding or holding.quantity < purchase.quantity:
            raise HTTPException(status_code=400, detail="Not enough stock to sell")

        stock = yf.Ticker(purchase.ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]

        # Update or delete holding
        holding.quantity -= purchase.quantity
        if holding.quantity == 0:
            db.delete(holding)

        player.cash += price * purchase.quantity
        db.commit()
        return {"message": "Stock sold successfully"}
    finally:
        db.close()
#SELL STOCK
#GET PORTFOLIO
@app.get("/portfolio/{player_id}")
def get_portfolio(player_id: int):
    db = database.SessionLocal()
    rate = get_usd_to_inr()
    try:
        player = db.query(models.Player).filter(models.Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        holdings_data = []
        total_profit = 0

        for h in player.portfolio:
            try:
                stock = yf.Ticker(h.ticker)
                current_price = stock.fast_info.get("lastPrice", None)
                if current_price is None or current_price == 0:
                    hist = stock.history(period="1d", interval="1m")
                    current_price = hist["Close"].iloc[-1] if not hist.empty else h.purchase_price
            except:
                current_price = h.purchase_price

            if h.ticker.upper().endswith(".NS"):
                purchase_price_usd = h.purchase_price / rate
                current_price_usd = current_price / rate
            else:
                purchase_price_usd = h.purchase_price
                current_price_usd = current_price

            profit = (current_price_usd - purchase_price_usd) * h.quantity
            total_profit += profit

            holdings_data.append({
                "ticker": h.ticker,
                "quantity": h.quantity,
                "purchase_price": purchase_price_usd,
                "current_price": current_price_usd,
                "profit": profit,
                "currency": "$"
            })

        return {
            "name": player.name,
            "cash": round(player.cash, 2),
            "holdings": holdings_data,
            "total_profit": round(total_profit, 2)
        }
    finally:
        db.close()



@app.get("/time_left/{room_id}")
def get_time_left(room_id: str):
    db = database.SessionLocal()
    try:
        room = db.query(models.Room).filter(models.Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        now = datetime.utcnow()
        remaining = (room.end_time - now).total_seconds()
        return {"seconds_left": max(0, int(remaining))}
    finally:
        db.close()  # ✅ Prevent connection leak


@app.get("/leaderboard/{room_id}")
def get_leaderboard(room_id: str):
    db = database.SessionLocal()
    try:
        room = db.query(models.Room).filter(models.Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        rate = get_usd_to_inr()
        leaderboard = []

        for player in room.players:
            total_profit = 0
            for h in player.portfolio:
                try:
                    stock = yf.Ticker(h.ticker)
                    current_price = stock.fast_info.get("lastPrice", None)
                    if current_price is None or current_price == 0:
                        hist = stock.history(period="1d", interval="1m")
                        current_price = hist["Close"].iloc[-1] if not hist.empty else h.purchase_price
                except:
                    current_price = h.purchase_price

                if h.ticker.upper().endswith(".NS"):
                    purchase_price_usd = h.purchase_price / rate
                    current_price_usd = current_price / rate
                else:
                    purchase_price_usd = h.purchase_price
                    current_price_usd = current_price

                profit = (current_price_usd - purchase_price_usd) * h.quantity
                total_profit += profit

            leaderboard.append({
                "name": player.name,
                "total_profit": round(total_profit, 2)
            })

        leaderboard.sort(key=lambda x: x["total_profit"], reverse=True)
        return leaderboard
    finally:
        db.close()



@app.get("/stock_price/{ticker}")
def get_stock_price(ticker: str):
    try:
        stock = yf.Ticker(ticker)

        # Try fast live price
        price = stock.fast_info.get("lastPrice", None)
        if price is None or price == 0:
            # fallback to 1-min interval
            hist = stock.history(period="1d", interval="1m")
            if not hist.empty:
                price = hist["Close"].iloc[-1]
            else:
                # fallback to last daily close.
                price = stock.history(period="1d")["Close"].iloc[-1]

        print(f"[PRICE] {ticker.upper()}: {price}")
        return {"ticker": ticker.upper(), "price": round(price, 2)}
    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=404, detail="Invalid ticker or no data available")
