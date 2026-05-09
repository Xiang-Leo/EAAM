# EAAM: Ancient Chinese Dental Calculus Microbiome Database

EAAM is a scientific data website MVP built to query, filter, and visualize the microbial composition of ancient Chinese dental calculus samples based on Kraken2 classification results.

## Setup Instructions

### 1. Generate Mock Data and Import
If you don't have the original `samples.csv` and `kraken2_raw.tsv`, you can generate mock data for testing:

```bash
# Create virtual environment and install requirements
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt pandas

# Generate mock data
python scripts/generate_mock_data.py

# Import data into SQLite database
python scripts/import_data.py
```

### 2. Run with Docker Compose

Ensure Docker is installed, then run:

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs

### 3. Run Locally (Development)

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Architecture

- **Backend**: FastAPI, SQLAlchemy, SQLite (compatible with PostgreSQL)
- **Frontend**: Next.js (App Router), Tailwind CSS, ECharts
- **Data**: Preprocessed via Pandas into a normalized database structure.
