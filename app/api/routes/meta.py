from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services import nepse as svc

router = APIRouter(prefix="/floorsheet", tags=["Floorsheet"])


@router.get("/")
async def floor_sheet(page: int = 0, size: int = 500):
    try:
        return await svc.get_floor_sheet(page=page, size=size)
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/{symbol}")
async def floor_sheet_of(symbol: str, business_date: Optional[str] = None, size: int = 500):
    try:
        return await svc.get_floor_sheet_of(symbol, business_date, size)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))
