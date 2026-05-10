#!/usr/bin/env python3
"""
convert_kraken2_to_long.py
--------------------------
将 Kraken2 宽表（wide format）转换为分析友好的长表（long format）CSV。

输入示例列名：
    perc, tot_all, tot_lvl, GX_Tang_1_all, GX_Tang_1_lvl, ..., lvl_type, taxid, name

输出字段：
    sample_id, taxid, name, lvl_type, rank, reads_all, reads_lvl,
    relative_abundance_all, relative_abundance_lvl

用法：
    python scripts/convert_kraken2_to_long.py
    python scripts/convert_kraken2_to_long.py --input data/raw/kraken2_raw.tsv --output data/processed/taxonomy_abundance_long.csv
"""

import argparse
import logging
import os
import sys
import warnings
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量：lvl_type → rank 映射
# ---------------------------------------------------------------------------
RANK_MAP: dict[str, str] = {
    "U":  "unclassified",
    "R":  "root",
    "R1": "root_sublevel",
    "R2": "domain",
    "K":  "kingdom",
    "P":  "phylum",
    "C":  "class",
    "O":  "order",
    "F":  "family",
    "G":  "genus",
    "G1": "genus_sublevel",
    "S":  "species",
}

# Kraken2 宽表中固定存在的非样品列
FIXED_COLS = {"perc", "tot_all", "tot_lvl", "lvl_type", "taxid", "name"}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _extract_sample_ids(columns: list[str]) -> list[str]:
    """
    从列名中识别所有以 _all 结尾的样品列，并提取 sample_id 前缀。
    例如：GX_Tang_1_all -> GX_Tang_1
    """
    sample_ids = []
    for col in columns:
        if col.endswith("_all") and col not in FIXED_COLS:
            sample_id = col[: -len("_all")]
            # 验证对应的 _lvl 列也存在
            lvl_col = f"{sample_id}_lvl"
            if lvl_col in columns:
                sample_ids.append(sample_id)
            else:
                logger.warning(
                    "列 '%s' 存在但未找到对应的 '%s'，跳过该样品。",
                    col,
                    lvl_col,
                )
    return sample_ids


def _compute_total_reads(df: pd.DataFrame, sample_id: str) -> float:
    """
    计算样品的总 reads（用于相对丰度分母）。

    优先使用 root 行（lvl_type == 'R'）的 reads_all 值。
    如果找不到 root 行，使用该样品 reads_all 的最大值，并发出 warning。
    """
    all_col = f"{sample_id}_all"

    root_mask = df["lvl_type"].str.strip() == "R"
    root_rows = df.loc[root_mask, all_col]

    if not root_rows.empty:
        total = float(root_rows.iloc[0])
        if total > 0:
            return total
        logger.warning(
            "样品 '%s' 的 root 行 reads_all 为 0，回退到最大值策略。", sample_id
        )

    # 回退策略
    warnings.warn(
        f"样品 '{sample_id}' 未找到有效的 root 行（lvl_type='R'），"
        f"使用该样品 reads_all 的最大值作为分母。",
        UserWarning,
        stacklevel=4,
    )
    max_val = float(df[all_col].max())
    if max_val == 0:
        logger.error("样品 '%s' 所有 reads_all 均为 0，相对丰度将全部为 NaN。", sample_id)
        return float("nan")
    return max_val


# ---------------------------------------------------------------------------
# 核心转换函数
# ---------------------------------------------------------------------------

def convert_wide_to_long(input_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    """
    读取 Kraken2 宽表，转换为长表，写出 CSV，并返回 DataFrame。

    Parameters
    ----------
    input_path  : Kraken2 宽表路径（TSV 格式）
    output_path : 输出长表路径（CSV 格式）

    Returns
    -------
    pd.DataFrame  转换后的长表
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    # ------------------------------------------------------------------
    # 1. 读取输入文件
    # ------------------------------------------------------------------
    if not input_path.exists():
        logger.error("输入文件不存在：%s", input_path)
        sys.exit(1)

    logger.info("读取 Kraken2 宽表：%s", input_path)
    try:
        df = pd.read_csv(input_path, sep="\t", dtype={"taxid": str})
    except Exception as exc:
        logger.error("读取文件失败：%s", exc)
        sys.exit(1)

    logger.info("宽表大小：%d 行 × %d 列", *df.shape)

    # ------------------------------------------------------------------
    # 2. 基础校验
    # ------------------------------------------------------------------
    required_cols = {"lvl_type", "taxid", "name"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.error("宽表缺少必要列：%s", missing)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. 清洗固定列
    # ------------------------------------------------------------------
    df["name"] = df["name"].astype(str).str.strip()
    df["taxid"] = df["taxid"].astype(str).str.strip()
    df["lvl_type"] = df["lvl_type"].astype(str).str.strip()

    # ------------------------------------------------------------------
    # 4. 识别样品列
    # ------------------------------------------------------------------
    sample_ids = _extract_sample_ids(list(df.columns))
    if not sample_ids:
        logger.error("未在宽表中找到任何有效的样品列（以 _all / _lvl 结尾）。")
        sys.exit(1)

    logger.info("识别到 %d 个样品：%s … ", len(sample_ids), sample_ids[:3])

    # ------------------------------------------------------------------
    # 5. 逐样品转换为长表
    # ------------------------------------------------------------------
    records: list[dict] = []

    for sample_id in sample_ids:
        all_col = f"{sample_id}_all"
        lvl_col = f"{sample_id}_lvl"

        total_reads = _compute_total_reads(df, sample_id)
        logger.debug("样品 '%s' 总 reads = %.0f", sample_id, total_reads)

        for _, row in df.iterrows():
            reads_all = float(row[all_col])
            reads_lvl = float(row[lvl_col])

            # 跳过 reads_all == 0 且 reads_lvl == 0 的行（节省存储）
            if reads_all == 0 and reads_lvl == 0:
                continue

            lvl_type_raw = row["lvl_type"]
            rank = RANK_MAP.get(lvl_type_raw, lvl_type_raw)  # 未知 lvl_type 原样保留

            if pd.isna(total_reads) or total_reads == 0:
                rel_all = float("nan")
                rel_lvl = float("nan")
            else:
                rel_all = reads_all / total_reads
                rel_lvl = reads_lvl / total_reads

            records.append(
                {
                    "sample_id":               sample_id,
                    "taxid":                   row["taxid"],
                    "name":                    row["name"],
                    "lvl_type":                lvl_type_raw,
                    "rank":                    rank,
                    "reads_all":               reads_all,
                    "reads_lvl":               reads_lvl,
                    "relative_abundance_all":  rel_all,
                    "relative_abundance_lvl":  rel_lvl,
                }
            )

    if not records:
        logger.warning("转换后长表为空，没有写出任何行。")
        return pd.DataFrame()

    long_df = pd.DataFrame(records)
    logger.info("长表共 %d 行（已跳过 reads 均为 0 的记录）。", len(long_df))

    # ------------------------------------------------------------------
    # 6. 写出 CSV
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        long_df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info("长表已写出：%s", output_path)
    except Exception as exc:
        logger.error("写出文件失败：%s", exc)
        sys.exit(1)

    # 简单统计摘要
    logger.info(
        "摘要 | 样品数：%d | 唯一 taxid 数：%d | rank 分布：\n%s",
        long_df["sample_id"].nunique(),
        long_df["taxid"].nunique(),
        long_df["rank"].value_counts().to_string(),
    )

    return long_df


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 Kraken2 宽表 TSV 转换为长表 CSV（用于 EAAM 数据库导入）。"
    )
    parser.add_argument(
        "--input",
        default="data/raw/kraken2_raw.tsv",
        help="输入 Kraken2 宽表路径（TSV）。默认：data/raw/kraken2_raw.tsv",
    )
    parser.add_argument(
        "--output",
        default="data/processed/taxonomy_abundance_long.csv",
        help="输出长表路径（CSV）。默认：data/processed/taxonomy_abundance_long.csv",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别，默认 INFO。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.getLogger().setLevel(args.log_level)

    logger.info("=== Kraken2 宽表 → 长表转换开始 ===")
    convert_wide_to_long(args.input, args.output)
    logger.info("=== 转换完成 ===")


if __name__ == "__main__":
    main()
