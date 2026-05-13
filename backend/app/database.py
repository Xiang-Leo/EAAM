"""
backend/app/database.py
-----------------------
SQLAlchemy 2.0 风格的数据库引擎、会话工厂和 Base 声明。
兼容 SQLite（开发）与 PostgreSQL（生产）。
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from .config import get_settings


# ---------------------------------------------------------------------------
# 声明基类（所有 ORM 模型继承此类）
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """SQLAlchemy 2.0 DeclarativeBase，所有 ORM Model 的公共基类。"""
    pass


# ---------------------------------------------------------------------------
# 引擎工厂
# ---------------------------------------------------------------------------
def _make_engine():
    settings = get_settings()
    url = settings.DATABASE_URL

    connect_args: dict = {}

    if url.startswith("sqlite"):
        # SQLite 在多线程场景下需要关闭同线程检查
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        connect_args=connect_args,
        echo=False,          # 生产环境设为 False；调试时可改为 True
        future=True,         # 启用 SQLAlchemy 2.0 行为
        pool_pre_ping=True,  # 连接池心跳检测，防止 PostgreSQL 连接被切断
    )

    # SQLite 专属优化：开启 WAL 模式，提升并发读性能
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _make_engine()

# ---------------------------------------------------------------------------
# 会话工厂
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # 避免访问 commit 后对象触发额外 SELECT
)


# ---------------------------------------------------------------------------
# FastAPI Dependency：get_db
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入：提供数据库 Session，请求结束后自动关闭。

    用法::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 便捷函数：创建所有表（开发 / 测试时使用）
# ---------------------------------------------------------------------------
def create_all_tables() -> None:
    """根据 ORM 模型定义在数据库中创建所有表（若不存在）。"""
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_sqlite_migrations()


def _apply_lightweight_sqlite_migrations() -> None:
    """Small compatibility migrations for deployments without Alembic."""
    settings = get_settings()
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        table_names = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "data_import_jobs" in table_names:
            columns = {
                row[1]
                for row in conn.exec_driver_sql("PRAGMA table_info(data_import_jobs)").fetchall()
            }
            if "field_mapping" not in columns:
                conn.exec_driver_sql("ALTER TABLE data_import_jobs ADD COLUMN field_mapping TEXT")
