#!/usr/bin/env python3
"""
scripts/import_to_db.py
------------------------
将 samples.csv 和 taxonomy_abundance_long.csv 导入后端数据库（SQLite / PostgreSQL）。

用法：
    # 使用默认路径（SQLite，存放于 backend/ 下）
    python scripts/import_to_db.py

    # 自定义路径
    python scripts/import_to_db.py \\
        --samples   data/raw/samples.csv \\
        --abundance data/processed/taxonomy_abundance_long.csv \\
        --database-url sqlite:///./backend/ancient_calculus.db

    # 重置数据库（清空旧数据再导入）
    python scripts/import_to_db.py --reset

退出码：
    0  导入成功
    1  发生致命错误
"""

import argparse
import logging
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 将 backend/ 目录加入 Python 路径，确保可以直接 import app.*
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base
from app.models import Sample, Taxon, TaxonomyAbundance

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认值
# ---------------------------------------------------------------------------
DEFAULT_SAMPLES_PATH   = "data/raw/samples.csv"
DEFAULT_ABUNDANCE_PATH = "data/processed/taxonomy_abundance_long.csv"
DEFAULT_DATABASE_URL   = "sqlite:///./backend/ancient_calculus.db"
BATCH_SIZE             = 2_000  # 每批次写入记录数


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _na_to_none(value):
    """将 pandas NaN / NaT 转换为 Python None。"""
    if value is None:
        return None
    try:
        if math.isnan(float(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _make_engine_and_session(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(database_url, connect_args=connect_args, future=True)

    # SQLite 优化
    if database_url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, Session


def _reset_database(engine) -> None:
    """删除并重建所有表（清空旧数据）。"""
    logger.warning("--reset 模式：正在删除所有旧表……")
    Base.metadata.drop_all(bind=engine)
    logger.info("旧表已删除，重新创建……")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表重建完成。")


def _ensure_tables(engine) -> None:
    """若表不存在则创建（不删除现有数据）。"""
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表检查 / 创建完成。")


# ---------------------------------------------------------------------------
# 步骤 1：导入 Samples
# ---------------------------------------------------------------------------

def import_samples(
    db: Session,
    samples_path: Path,
) -> dict[str, int]:
    """
    将 samples.csv 导入 samples 表。
    返回 {sample_id: Sample.id} 映射。
    """
    logger.info("── 步骤 1/3：导入样品元数据 ─────────────────────────")
    df = pd.read_csv(samples_path, dtype=str)
    logger.info("读取样品 CSV：%d 行", len(df))

    sample_id_to_pk: dict[str, int] = {}
    inserted = skipped = 0

    for _, row in df.iterrows():
        sid = str(row.get("sample_id", "")).strip()
        if not sid:
            logger.warning("跳过空 sample_id 行。")
            skipped += 1
            continue

        # 若已存在则跳过（支持幂等导入）
        existing = db.query(Sample).filter(Sample.sample_id == sid).first()
        if existing:
            sample_id_to_pk[sid] = existing.id
            skipped += 1
            continue

        def _str(col: str) -> str | None:
            v = row.get(col)
            return str(v).strip() if pd.notna(v) and str(v).strip() else None

        def _int(col: str) -> int | None:
            v = row.get(col)
            try:
                return int(float(v)) if pd.notna(v) else None
            except (ValueError, TypeError):
                return None

        def _float(col: str) -> float | None:
            v = row.get(col)
            try:
                return float(v) if pd.notna(v) else None
            except (ValueError, TypeError):
                return None

        sample = Sample(
            sample_id=sid,
            province=_str("province"),
            region=_str("region"),
            dynasty=_str("dynasty"),
            period=_str("period"),
            estimated_year=_int("estimated_year"),
            sex=_str("sex"),
            subsistence_pattern=_str("subsistence_pattern"),
            site_name=_str("site_name"),
            latitude=_float("latitude"),
            longitude=_float("longitude"),
            source=_str("source"),
        )
        db.add(sample)
        db.flush()  # 获取自增 ID
        sample_id_to_pk[sid] = sample.id
        inserted += 1

    db.commit()
    logger.info("样品导入完成：新增 %d 条，跳过（已存在/空） %d 条。", inserted, skipped)
    return sample_id_to_pk


# ---------------------------------------------------------------------------
# 步骤 2：导入唯一 Taxa
# ---------------------------------------------------------------------------

def import_taxa(
    db: Session,
    abundance_df: pd.DataFrame,
) -> dict[tuple[str, str, str], int]:
    """
    从 abundance 长表中提取唯一 taxon，导入 taxa 表。
    返回 {(taxid, name, rank): Taxon.id} 映射。
    """
    logger.info("── 步骤 2/3：导入唯一分类单元（Taxa）──────────────────")

    # 提取唯一 taxon（taxid + name + rank 联合唯一）
    unique_taxa = (
        abundance_df[["taxid", "name", "lvl_type", "rank"]]
        .drop_duplicates(subset=["taxid", "name", "rank"])
        .reset_index(drop=True)
    )
    logger.info("唯一 taxon 数量：%d", len(unique_taxa))

    taxon_key_to_pk: dict[tuple[str, str, str], int] = {}
    inserted = skipped = 0

    for _, row in unique_taxa.iterrows():
        taxid    = str(row["taxid"]).strip()
        name     = str(row["name"]).strip()
        lvl_type = str(row["lvl_type"]).strip()
        rank     = str(row["rank"]).strip()
        key      = (taxid, name, rank)

        existing = (
            db.query(Taxon)
            .filter(Taxon.taxid == taxid, Taxon.name == name, Taxon.rank == rank)
            .first()
        )
        if existing:
            taxon_key_to_pk[key] = existing.id
            skipped += 1
            continue

        taxon = Taxon(taxid=taxid, name=name, lvl_type=lvl_type, rank=rank)
        db.add(taxon)
        db.flush()
        taxon_key_to_pk[key] = taxon.id
        inserted += 1

    db.commit()
    logger.info("Taxa 导入完成：新增 %d 条，跳过（已存在） %d 条。", inserted, skipped)
    return taxon_key_to_pk


# ---------------------------------------------------------------------------
# 步骤 3：导入 TaxonomyAbundance（批量）
# ---------------------------------------------------------------------------

def import_abundance(
    db: Session,
    abundance_df: pd.DataFrame,
    sample_id_to_pk: dict[str, int],
    taxon_key_to_pk: dict[tuple[str, str, str], int],
) -> int:
    """
    将 abundance 长表批量写入 taxonomy_abundance 表。
    返回成功写入的行数。
    """
    logger.info("── 步骤 3/3：批量导入 Taxonomy Abundance ──────────────")
    total_rows = len(abundance_df)
    logger.info("待导入总行数：%d（批量大小：%d）", total_rows, BATCH_SIZE)

    batch: list[dict] = []
    inserted = skipped_sample = skipped_taxon = 0
    t0 = time.time()

    for idx, row in abundance_df.iterrows():
        sid  = str(row["sample_id"]).strip()
        txid = str(row["taxid"]).strip()
        name = str(row["name"]).strip()
        rank = str(row["rank"]).strip()
        key  = (txid, name, rank)

        # 检查 sample 是否存在
        pk_sample = sample_id_to_pk.get(sid)
        if pk_sample is None:
            if skipped_sample < 5:
                logger.warning("sample_id '%s' 不在 samples 表中，跳过该行。", sid)
            elif skipped_sample == 5:
                logger.warning("（后续相同 warning 将不再重复输出）")
            skipped_sample += 1
            continue

        # 检查 taxon 是否存在
        pk_taxon = taxon_key_to_pk.get(key)
        if pk_taxon is None:
            logger.warning("taxon key %s 不在 taxa 表中，跳过。", key)
            skipped_taxon += 1
            continue

        batch.append(
            {
                "sample_id":               pk_sample,
                "taxon_id":                pk_taxon,
                "reads_all":               float(row["reads_all"]),
                "reads_lvl":               float(row["reads_lvl"]),
                "relative_abundance_all":  float(row["relative_abundance_all"]),
                "relative_abundance_lvl":  float(row["relative_abundance_lvl"]),
            }
        )

        if len(batch) >= BATCH_SIZE:
            db.bulk_insert_mappings(TaxonomyAbundance, batch)
            db.commit()
            inserted += len(batch)
            elapsed = time.time() - t0
            logger.info(
                "  已写入 %d / %d 行（%.1f%%）  耗时 %.1fs",
                inserted, total_rows, 100 * inserted / total_rows, elapsed,
            )
            batch.clear()

    # 写入剩余不足一批的数据
    if batch:
        db.bulk_insert_mappings(TaxonomyAbundance, batch)
        db.commit()
        inserted += len(batch)

    elapsed_total = time.time() - t0
    logger.info(
        "Abundance 导入完成：写入 %d 行，"
        "跳过（无 sample）%d 行，跳过（无 taxon）%d 行。总耗时 %.1fs。",
        inserted, skipped_sample, skipped_taxon, elapsed_total,
    )
    return inserted


# ---------------------------------------------------------------------------
# 统计摘要
# ---------------------------------------------------------------------------

def print_summary(db: Session) -> None:
    n_samples   = db.query(Sample).count()
    n_taxa      = db.query(Taxon).count()
    n_abundance = db.query(TaxonomyAbundance).count()

    logger.info("=" * 55)
    logger.info("导入统计摘要")
    logger.info("  samples              : %d", n_samples)
    logger.info("  taxa                 : %d", n_taxa)
    logger.info("  taxonomy_abundance   : %d", n_abundance)
    logger.info("=" * 55)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_import(
    samples_path: Path,
    abundance_path: Path,
    database_url: str,
    reset: bool,
) -> None:
    # 检查文件存在
    for p in (samples_path, abundance_path):
        if not p.exists():
            logger.error("文件不存在：%s", p)
            sys.exit(1)

    logger.info("数据库连接：%s", database_url)
    engine, SessionFactory = _make_engine_and_session(database_url)

    if reset:
        _reset_database(engine)
    else:
        _ensure_tables(engine)

    # 读取 abundance CSV（一次性读入，节省反复 I/O）
    logger.info("读取 abundance 长表：%s", abundance_path)
    abundance_df = pd.read_csv(abundance_path, dtype={"taxid": str, "sample_id": str})
    logger.info("abundance 长表：%d 行", len(abundance_df))

    db: Session = SessionFactory()
    try:
        sample_id_to_pk = import_samples(db, samples_path)
        taxon_key_to_pk = import_taxa(db, abundance_df)
        import_abundance(db, abundance_df, sample_id_to_pk, taxon_key_to_pk)
        print_summary(db)
    except Exception as exc:
        db.rollback()
        logger.exception("导入过程中发生致命错误：%s", exc)
        sys.exit(1)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 samples.csv 和 taxonomy_abundance_long.csv 导入 EAAM 数据库。"
    )
    parser.add_argument(
        "--samples",
        default=DEFAULT_SAMPLES_PATH,
        help=f"samples CSV 路径。默认：{DEFAULT_SAMPLES_PATH}",
    )
    parser.add_argument(
        "--abundance",
        default=DEFAULT_ABUNDANCE_PATH,
        help=f"abundance 长表 CSV 路径。默认：{DEFAULT_ABUNDANCE_PATH}",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        help=f"SQLAlchemy 数据库 URL。默认：{DEFAULT_DATABASE_URL}（可通过 DATABASE_URL 环境变量覆盖）",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空并重建数据库后再导入（⚠ 会删除所有现有数据）。",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"批量插入大小。默认：{BATCH_SIZE}",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.getLogger().setLevel(args.log_level)

    global BATCH_SIZE
    BATCH_SIZE = args.batch_size

    logger.info("=== EAAM 数据库导入开始 ===")
    t_start = time.time()

    run_import(
        samples_path=Path(args.samples),
        abundance_path=Path(args.abundance),
        database_url=args.database_url,
        reset=args.reset,
    )

    logger.info("=== 导入完成，总耗时 %.1fs ===", time.time() - t_start)


if __name__ == "__main__":
    main()
