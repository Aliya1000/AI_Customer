from typing import List
from fastapi import APIRouter, Depends, status

try:
    from backend.app.schemas.product import ProductResponse
    from backend.app.services.product_service import ProductService
except ImportError:
    from app.schemas.product import ProductResponse
    from app.services.product_service import ProductService

router = APIRouter(tags=["Products"])


def get_product_service() -> ProductService:
    return ProductService()


@router.get(
    "/products",
    status_code=status.HTTP_200_OK,
    response_model=List[ProductResponse],
    summary="List all products",
)
@router.get(
    "/products/",
    status_code=status.HTTP_200_OK,
    response_model=List[ProductResponse],
    include_in_schema=False,
)
def list_products(
    service: ProductService = Depends(get_product_service),
) -> List[ProductResponse]:
    return service.list_products()
