from typing import Any, Dict, List, Optional
from fastapi import HTTPException

try:
    from backend.app.schemas.product import ProductResponse
    from backend.app.supabase_client.product_repo import ProductRepository
except ImportError:
    from app.schemas.product import ProductResponse
    from app.supabase_client.product_repo import ProductRepository


class ProductService:
    def __init__(self, product_repo: Optional[ProductRepository] = None):
        self.product_repo = product_repo or ProductRepository()

    def list_products(self) -> List[ProductResponse]:
        products = self.product_repo.list_products()
        return [ProductResponse(**p) for p in products]

    def get_product(self, product_id: str) -> ProductResponse:
        prod = self.product_repo.get_by_id(product_id)
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
        return ProductResponse(**prod)
