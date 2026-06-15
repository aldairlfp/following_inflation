from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer

from database.database import Base


class ExchangeRateRecord(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    usd = Column(Float, nullable=True)
    euro = Column(Float, nullable=True)
    mlc = Column(Float, nullable=True)
    cad = Column(Float, nullable=True)
    mxn = Column(Float, nullable=True)
    zelle = Column(Float, nullable=True)
    cla = Column(Float, nullable=True)
