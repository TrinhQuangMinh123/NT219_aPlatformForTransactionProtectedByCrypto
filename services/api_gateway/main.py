from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


app = FastAPI()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()
