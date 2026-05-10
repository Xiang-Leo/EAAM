import pandas as pd
import pytest
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.convert_kraken2_to_long import convert_wide_to_long

@pytest.fixture
def sample_kraken2_wide(tmp_path):
    """
    创建一个临时的 Kraken2 宽表文件用于测试。
    测试要求：
    - sample_id 识别 (SampleA, SampleB)
    - name 字段去除空格
    - lvl_type 正确映射 rank
    - relative abundance 正确计算 (使用 root 作为分母)
    """
    content = (
        "perc\ttot_all\ttot_lvl\tSampleA_all\tSampleA_lvl\tSampleB_all\tSampleB_lvl\tlvl_type\ttaxid\tname\n"
        "100.0\t1000\t0\t1000\t0\t500\t0\tR\t1\t root \n"
        "50.0\t500\t100\t500\t100\t250\t50\tG\t123\t  Streptococcus \n"
        "10.0\t100\t100\t100\t100\t50\t50\tS\t456\t Streptococcus mutans \n"
    )
    input_file = tmp_path / "test_raw.tsv"
    input_file.write_text(content, encoding="utf-8")
    return input_file

def test_convert_wide_to_long(sample_kraken2_wide, tmp_path):
    output_file = tmp_path / "output.csv"
    
    # 运行转换
    df = convert_wide_to_long(sample_kraken2_wide, output_file)
    
    # 验证文件是否生成
    assert output_file.exists()
    
    # 验证是否返回了正确的 dataframe
    assert not df.empty
    
    # 1. 能正确识别 sample_id
    sample_ids = df["sample_id"].unique()
    assert set(sample_ids) == {"SampleA", "SampleB"}
    
    # 2. 能正确生成 long table (2 samples * 3 taxa = 6 rows)
    assert len(df) == 6
    
    # 3. name 字段去除空格
    names = df["name"].unique()
    assert "root" in names
    assert "Streptococcus" in names
    assert "Streptococcus mutans" in names
    assert " root " not in names  # 原有的空格已被去除
    
    # 4. lvl_type 正确映射 rank
    ranks = set(df["rank"].unique())
    assert "root" in ranks       # R -> root
    assert "genus" in ranks      # G -> genus
    assert "species" in ranks    # S -> species
    
    # 5. relative abundance 正确计算
    # 对 SampleA: root_all = 1000. 
    #   Streptococcus (G): all = 500 (500/1000 = 0.5), lvl = 100 (100/1000 = 0.1)
    sample_a_strep = df[(df["sample_id"] == "SampleA") & (df["name"] == "Streptococcus")].iloc[0]
    assert sample_a_strep["reads_all"] == 500
    assert sample_a_strep["reads_lvl"] == 100
    assert sample_a_strep["relative_abundance_all"] == 0.5
    assert sample_a_strep["relative_abundance_lvl"] == 0.1

    # 对 SampleB: root_all = 500.
    #   Streptococcus mutans (S): all = 50 (50/500 = 0.1), lvl = 50 (50/500 = 0.1)
    sample_b_mutans = df[(df["sample_id"] == "SampleB") & (df["name"] == "Streptococcus mutans")].iloc[0]
    assert sample_b_mutans["reads_all"] == 50
    assert sample_b_mutans["reads_lvl"] == 50
    assert sample_b_mutans["relative_abundance_all"] == 0.1
    assert sample_b_mutans["relative_abundance_lvl"] == 0.1
