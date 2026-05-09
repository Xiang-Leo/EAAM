from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter()

@router.get("/samples", response_model=schemas.PaginatedSamples)
def get_samples(
    dynasty: Optional[str] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    sex: Optional[str] = None,
    subsistence_pattern: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Sample)
    
    if dynasty:
        query = query.filter(models.Sample.dynasty == dynasty)
    if region:
        query = query.filter(models.Sample.region == region)
    if province:
        query = query.filter(models.Sample.province == province)
    if sex:
        query = query.filter(models.Sample.sex == sex)
    if subsistence_pattern:
        query = query.filter(models.Sample.subsistence_pattern == subsistence_pattern)
        
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size
    }

@router.get("/samples/{sample_id}/taxa", response_model=List[schemas.SampleTaxonResponse])
def get_sample_taxa(
    sample_id: str,
    limit: int = Query(20, ge=1, le=100),
    rank: str = Query("S"), # Default to species
    db: Session = Depends(get_db)
):
    # Verify sample exists
    sample = db.query(models.Sample).filter(models.Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    taxa = db.query(models.SampleTaxon).join(models.Taxonomy).filter(
        models.SampleTaxon.sample_id == sample_id,
        models.Taxonomy.rank == rank
    ).order_by(desc(models.SampleTaxon.relative_abundance_all)).limit(limit).all()
    
    return taxa

@router.get("/taxa/{taxid}/distribution", response_model=List[schemas.TaxonDistributionItem])
def get_taxon_distribution(
    taxid: str,
    group_by: str = Query("dynasty", pattern="^(dynasty|region|province)$"),
    db: Session = Depends(get_db)
):
    # Verify taxon exists
    taxon = db.query(models.Taxonomy).filter(models.Taxonomy.taxid == taxid).first()
    if not taxon:
        raise HTTPException(status_code=404, detail="Taxon not found")

    # Get all sample taxa for this taxid, joined with sample metadata
    results = db.query(
        getattr(models.Sample, group_by).label("group_by_field"),
        models.SampleTaxon.relative_abundance_all
    ).join(models.SampleTaxon, models.Sample.id == models.SampleTaxon.sample_id)\
     .filter(models.SampleTaxon.taxid == taxid).all()
    
    # Process into lists by group
    distribution_dict = {}
    for group_val, abundance in results:
        if group_val is None:
            continue
        if group_val not in distribution_dict:
            distribution_dict[group_val] = []
        distribution_dict[group_val].append(abundance)
        
    return [{"group_by": k, "abundances": v} for k, v in distribution_dict.items()]

@router.get("/top-taxa", response_model=List[schemas.TopTaxonItem])
def get_top_taxa(
    group_by: str = Query("dynasty", pattern="^(dynasty|region)$"),
    group_value: str = Query(..., description="The specific dynasty or region to query"),
    rank: str = Query("S"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    # Find samples belonging to this group
    sample_query = db.query(models.Sample.id)
    if group_by == "dynasty":
        sample_query = sample_query.filter(models.Sample.dynasty == group_value)
    else:
        sample_query = sample_query.filter(models.Sample.region == group_value)
        
    sample_ids = [s[0] for s in sample_query.all()]
    
    if not sample_ids:
        return []

    # Calculate mean relative abundance for each taxon in these samples
    results = db.query(
        models.Taxonomy.taxid,
        models.Taxonomy.name,
        func.avg(models.SampleTaxon.relative_abundance_all).label("mean_abundance")
    ).join(models.SampleTaxon, models.Taxonomy.taxid == models.SampleTaxon.taxid)\
     .filter(
         models.SampleTaxon.sample_id.in_(sample_ids),
         models.Taxonomy.rank == rank
     )\
     .group_by(models.Taxonomy.taxid, models.Taxonomy.name)\
     .order_by(desc("mean_abundance"))\
     .limit(limit).all()
     
    return [{"taxid": r[0], "name": r[1], "mean_abundance": r[2]} for r in results]
