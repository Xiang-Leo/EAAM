#!/usr/bin/env python3
"""
validate_data.py
----------------
检查 samples.csv 与 taxonomy_abundance_long.csv 的一致性与数据质量。

用法：
    python scripts/validate_data.py
    python scripts/validate_data.py \\
        --samples   data/raw/samples.csv \\
        --abundance data/processed/taxonomy_abundance_long.csv \\
        --report    data/processed/validation_report.txt

退出码：
    0  所有检查通过（或仅有 warning 级别问题）
    1  存在至少一个 ERROR 级别问题
"""

import argparse
import logging
import sys
from datetime import datetime
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
# 必要字段定义
# ---------------------------------------------------------------------------
REQUIRED_SAMPLE_COLS = {
    "sample_id", "province", "region", "dynasty", "sex", "subsistence_pattern"
}

REQUIRED_ABUNDANCE_COLS = {
    "sample_id", "taxid", "name", "lvl_type", "rank",
    "reads_all", "reads_lvl",
    "relative_abundance_all", "relative_abundance_lvl",
}

# ---------------------------------------------------------------------------
# 报告收集器
# ---------------------------------------------------------------------------

class ValidationReport:
    """收集所有检查结果，最后统一输出。"""

    def __init__(self) -> None:
        self.errors:   list[str] = []
        self.warnings: list[str] = []
        self.infos:    list[str] = []

    # ---- 记录方法 ----------------------------------------------------------
    def error(self, msg: str) -> None:
        self.errors.append(msg)
        logger.error(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning(msg)

    def info(self, msg: str) -> None:
        self.infos.append(msg)
        logger.info(msg)

    # ---- 汇总属性 ----------------------------------------------------------
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings)

    # ---- 生成报告文本 -------------------------------------------------------
    def render(self) -> str:
        lines: list[str] = []
        sep = "=" * 70

        lines.append(sep)
        lines.append("EAAM 数据验证报告")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(sep)
        lines.append("")

        # 汇总
        lines.append(f"[SUMMARY]  ERROR: {len(self.errors)}  |  WARNING: {len(self.warnings)}")
        lines.append("")

        # INFO
        if self.infos:
            lines.append("── 信息 (INFO) ──────────────────────────────────────────────────────")
            for msg in self.infos:
                lines.append(f"  ✓  {msg}")
            lines.append("")

        # WARNING
        if self.warnings:
            lines.append("── 警告 (WARNING) ───────────────────────────────────────────────────")
            for msg in self.warnings:
                lines.append(f"  ⚠  {msg}")
            lines.append("")

        # ERROR
        if self.errors:
            lines.append("── 错误 (ERROR) ─────────────────────────────────────────────────────")
            for msg in self.errors:
                lines.append(f"  ✗  {msg}")
            lines.append("")

        # 结论
        if self.has_errors:
            lines.append("【结论】数据存在严重错误，请修复后再导入数据库。")
        elif self.warnings:
            lines.append("【结论】数据存在轻微问题，建议核查后导入。")
        else:
            lines.append("【结论】所有检查通过，数据可以导入数据库。")

        lines.append(sep)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 各项检查函数
# ---------------------------------------------------------------------------

def check_samples(df: pd.DataFrame, report: ValidationReport) -> set[str]:
    """
    检查 samples.csv：
    1. 必要字段是否存在
    2. sample_id 是否有空值
    3. sample_id 是否有重复
    返回去重后的合法 sample_id 集合。
    """
    # 1. 必要字段
    missing_cols = REQUIRED_SAMPLE_COLS - set(df.columns)
    if missing_cols:
        report.error(f"samples.csv 缺少必要字段：{sorted(missing_cols)}")
        return set()
    else:
        report.info(f"samples.csv 字段完整（包含全部 {len(REQUIRED_SAMPLE_COLS)} 个必要字段）。")

    # 2. 空 sample_id
    null_mask = df["sample_id"].isna() | (df["sample_id"].astype(str).str.strip() == "")
    null_count = null_mask.sum()
    if null_count > 0:
        report.error(f"samples.csv 中有 {null_count} 行的 sample_id 为空（行号：{df.index[null_mask].tolist()}）。")
    else:
        report.info("samples.csv 无空 sample_id。")

    # 3. 重复 sample_id
    dup_mask = df["sample_id"].duplicated(keep=False)
    dup_ids = df.loc[dup_mask, "sample_id"].unique().tolist()
    if dup_ids:
        report.error(f"samples.csv 中有 {len(dup_ids)} 个重复 sample_id：{dup_ids[:10]}{'...' if len(dup_ids) > 10 else ''}。")
    else:
        report.info("samples.csv 无重复 sample_id。")

    valid_ids = set(df.loc[~null_mask, "sample_id"].astype(str).str.strip())
    report.info(f"samples.csv 共 {len(valid_ids)} 个有效样品。")
    return valid_ids


def check_abundance(df: pd.DataFrame, report: ValidationReport) -> set[str]:
    """
    检查 taxonomy_abundance_long.csv：
    1. 必要字段是否存在
    2. reads_all / reads_lvl 非负性
    3. relative_abundance 在 [0, 1] 范围
    返回 abundance 表中出现的 sample_id 集合。
    """
    # 1. 必要字段
    missing_cols = REQUIRED_ABUNDANCE_COLS - set(df.columns)
    if missing_cols:
        report.error(f"abundance 表缺少必要字段：{sorted(missing_cols)}")
        return set()
    else:
        report.info(f"abundance 表字段完整（包含全部 {len(REQUIRED_ABUNDANCE_COLS)} 个必要字段）。")

    report.info(f"abundance 表共 {len(df)} 行，{df['sample_id'].nunique()} 个唯一样品，{df['taxid'].nunique()} 个唯一 taxid。")

    # 2. reads_all 非负
    neg_all = (df["reads_all"] < 0).sum()
    if neg_all > 0:
        report.error(f"abundance 表中有 {neg_all} 行的 reads_all 为负数。")
    else:
        report.info("reads_all 全部为非负数。")

    # reads_lvl 非负
    neg_lvl = (df["reads_lvl"] < 0).sum()
    if neg_lvl > 0:
        report.error(f"abundance 表中有 {neg_lvl} 行的 reads_lvl 为负数。")
    else:
        report.info("reads_lvl 全部为非负数。")

    # reads_lvl <= reads_all（通常应满足）
    invalid_lvl = (df["reads_lvl"] > df["reads_all"]).sum()
    if invalid_lvl > 0:
        report.warning(f"有 {invalid_lvl} 行的 reads_lvl > reads_all（可能正常，但建议核查）。")

    # 3. relative_abundance_all 在 [0, 1]
    ra_all = df["relative_abundance_all"].dropna()
    out_of_range_all = ((ra_all < 0) | (ra_all > 1 + 1e-9)).sum()
    if out_of_range_all > 0:
        report.error(f"有 {out_of_range_all} 行的 relative_abundance_all 不在 [0, 1] 范围内。")
    else:
        report.info("relative_abundance_all 全部在 [0, 1] 范围内。")

    # relative_abundance_lvl 在 [0, 1]
    ra_lvl = df["relative_abundance_lvl"].dropna()
    out_of_range_lvl = ((ra_lvl < 0) | (ra_lvl > 1 + 1e-9)).sum()
    if out_of_range_lvl > 0:
        report.error(f"有 {out_of_range_lvl} 行的 relative_abundance_lvl 不在 [0, 1] 范围内。")
    else:
        report.info("relative_abundance_lvl 全部在 [0, 1] 范围内。")

    # NaN 值检查
    nan_ra_all = df["relative_abundance_all"].isna().sum()
    if nan_ra_all > 0:
        report.warning(f"有 {nan_ra_all} 行的 relative_abundance_all 为 NaN（可能是总 reads 为 0 导致）。")

    return set(df["sample_id"].astype(str).str.strip().unique())


def check_sample_id_consistency(
    sample_ids: set[str],
    abundance_ids: set[str],
    report: ValidationReport,
) -> None:
    """
    检查两张表的 sample_id 交叉一致性：
    1. abundance 中有但 samples 中没有的 ID（孤立记录）
    2. samples 中有但 abundance 中没有的 ID（缺失数据）
    """
    orphan = abundance_ids - sample_ids
    if orphan:
        report.error(
            f"abundance 表中有 {len(orphan)} 个 sample_id 在 samples.csv 中不存在："
            f" {sorted(orphan)[:10]}{'...' if len(orphan) > 10 else ''}。"
        )
    else:
        report.info("abundance 表中的所有 sample_id 均存在于 samples.csv。")

    missing = sample_ids - abundance_ids
    if missing:
        report.warning(
            f"samples.csv 中有 {len(missing)} 个 sample_id 在 abundance 表中没有数据："
            f" {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}。"
        )
    else:
        report.info("samples.csv 中的所有 sample_id 均在 abundance 表中有数据。")


def check_abundance_sanity(df: pd.DataFrame, report: ValidationReport) -> None:
    """
    检查每个样品 root/domain 层面的 abundance 合理性：
    - 对每个样品，root 行（rank='root'）或 domain 行（rank='domain'）的
      relative_abundance_all 之和应接近 1.0（允许 ±0.1 的误差）。
    - 如果样品没有 root/domain 行，则跳过并给出 warning。
    """
    top_ranks = {"root", "domain", "unclassified"}
    top_df = df[df["rank"].isin(top_ranks)].copy()

    if top_df.empty:
        report.warning("abundance 表中没有 root / domain / unclassified 级别的行，跳过合理性检查。")
        return

    # 按样品汇总顶层 abundance
    per_sample = (
        top_df.groupby("sample_id")["relative_abundance_all"]
        .sum()
        .reset_index()
        .rename(columns={"relative_abundance_all": "top_sum"})
    )

    # 找出顶层 abundance 之和明显异常的样品
    TOLERANCE = 0.15  # 允许 15% 误差
    anomalies = per_sample[
        (per_sample["top_sum"] < 1.0 - TOLERANCE) |
        (per_sample["top_sum"] > 1.0 + TOLERANCE)
    ]

    if anomalies.empty:
        report.info(
            f"已检查 {len(per_sample)} 个样品的顶层 abundance 合理性，均在 [0.85, 1.15] 范围内。"
        )
    else:
        for _, row in anomalies.iterrows():
            report.warning(
                f"样品 '{row['sample_id']}' 的顶层（root/domain/unclassified）"
                f" relative_abundance 之和为 {row['top_sum']:.4f}，偏离 1.0 超过 {TOLERANCE:.0%}。"
            )

    # 没有任何顶层行的样品
    samples_with_top = set(top_df["sample_id"].unique())
    all_samples = set(df["sample_id"].unique())
    no_top = all_samples - samples_with_top
    if no_top:
        report.warning(
            f"以下 {len(no_top)} 个样品没有 root/domain/unclassified 行，无法做顶层合理性检查："
            f" {sorted(no_top)[:10]}{'...' if len(no_top) > 10 else ''}。"
        )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_validation(
    samples_path: Path,
    abundance_path: Path,
    report_path: Path,
) -> ValidationReport:
    report = ValidationReport()
    report.info(f"samples 文件：{samples_path}")
    report.info(f"abundance 文件：{abundance_path}")
    report.info(f"报告输出：{report_path}")

    # ------------------------------------------------------------------
    # 读取文件
    # ------------------------------------------------------------------
    def _load(path: Path, sep: str = ",") -> pd.DataFrame | None:
        if not path.exists():
            report.error(f"文件不存在：{path}")
            return None
        try:
            df = pd.read_csv(path, sep=sep, dtype=str)
            # 尝试将数值列转回数值
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass
            return df
        except Exception as exc:
            report.error(f"读取文件失败 {path}：{exc}")
            return None

    samples_df   = _load(samples_path)
    abundance_df = _load(abundance_path)

    if samples_df is None or abundance_df is None:
        return report  # 文件级别错误，无法继续

    # ------------------------------------------------------------------
    # 各项检查（不提前 return，尽量收集所有问题）
    # ------------------------------------------------------------------
    report.info("── 开始检查 samples.csv ──────────────────────────")
    sample_ids = check_samples(samples_df, report)

    report.info("── 开始检查 abundance 表 ─────────────────────────")
    abundance_ids = check_abundance(abundance_df, report)

    if sample_ids and abundance_ids:
        report.info("── 开始交叉一致性检查 ────────────────────────────")
        check_sample_id_consistency(sample_ids, abundance_ids, report)

        report.info("── 开始顶层 abundance 合理性检查 ─────────────────")
        check_abundance_sanity(abundance_df, report)

    return report


def write_report(report: ValidationReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    text = report.render()
    try:
        report_path.write_text(text, encoding="utf-8")
        logger.info("验证报告已写出：%s", report_path)
    except Exception as exc:
        logger.error("写出报告失败：%s", exc)
    # 同时打印到终端
    print("\n" + text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="验证 EAAM 数据文件一致性与质量，输出 validation_report.txt。"
    )
    parser.add_argument(
        "--samples",
        default="data/raw/samples.csv",
        help="samples.csv 路径。默认：data/raw/samples.csv",
    )
    parser.add_argument(
        "--abundance",
        default="data/processed/taxonomy_abundance_long.csv",
        help="长表 abundance CSV 路径。默认：data/processed/taxonomy_abundance_long.csv",
    )
    parser.add_argument(
        "--report",
        default="data/processed/validation_report.txt",
        help="验证报告输出路径。默认：data/processed/validation_report.txt",
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

    logger.info("=== EAAM 数据验证开始 ===")

    report = run_validation(
        samples_path=Path(args.samples),
        abundance_path=Path(args.abundance),
        report_path=Path(args.report),
    )

    write_report(report, Path(args.report))

    logger.info("=== 验证完成：%d ERROR, %d WARNING ===", len(report.errors), len(report.warnings))

    sys.exit(1 if report.has_errors else 0)


if __name__ == "__main__":
    main()
