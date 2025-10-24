import logging
import os
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from hsm_service import initialize_keys_if_not_exist, sign_message, get_public_key_bytes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    service: str


class SignRequest(BaseModel):
    message: str


class SignResponse(BaseModel):
    signature: str  # base64 encoded


class PublicKeyResponse(BaseModel):
    public_key: str  # base64 encoded


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Payment Orchestrator starting up...")
    try:
        initialize_keys_if_not_exist()
        logger.info("HSM keys initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize HSM keys: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Payment Orchestrator shutting down...")


app = FastAPI(
    title="Payment Orchestrator",
    description="Microservice for orchestrating payment processing",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return HealthResponse(status="ok", service="payment_orchestrator")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Payment Orchestrator is running"}


@app.post("/sign", response_model=SignResponse)
async def sign_endpoint(request: SignRequest):
    """
    Sign a message using HSM private key.
    
    Args:
        request: JSON with 'message' field
        
    Returns:
        Signature in base64 format
    """
    try:
        logger.info(f"Signing message: {request.message[:50]}...")
        signature_bytes = sign_message(request.message)
        signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')
        logger.info(f"Message signed successfully")
        return SignResponse(signature=signature_b64)
    except Exception as e:
        logger.error(f"Signing failed: {str(e)}")
        raise


@app.get("/public-key", response_model=PublicKeyResponse)
async def get_public_key_endpoint():
    """
    Get the public key from HSM.
    
    Returns:
        Public key in base64 format
    """
    try:
        logger.info("Retrieving public key from HSM")
        public_key_bytes = get_public_key_bytes()
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')
        logger.info("Public key retrieved successfully")
        return PublicKeyResponse(public_key=public_key_b64)
    except Exception as e:
        logger.error(f"Failed to retrieve public key: {str(e)}")
        raise


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
