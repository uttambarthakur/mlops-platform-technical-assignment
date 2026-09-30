import time
import uuid
import os
import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import jwt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from api.v1.minimum import router as minimum_router
from log import get_logger
from app.models.orm_models import Base



engine = create_async_engine(os.getenv("DATABASE_URL", ""), echo=True, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: optional cleanup

app = FastAPI()
logger = get_logger()
load_dotenv()

origins = [
    "https://localhost:4200",
]


app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods="*", allow_headers=["*"])

app.include_router(minimum_router, prefix="/api/v1")


def create_token(role: str, env: str = "staging", ttl_minutes: int = 30) -> str:
    """Generate token for a role using jwt"""
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ttl_minutes)
    payload = {
        "role": role,
        "env": env,
        "exp": exp
        }  # other claims can also be added if needed such as tenant_id

    return jwt.encode(payload, os.getenv("SECRET_KEY", "thisissamplestring"), algorithm=os.getenv("ALGORITHM", "SHA256"))


def decode_token(token: str):
    """Verify token and return role if valid"""
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY", "thisissamplestring"), algorithms=[os.getenv("ALGORITHM", "SHA256")])
        return payload
    except jwt.ExpiredSignatureError:
        return {"role": "guest", "env": "unknown", "error": "Token Expired"}
    except jwt.PyJWKError:
        return {"role": "guest", "env": "unknown", "error": "Invalid Token"}


@app.middleware("http")
async def add_observability(request: Request, call_next):
    # Generate correlation ID per request
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    start_time = time.time()
    logger.info(f"[{correlation_id}] Incoming {request.method} {request.url}")

    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"[{correlation_id}] Error: {e}")
        raise

    process_time = (time.time() - start_time) * 1000
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time-ms"] = str(process_time)

    logger.info(f"[{correlation_id}] Completed in {process_time:.2f}ms")
    return response


@app.middleware("http")
async def jwt_role_auth(request: Request, call_next):
    """
    - Reads 'X-Role' header (e.g admin, approver, operator)
    - Enforces rules: only admin can deploy to production
    - Returns 403 if unauthorized
    """
    auth_header = request.headers.get("Authorization")
    claims = {"role": "guest", "env": "unknown"}

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        claims = decode_token(token=token)

    role = claims.get("role", "guest")
    env = claims.get("env", "staging")
    # Governance rules
    if request.url.path.startswith("/deployments") and request.method == "POST":
        env = request.query_params.get("env", "staging")
        if env.lower() == "production" and role != "admin":
            return JSONResponse(status_code=403, content={"detail": "Only admin can deploy to production"})

    if request.url.path.endswith("rollback") and role not in ["admin", "operator"]:
        return JSONResponse(
            status_code=403,
            content={"detail", "Rollback requires admin or operator role"}
        )
    if request.url.path.endswith("/versions") and request.method == "POST":
        if role != "approver":
            return JSONResponse(
                status_code=403,
                content={"detail": "Only approver can register new versions"}
            )

    request.state.claims = claims
    return await call_next(request)
