import uuid
from typing import Any, Dict, List, Optional, Union
from backend.app.schemas.product import ProductCreate
from backend.app.supabase_client.client import get_supabase_client


class ProductRepository:
    def __init__(self, client: Optional[Any] = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def list_products(self) -> List[Dict[str, Any]]:
        res = self.client.table("products").select("*").execute()
        return res.data or []

    def get_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("products")
            .select("*")
            .eq("product_id", product_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def get_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        res = (
            self.client.table("products")
            .select("*")
            .eq("product_name", product_name)
            .execute()
        )
        return res.data[0] if res.data else None

    def create_product(
        self, product_data: Union[Dict[str, Any], ProductCreate]
    ) -> Dict[str, Any]:
        if isinstance(product_data, ProductCreate):
            data = product_data.model_dump(exclude_none=True)
        else:
            data = dict(product_data)

        if not data.get("product_id"):
            data["product_id"] = f"PRD-{uuid.uuid4().hex[:6].upper()}"

        res = self.client.table("products").insert(data).execute()
        return res.data[0] if res.data else data


product_repo = ProductRepository()
