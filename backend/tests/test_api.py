import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models

# Use an in-memory SQLite database for testing.
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Insert mock data
    sample1 = models.Sample(sample_id="S1", dynasty="Tang", region="North", sex="M")
    sample2 = models.Sample(sample_id="S2", dynasty="Tang", region="South", sex="F")
    
    tax1 = models.Taxon(taxid="1", name="Taxon 1", lvl_type="S", rank="species")
    tax2 = models.Taxon(taxid="2", name="Taxon 2", lvl_type="S", rank="species")
    
    db.add_all([sample1, sample2, tax1, tax2])
    db.commit()
    
    st1 = models.TaxonomyAbundance(
        sample_id=sample1.id,
        taxon_id=tax1.id,
        reads_all=100,
        reads_lvl=50,
        relative_abundance_all=0.8,
        relative_abundance_lvl=0.5,
    )
    st2 = models.TaxonomyAbundance(
        sample_id=sample1.id,
        taxon_id=tax2.id,
        reads_all=25,
        reads_lvl=10,
        relative_abundance_all=0.2,
        relative_abundance_lvl=0.1,
    )
    db.add_all([st1, st2])
    db.commit()
    
    yield
    Base.metadata.drop_all(bind=engine)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to EAAM API"

def test_get_samples():
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

def test_get_samples_filter():
    response = client.get("/api/samples?sex=F")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["sample_id"] == "S2"

def test_get_sample_taxa():
    response = client.get("/api/samples/S1/taxa?rank=species")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["taxid"] == "1" # Should be ordered by abundance

def test_get_taxon_distribution():
    response = client.get("/api/taxa/1/distribution")
    assert response.status_code == 200
    data = response.json()
    assert data["group_by"] == "dynasty"
    assert data["data"][0]["group"] == "Tang"
    assert data["data"][0]["mean_abundance"] == 0.4
    assert data["data"][0]["sample_count"] == 2
