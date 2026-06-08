from fastapi import FastAPI
from app.errors import register_error_handlers
from app.routers import products

app = FastAPI(
    title="Marketplace API",
    description="API маркетплейса — HW2",
    version="1.0.0",
)

register_error_handlers(app)

app.include_router(products.router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}