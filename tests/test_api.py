import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 必须在导入 app.main 之前设置 PYTHONPATH 保证正确引用
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.main import app
from app.database import get_db, Base
from app.models import Sample, Taxon, TaxonomyAbundance

# 使用临时内存 SQLite 数据库用于测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 覆盖 get_db 依赖
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    # 每次测试前建表
    Base.metadata.create_all(bind=engine)
    
    # 注入假数据用于后续路由测试
    db = TestingSessionLocal()
    
    sample1 = Sample(sample_id="Test_1", dynasty="Tang", province="Shaanxi", sex="M", estimated_year=700)
    sample2 = Sample(sample_id="Test_2", dynasty="Han", province="Henan", sex="F", estimated_year=100)
    db.add(sample1)
    db.add(sample2)
    
    taxon1 = Taxon(taxid="111", name="Streptococcus", lvl_type="G", rank="genus")
    taxon2 = Taxon(taxid="222", name="Streptococcus mutans", lvl_type="S", rank="species")
    db.add(taxon1)
    db.add(taxon2)
    
    db.commit()
    
    # 建立丰度关联
    abund1 = TaxonomyAbundance(
        sample_id=sample1.id, taxon_id=taxon1.id, 
        reads_all=100, reads_lvl=50, 
        relative_abundance_all=0.5, relative_abundance_lvl=0.25
    )
    abund2 = TaxonomyAbundance(
        sample_id=sample2.id, taxon_id=taxon1.id, 
        reads_all=200, reads_lvl=100, 
        relative_abundance_all=0.8, relative_abundance_lvl=0.4
    )
    db.add(abund1)
    db.add(abund2)
    db.commit()
    
    yield  # 运行测试
    
    # 测试后清空表
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    """验证 GET /health 返回 ok"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_summary():
    """验证 GET /api/summary 在有数据和空数据下均不报错"""
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["sample_count"] == 2
    assert data["taxon_count"] == 2
    assert data["abundance_count"] == 2
    
    # 校验朝代分布是否正确统计
    dynasty_dist = {d["group"]: d["count"] for d in data["dynasty_distribution"]}
    assert dynasty_dist.get("Tang") == 1
    assert dynasty_dist.get("Han") == 1


def test_get_samples():
    """验证 GET /api/samples 返回 total 和 items，且支持基础参数过滤"""
    # 1. 查全部
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    
    # 2. 查唐代
    response_tang = client.get("/api/samples?dynasty=Tang")
    data_tang = response_tang.json()
    assert data_tang["total"] == 1
    assert data_tang["items"][0]["sample_id"] == "Test_1"


def test_search_taxa():
    """验证 GET /api/taxa/search 可搜索 taxon"""
    # 搜索包含 "Strep" 的 taxon
    response = client.get("/api/taxa/search?q=Strep")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # 应该返回 Streptococcus 和 Streptococcus mutans
    
    # 测试附带 rank 过滤
    response_species = client.get("/api/taxa/search?q=Strep&rank=species")
    data_species = response_species.json()
    assert len(data_species) == 1
    assert data_species[0]["name"] == "Streptococcus mutans"


def test_get_top_taxa():
    """验证 GET /api/taxa/top 可正确返回 top taxa（涵盖平均丰度计算逻辑）"""
    # 获取 genus 级别的 top taxa
    response = client.get("/api/taxa/top?rank=genus")
    assert response.status_code == 200
    data = response.json()
    
    # 数据库里只有 Streptococcus 是 genus，应该只返回这 1 个
    assert len(data) == 1
    taxon = data[0]
    assert taxon["name"] == "Streptococcus"
    assert taxon["sample_count"] == 2
    
    # Streptococcus 在 Sample 1 (0.5) 和 Sample 2 (0.8)，均值为 (0.5+0.8)/2 = 0.65
    assert abs(taxon["mean_abundance"] - 0.65) < 1e-5
