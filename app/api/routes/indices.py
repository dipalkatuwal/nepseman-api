from fastapi import APIRouter, HTTPException

from app.models.responses import ok
from app.services import nepse as svc

router = APIRouter(prefix="/indices", tags=["Indices"])


@router.get("/nepse")
async def nepse_index():
    try:
        return ok(await svc.get_nepse_index())
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/subindices")
async def nepse_subindices():
    try:
        return ok(await svc.get_nepse_subindices())
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/graph/{index_name}")
async def index_graph(index_name: str = "nepse"):
    """
    index_name: nepse | sensitive | float | sensitive_float | banking |
                dev_bank | finance | hotel_tourism | hydro | investment |
                life_insurance | manufacturing | microfinance | mutual_fund |
                non_life_insurance | others | trading
    """
    try:
        return ok(await svc.get_index_graph(index_name))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, str(e))
