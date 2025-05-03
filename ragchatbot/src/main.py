from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from fastapi import Form
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.requests import Request
from src.security import is_rate_limited
from config.config import TOKEN_RETRIEVAL_SECRET
from src.rag import generate_answer
import uuid

# One-time valid tokens
one_time_tokens = set()

app = FastAPI(
    title="SalesChatBot API",
    summary="This API receives query as a json and returns an answer based on its knowledge base trained before.",
    version="1.0.0",
    contact={
        "name": "Erfan Mahmoudi",
        "email": "e.mahmoudi@greenweb.ir",
    },
)

# Simple in-memory rate limiter
rate_limit_data: Dict[str, list] = {}

# Request Models
class GetTokenRequest(BaseModel):
    secret: str = Field(
        ...,
        title="secret key for test in dev mode",
        description="کلید جهت استفاده از API",
        example="tir-ligufhwli-ughfwieuy-lguewiyg"
    )

# Response Models
class TokenResponse(BaseModel):
    token: str = Field(
        ...,
        title="Generated token",
        description="توکن یکبار مصرف تولیدشده",
        example="550e8400-e29b-41d4-a716-446655440000"
    )

class BaseErrorResponse(BaseModel):
    detail: str = Field(..., example="خطایی غیر منتظره رخ داده است")

class BadRequestResponse(BaseErrorResponse):
    detail: str = Field(..., example="پیام خالی است")

class UnauthorizedResponse(BaseErrorResponse):
    detail: str = Field(..., example=".توکن وارد نشده است")

class ForbiddenResponse(BaseErrorResponse):
    detail: str = Field(..., example=".توکن وارد شده معتبر نیست")

class TooShortDescriptionResponse(BaseErrorResponse):
    detail: str = Field(..., example="پیام خیلی کوتاه است")

class ValidationResponse(BaseErrorResponse):
    detail: str = Field(..., example="فرمت ورودی نامعتبر است")

class RateLimitResponse(BaseErrorResponse):
    detail: str = Field(..., example="تعداد درخواست‌ها بیش از حد مجاز است.")

class InternalServerErrorResponse(BaseErrorResponse):
    detail: str = Field(..., example="خطایی سمت سرور رخ داده است")

class ChatRequest(BaseModel):
    query: str = Field(..., example="من برای خرید هاست نیاز به کمک دارم")

class ChatResponse(BaseModel):
    answer: str = Field(..., example="برای خرید هاست، ابتدا باید نیازهای خود را مشخص کنید. آیا به هاست اشتراکی نیاز دارید یا هاست اختصاصی؟ همچنین، توجه داشته باشید که هاست شما باید با نوع وب‌سایت شما سازگار باشد. برای مثال، اگر وب‌سایت شما بر پایه وردپرس است، بهتر است از هاست وردپرس استفاده کنید.")

@app.post(
    "/get_token/",
    summary="Generate a one-time-use token",
    responses={
        401: {"model": UnauthorizedResponse, "description": "When token is empty"},
        403: {"model": ForbiddenResponse, "description": "When token is invalid"},
        422: {"model": ValidationResponse, "description": "input format validation error"},
        429: {"model": RateLimitResponse, "description": "When rate limit is exceeded"},
        500: {"model": InternalServerErrorResponse, "description": "internal server error"},
    },
    response_model=TokenResponse
)
async def get_token(
    request: GetTokenRequest,
    client_request: Request
):  
    if not request.secret or request.secret == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"msg": "فیلد کلید نمیتواند خالی باشد"}
        )
    
    client_ip = client_request.client.host
    if is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"msg": "تعداد درخواست‌ها بیش از حد مجاز است"}
        )

    if request.secret != TOKEN_RETRIEVAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"msg": "توکن نامعتبر یا منقضی شده است"}
        )

    new_token = str(uuid.uuid4())
    one_time_tokens.add(new_token)
    return {"token": new_token}

@app.post(
        "/chat",
        response_model=ChatResponse,
        responses={
            400: {"model": BadRequestResponse, "description": "When message is empty"},
            401: {"model": UnauthorizedResponse, "description": "When token is empty"},
            403: {"model": ForbiddenResponse, "description": "When token is invalid"},
            422: {"model": TooShortDescriptionResponse, "description": "When description is too short or invalid"},
            429: {"model": RateLimitResponse, "description": "When rate limit is exceeded"},
            500: {"model": InternalServerErrorResponse, "description": "internal server error"},
    }
)
async def chat(
    request: ChatRequest,
    client_request: Request,
    x_api_key: Optional[str] = Header(None, alias="x-api-key")
):
    
    if not x_api_key or x_api_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"msg": "فیلد کلید نمیتواند خالی باشد"}
        )

    if x_api_key not in one_time_tokens:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"msg": "توکن نامعتبر یا منقضی شده است"}
        )
    one_time_tokens.remove(x_api_key)

    # Rate limiting
    client_ip = client_request.client.host
    if is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"msg": "تعداد درخواست‌ها بیش از حد مجاز است"}
        )

    try:
        # Call the generate_answer function from rag.py
        answer = generate_answer(request.query)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطایی در پردازش سوال رخ داده است: {str(e)}"
        )

