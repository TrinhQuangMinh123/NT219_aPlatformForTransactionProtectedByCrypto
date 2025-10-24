import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    service: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Order Service starting up...")
    yield
    # Shutdown
    logger.info("Order Service shutting down...")


app = FastAPI(
    title="Order Service",
    description="Microservice for managing orders",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return HealthResponse(status="ok", service="order_service")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Order Service is running"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
