from pydantic import BaseModel, Field

# Base schema with validation (NEW)
class ProductBase(BaseModel):
    name: str = Field(..., min_length=2)          # Ensures name is at least 2 chars
    description: str = Field(..., min_length=5)   # Ensures meaningful description
    price: float = Field(..., gt=0)               # Price must be > 0
    quantity: int = Field(..., ge=0)              # Quantity cannot be negative


# Used when creating/updating product (NEW)
class ProductCreate(ProductBase):
    pass


# Response model (NEW)
class ProductResponse(ProductBase):
    id: int   # Include ID in response

    class Config:
        orm_mode = True   # ✅ FIX: required for SQLAlchemy → Pydantic 
        # Allows returning SQLAlchemy models directly (IMPORTANT)