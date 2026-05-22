from fastapi import APIRouter, HTTPException
from api.models import StyleRequest, StyleResponse, RecommendedItem
from agent.cache import get_cached, set_cache
from agent.workflow import run_workflow

router = APIRouter(prefix="/api/v1", tags=["Stylist"])


@router.post(
    "/style-me",
    response_model=StyleResponse,
    summary="Get an AI outfit recommendation",
    description=(
        "Send a natural language styling prompt and receive a curated outfit "
        "recommendation with a luxurious stylist note. Responses are semantically "
        "cached — identical or near-identical prompts return instantly."
    ),
)
async def style_me(request: StyleRequest) -> StyleResponse:
    cached = get_cached(request.prompt)
    if cached:
        items = [RecommendedItem(**i) for i in cached.get("recommended_items", [])]
        return StyleResponse(
            recommended_items=items,
            total_price=cached.get("total_price", "$0.00"),
            stylist_note=cached.get("stylist_note", ""),
            cache_hit=True,
        )

    try:
        result = run_workflow(request.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")

    if not result or not result.get("recommended_items"):
        raise HTTPException(status_code=422, detail="Could not generate a recommendation. Try rephrasing.")

    set_cache(request.prompt, result)

    items = [RecommendedItem(**i) for i in result.get("recommended_items", [])]
    return StyleResponse(
        recommended_items=items,
        total_price=result.get("total_price", "$0.00"),
        stylist_note=result.get("stylist_note", ""),
        cache_hit=False,
    )
