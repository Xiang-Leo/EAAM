"""
backend/app/main.py
--------------------
EAAM FastAPI 应用入口。

启动方式：
    cd backend
    uvicorn app.main:app --reload

生产环境：
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_all_tables
from app.api.routers import samples, taxa, summary, ai, admin

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 生命周期：启动 / 关闭
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager（替代已废弃的 on_event）。
    - 启动时：确保数据库表已创建（不导入数据）。
    - 关闭时：可在此释放资源（如连接池）。
    """
    settings = get_settings()
    logger.info("EAAM API 启动中…  数据库：%s", settings.DATABASE_URL)
    create_all_tables()
    logger.info("数据库表检查完成，服务就绪。")
    yield
    logger.info("EAAM API 正在关闭。")


# ---------------------------------------------------------------------------
# 应用实例
# ---------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # 本地开发前端默认端口
        "http://localhost:9039",   # Docker Compose 映射的前端端口
        # 在真实部署中，应当把云服务器的公网 IP 放进环境变量 CORS_ORIGINS 中，或者直接在这里放行。
        # 这里设置为允许所有以避免初学者配置麻烦，生产环境建议缩小范围
        "*", 
        *settings.CORS_ORIGINS,
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers 注册
# ---------------------------------------------------------------------------
app.include_router(samples.router, prefix="/api/samples", tags=["Samples"])
app.include_router(taxa.router,    prefix="/api/taxa",    tags=["Taxa"])
app.include_router(summary.router, prefix="/api/summary", tags=["Summary"])
app.include_router(ai.router,      prefix="/api/ai",      tags=["AI"])
app.include_router(admin.router,   prefix="/api/admin",   tags=["Admin"])

# ---------------------------------------------------------------------------
# 基础路由
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health_check():
    """
    健康检查端点，供 Docker / 负载均衡器探活使用。
    """
    return {"status": "ok"}


@app.get("/", tags=["Root"])
def root():
    """API 根路径，返回欢迎信息与文档链接。"""
    return {
        "message": "Welcome to EAAM API",
        "docs":    "/docs",
        "redoc":   "/redoc",
        "health":  "/health",
    }
