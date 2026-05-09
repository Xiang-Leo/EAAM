from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class SampleBase(BaseModel):
    id: str
    province: Optional[str] = None
    region: Optional[str] = None
    dynasty: Optional[str] = None
    period: Optional[str] = None
    estimated_year: Optional[float] = None
    sex: Optional[str] = None
    subsistence_pattern: Optional[str] = None
    site_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = None

class Sample(SampleBase):
    model_config = ConfigDict(from_attributes=True)

class TaxonomyBase(BaseModel):
    taxid: str
    name: str
    rank: str

class Taxonomy(TaxonomyBase):
    model_config = ConfigDict(from_attributes=True)

class SampleTaxonBase(BaseModel):
    sample_id: str
    taxid: str
    lvl_type: Optional[str] = None
    reads_all: float
    reads_lvl: float
    relative_abundance_all: float
    relative_abundance_lvl: float

class SampleTaxonResponse(SampleTaxonBase):
    taxonomy: Taxonomy
    model_config = ConfigDict(from_attributes=True)

class PaginatedSamples(BaseModel):
    items: List[Sample]
    total: int
    page: int
    size: int

class TaxonDistributionItem(BaseModel):
    group_by: str # e.g. dynasty or region value
    abundances: List[float] # array of relative abundances

class TopTaxonItem(BaseModel):
    taxid: str
    name: str
    mean_abundance: float
