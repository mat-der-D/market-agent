from fastapi import FastAPI
from pydantic import BaseModel

from converter import convert

app = FastAPI()


class ConvertRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: float


class ConvertResponse(BaseModel):
    result: float | None = None
    rate: float | None = None
    fetched_at: str | None = None
    error: str | None = None


@app.post("/convert", response_model=ConvertResponse)
def convert_endpoint(req: ConvertRequest) -> dict:
    return convert(req.from_currency, req.to_currency, req.amount)


@app.get("/health")
def health():
    return {"status": "ok"}
