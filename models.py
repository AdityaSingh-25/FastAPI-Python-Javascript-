from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)
    category: str = Field(default="Uncategorized", min_length=1)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    delta: int = Field(..., description="Amount to add to (or subtract from) current stock")


class CategoryStat(BaseModel):
    category: str
    product_count: int
    total_inventory: int
    total_catalog_value: float


class ProductSummary(BaseModel):
    total_products: int
    total_inventory: int
    total_catalog_value: float
    low_stock_count: int
    out_of_stock_count: int
    average_price: float
    category_breakdown: List[CategoryStat]


class ProductInsights(BaseModel):
    highest_value_product: Optional[ProductResponse]
    reorder_recommendations: List[ProductResponse]
    out_of_stock_products: List[ProductResponse]


class ImportRowError(BaseModel):
    row: int
    error: str


class ImportResult(BaseModel):
    created: int
    failed: int
    errors: List[ImportRowError]
