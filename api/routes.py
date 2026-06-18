from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import ExchangeRateRecord

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("", summary="List saved exchange rate records")
def list_rates(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(ExchangeRateRecord)
        .order_by(ExchangeRateRecord.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.get("/latest", summary="Get the most recent exchange rate record")
def latest_rates(db: Session = Depends(get_db)):
    record = (
        db.query(ExchangeRateRecord)
        .order_by(ExchangeRateRecord.timestamp.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No rates found")
    return record


@router.post("/fetch", summary="Manually trigger a scrape and save")
def fetch_rates():
    from main import (
        _scrape_and_save,
    )  # imported here to avoid circular import at module level

    _scrape_and_save()
    return {"message": "Rates fetched and saved successfully"}


VALID_CURRENCIES = {"usd", "euro", "mlc", "cad", "mxn", "zelle", "cla"}


@router.get(
    "/history/{currency}", summary="Get historical values for a single currency"
)
def currency_history(currency: str, months: int = 3, db: Session = Depends(get_db)):
    if currency not in VALID_CURRENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid currency. Valid options: {', '.join(sorted(VALID_CURRENCIES))}",
        )
    since = datetime.utcnow() - timedelta(days=months * 30)
    records = (
        db.query(ExchangeRateRecord)
        .filter(ExchangeRateRecord.timestamp >= since)
        .order_by(ExchangeRateRecord.timestamp.asc())
        .all()
    )
    return [
        {"timestamp": r.timestamp.isoformat(), "value": getattr(r, currency)}
        for r in records
        if getattr(r, currency) is not None
    ]
