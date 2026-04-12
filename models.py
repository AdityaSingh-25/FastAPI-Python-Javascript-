from pydantic import BaseModel, Field, ConfigDict

# Base schema with validation
class ProductBase(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)


# Create schema
class ProductCreate(ProductBase):
    pass


# Update schema
class ProductUpdate(ProductBase):
    pass


# Response schema
class ProductResponse(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)  
    #  REQUIRED for SQLAlchemy → Pydantic conversion