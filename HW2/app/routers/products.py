from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import Product
from app.errors import AppError

from app.generated.models import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductStatus,
)

router = APIRouter(prefix="/products", tags=["Products"])


def _to_response(p: Product) -> ProductResponse:
    return ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        price=float(p.price),
        stock=p.stock,
        category=p.category,
        status=ProductStatus(root=p.status),
        created_at=p.created_at.replace(tzinfo=timezone.utc),
        updated_at=p.updated_at.replace(tzinfo=timezone.utc),
    )


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    product = Product(
        name=body.name,
        description=body.description,
        price=body.price,
        stock=body.stock,
        category=body.category,
        status=body.status.root if body.status else "ACTIVE",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_response(product)


@router.get("/{id}", response_model=ProductResponse)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise AppError(
            error_code="PRODUCT_NOT_FOUND",
            message=f"Товар с id={id} не найден",
            status_code=404,
        )
    return _to_response(product)


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(0, ge=0, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    status: str = Query(None, description="Фильтр по статусу"),
    category: str = Query(None, description="Фильтр по категории"),
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if status:
        query = query.filter(Product.status == status)
    if category:
        query = query.filter(Product.category == category)

    total = query.count()
    items = query.offset(page * size).limit(size).all()

    return ProductListResponse(
        items=[_to_response(p) for p in items],
        total_elements=total,
        page=page,
        size=size,
    )


@router.put("/{id}", response_model=ProductResponse)
def update_product(id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise AppError(
            error_code="PRODUCT_NOT_FOUND",
            message=f"Товар с id={id} не найден",
            status_code=404,
        )

    if body.name is not None:
        product.name = body.name
    if body.description is not None:
        product.description = body.description
    if body.price is not None:
        product.price = body.price
    if body.stock is not None:
        product.stock = body.stock
    if body.category is not None:
        product.category = body.category
    if body.status is not None:
        product.status = body.status.root

    db.commit()
    db.refresh(product)
    return _to_response(product)


@router.delete("/{id}", response_model=ProductResponse)
def delete_product(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise AppError(
            error_code="PRODUCT_NOT_FOUND",
            message=f"Товар с id={id} не найден",
            status_code=404,
        )

    product.status = "ARCHIVED"
    db.commit()
    db.refresh(product)
    return _to_response(product)
