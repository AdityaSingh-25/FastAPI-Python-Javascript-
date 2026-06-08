import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import (
    ImportResult,
    ProductCreate,
    ProductInsights,
    ProductPage,
    ProductResponse,
    ProductSummary,
    StockAdjustment,
)
from app.services import products as service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductPage)
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    min_price: float = Query(default=0, ge=0),
    max_price: float = Query(default=100000, ge=0),
    search: str = "",
    stock_status: str = "all",
    category: str = "",
    sort_by: str = "name",
    db: Session = Depends(get_db),
):
    if min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price",
        )
    if stock_status not in service.STOCK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stock_status must be one of: all, healthy, low, out",
        )
    if sort_by not in service.SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_by must be one of: name, stock, value, price",
        )

    items, total = service.list_products(
        db,
        skip=skip,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        search=search,
        stock_status=stock_status,
        category=category,
        sort_by=sort_by,
    )
    return ProductPage(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/summary", response_model=ProductSummary)
def get_summary(db: Session = Depends(get_db)):
    return service.summarize(db)


@router.get("/insights", response_model=ProductInsights)
def get_insights(db: Session = Depends(get_db)):
    data = service.insights(db)
    return ProductInsights(
        highest_value_product=(
            ProductResponse.model_validate(data["highest_value_product"])
            if data["highest_value_product"]
            else None
        ),
        reorder_recommendations=[
            ProductResponse.model_validate(p) for p in data["reorder_recommendations"]
        ],
        out_of_stock_products=[
            ProductResponse.model_validate(p) for p in data["out_of_stock_products"]
        ],
    )


@router.get("/categories", response_model=list[str])
def get_categories(db: Session = Depends(get_db)):
    return service.list_categories(db)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    try:
        return service.get_product(db, product_id)
    except service.ProductNotFound:
        raise HTTPException(status_code=404, detail="Product not found")


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    try:
        created = service.create_product(db, product)
        logger.info("Product created: ID=%s", created.id)
        return created
    except Exception as exc:
        db.rollback()
        logger.error("Error creating product: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create product")


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
async def import_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    try:
        created, errors = service.import_csv(db, raw, file.filename)
    except service.CsvImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.error("Error importing products: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to import products")

    logger.info("Imported %s products with %s errors", created, len(errors))
    return ImportResult(created=created, failed=len(errors), errors=errors)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, updated: ProductCreate, db: Session = Depends(get_db)):
    try:
        product = service.update_product(db, product_id, updated)
        logger.info("Product updated: ID=%s", product_id)
        return product
    except service.ProductNotFound:
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception as exc:
        db.rollback()
        logger.error("Error updating product %s: %s", product_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update product")


@router.patch("/{product_id}/stock", response_model=ProductResponse)
def adjust_stock(product_id: int, adjustment: StockAdjustment, db: Session = Depends(get_db)):
    try:
        product = service.adjust_stock(db, product_id, adjustment.delta)
        logger.info(
            "Stock adjusted: ID=%s, delta=%s, quantity=%s",
            product_id,
            adjustment.delta,
            product.quantity,
        )
        return product
    except service.ProductNotFound:
        raise HTTPException(status_code=404, detail="Product not found")
    except service.InvalidStockAdjustment as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    try:
        service.delete_product(db, product_id)
        logger.info("Product deleted: ID=%s", product_id)
        return {"message": "Product deleted successfully"}
    except service.ProductNotFound:
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception as exc:
        db.rollback()
        logger.error("Error deleting product %s: %s", product_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete product")
