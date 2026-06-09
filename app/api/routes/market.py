from fastapi import APIRouter, HTTPException

from app.services import nepse as svc

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/status")
async def market_status():
    try:
        return await svc.get_market_status()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/summary")
async def market_summary():
    try:
        return await svc.get_market_summary()
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/supply-demand")
async def supply_demand():
    try:
        return await svc.get_supply_demand()
    except Exception as e:
        raise HTTPException(502, str(e))
