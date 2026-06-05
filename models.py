from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProductSummary(BaseModel):
    total_products: int
    total_inventory: int
    total_catalog_value: float
    low_stock_count: int
    out_of_stock_count: int
    average_price: float


class ProductInsights(BaseModel):
    highest_value_product: Optional[ProductResponse]
    reorder_recommendations: List[ProductResponse]
    out_of_stock_products: List[ProductResponse]
