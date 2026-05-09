from sqlalchemy import Column, String, Float, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import Base

class Sample(Base):
    __tablename__ = "samples"

    id = Column(String, primary_key=True, index=True) # sample_id
    province = Column(String, index=True)
    region = Column(String, index=True)
    dynasty = Column(String, index=True)
    period = Column(String)
    estimated_year = Column(Float)
    sex = Column(String, index=True)
    subsistence_pattern = Column(String, index=True)
    site_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    source = Column(String)

    taxa = relationship("SampleTaxon", back_populates="sample")


class Taxonomy(Base):
    __tablename__ = "taxonomy"

    taxid = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    rank = Column(String, index=True)

    samples = relationship("SampleTaxon", back_populates="taxonomy")


class SampleTaxon(Base):
    __tablename__ = "sample_taxa"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sample_id = Column(String, ForeignKey("samples.id"), index=True)
    taxid = Column(String, ForeignKey("taxonomy.taxid"), index=True)
    
    lvl_type = Column(String)
    reads_all = Column(Float)
    reads_lvl = Column(Float)
    relative_abundance_all = Column(Float)
    relative_abundance_lvl = Column(Float)

    sample = relationship("Sample", back_populates="taxa")
    taxonomy = relationship("Taxonomy", back_populates="samples")

    __table_args__ = (
        Index('idx_sample_taxid', 'sample_id', 'taxid'),
    )
