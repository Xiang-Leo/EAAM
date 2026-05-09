import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app import models

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Insert mock data
    sample1 = models.Sample(id="S1", dynasty="Tang", region="North", sex="M")
    sample2 = models.Sample(id="S2", dynasty="Tang", region="South", sex="F")
    
    tax1 = models.Taxonomy(taxid="1", name="Taxon 1", rank="S")
    tax2 = models.Taxonomy(taxid="2", name="Taxon 2", rank="S")
    
    db.add_all([sample1, sample2, tax1, tax2])
    db.commit()
    
    st1 = models.SampleTaxon(sample_id="S1", taxid="1", reads_all=100, reads_lvl=50, relative_abundance_all=0.8, relative_abundance_lvl=0.5)
    st2 = models.SampleTaxon(sample_id="S1", taxid="2", reads_all=25, reads_lvl=10, relative_abundance_all=0.2, relative_abundance_lvl=0.1)
    db.add_all([st1, st2])
    db.commit()
    
    yield
    Base.metadata.drop_all(bind=engine)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to EAAM API"}

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
    assert data["items"][0]["id"] == "S2"

def test_get_sample_taxa():
    response = client.get("/api/samples/S1/taxa")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["taxid"] == "1" # Should be ordered by abundance

def test_get_taxon_distribution():
    response = client.get("/api/taxa/1/distribution")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["group_by"] == "Tang"
    assert data[0]["abundances"] == [0.8]
