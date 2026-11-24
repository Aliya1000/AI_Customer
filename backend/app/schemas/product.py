from typing import Optional
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    product_id: Optional[str] = None
    product_name: str = Field(min_length=1)
    product_description: str = Field(min_length=1)
    product_category: str = Field(min_length=1)


class ProductResponse(BaseModel):
    product_id: str
    product_name: str
    product_description: str
    product_category: str
