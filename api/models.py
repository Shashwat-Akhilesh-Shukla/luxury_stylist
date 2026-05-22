from pydantic import BaseModel, Field
from typing import Optional


class StyleRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        examples=["I have dark navy chinos, what t-shirt and shoes should I wear for a summer yacht party?"],
    )


class RecommendedItem(BaseModel):
    name: str
    price: str
    category: str
    color: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None


class StyleResponse(BaseModel):
    recommended_items: list[RecommendedItem]
    total_price: str
    stylist_note: str
    cache_hit: bool = False
