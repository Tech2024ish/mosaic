from fastapi import APIRouter

router = APIRouter()


@router.get("", tags=["system"])
def api_root() -> dict[str, str]:
    return {"name": "MOSAIC API", "version": "v1"}
