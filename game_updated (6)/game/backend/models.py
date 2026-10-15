from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class Room(Base):
    __tablename__ = "rooms"
    id = Column(String, primary_key=True, index=True)
    host = Column(String)
    max_players = Column(Integer)
    initial_cash = Column(Float)
    end_time = Column(DateTime)
    players = relationship("Player", back_populates="room")

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    room_id = Column(String, ForeignKey("rooms.id"))
    cash = Column(Float)
    room = relationship("Room", back_populates="players")
    portfolio = relationship("StockHolding", back_populates="player")

class StockHolding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    ticker = Column(String)
    quantity = Column(Integer)
    purchase_price = Column(Float)
    player = relationship("Player", back_populates="portfolio")
