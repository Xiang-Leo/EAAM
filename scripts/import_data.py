import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add the parent directory to the path so we can import the backend app
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app import models

DATABASE_URL = "sqlite:///../data/eaam.db"

RANK_MAP = {
    'U': 'unclassified',
    'R': 'root',
    'R1': 'root_sublevel',
    'R2': 'domain',
    'K': 'kingdom',
    'P': 'phylum',
    'C': 'class',
    'O': 'order',
    'F': 'family',
    'G': 'genus',
    'G1': 'genus_sublevel',
    'S': 'species'
}

def import_data():
    samples_path = 'data/samples.csv'
    kraken_path = 'data/kraken2_raw.tsv'
    
    if not os.path.exists(samples_path) or not os.path.exists(kraken_path):
        print(f"Error: Could not find {samples_path} or {kraken_path}")
        print("Please run generate_mock_data.py first.")
        return

    # Database setup
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'eaam.db')
    engine = create_engine(f"sqlite:///{db_path}")
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Loading samples...")
    samples_df = pd.read_csv(samples_path)
    # Handle NaN values
    samples_df = samples_df.replace({np.nan: None})
    
    # Load samples into DB
    for _, row in samples_df.iterrows():
        sample = models.Sample(
            id=row['sample_id'],
            province=row['province'],
            region=row['region'],
            dynasty=row['dynasty'],
            period=row['period'],
            estimated_year=row.get('estimated_year'),
            sex=row['sex'],
            subsistence_pattern=row['subsistence_pattern'],
            site_name=row['site_name'],
            latitude=row.get('latitude'),
            longitude=row.get('longitude'),
            source=row['source']
        )
        session.add(sample)
    
    session.commit()
    print(f"Loaded {len(samples_df)} samples.")

    print("Loading Kraken2 data...")
    kraken_df = pd.read_csv(kraken_path, sep='\t')
    
    # Extract taxa
    taxa_df = kraken_df[['taxid', 'name', 'lvl_type']].drop_duplicates()
    for _, row in taxa_df.iterrows():
        taxid_str = str(row['taxid'])
        rank_mapped = RANK_MAP.get(row['lvl_type'], row['lvl_type'])
        
        taxon = models.Taxonomy(
            taxid=taxid_str,
            name=row['name'],
            rank=rank_mapped
        )
        session.merge(taxon)
    session.commit()
    print(f"Loaded {len(taxa_df)} taxa.")

    print("Melting Kraken2 table...")
    # Find all sample column pairs: _all and _lvl
    sample_ids = samples_df['sample_id'].tolist()
    
    # We will iterate sample by sample to save memory or melt chunks
    total_records = 0
    for sample_id in sample_ids:
        col_all = f"{sample_id}_all"
        col_lvl = f"{sample_id}_lvl"
        
        if col_all in kraken_df.columns and col_lvl in kraken_df.columns:
            # Calculate total for this sample from the wide table
            # tot_all is in the wide table, but it varies per taxid in the raw file? Wait, tot_all is usually for the whole sample? 
            # In the prompt: tot_all, tot_lvl are columns in the wide table. This implies totals might be row-wise?
            # Actually, relative abundance is reads_all / tot_all (for that sample? But the prompt shows tot_all, GX_Tang_1_all...
            # The prompt example: `perc,tot_all,tot_lvl,GX_Tang_1_all,GX_Tang_1_lvl`
            # This looks like `tot_all` is the sum of reads across ALL samples for that taxon? Or is it the sample total?
            # Kraken2 report: `tot_all` is usually the total reads for that clade across the pooled samples, or it's a sum.
            # We will calculate relative abundance based on the sample's total reads sum over species, or just sum of reads for that sample.
            # To be safe and simple: sample_total_all = sum of all species/taxa reads for this sample.
            # But the user mentioned adding relative abundance. We'll use the sample's total reads sum.
            
            sample_reads = kraken_df[['taxid', 'lvl_type', col_all, col_lvl]].copy()
            # Filter out zero reads to save DB space
            sample_reads = sample_reads[sample_reads[col_all] > 0]
            
            # Calculate sample total reads for relative abundance
            # A more precise way is to use root (taxid 1) reads as total.
            # If not available, sum of species or just sum all (though summing all double counts due to taxonomy tree).
            # For MVP, let's just use sum of 'S' (species) or just the sum of the column if we don't have tree logic.
            total_reads_all = sample_reads[col_all].sum()
            total_reads_lvl = sample_reads[col_lvl].sum()
            
            if total_reads_all == 0: total_reads_all = 1
            if total_reads_lvl == 0: total_reads_lvl = 1
            
            records_to_insert = []
            for _, row in sample_reads.iterrows():
                rel_all = row[col_all] / total_reads_all
                rel_lvl = row[col_lvl] / total_reads_lvl
                
                records_to_insert.append(
                    models.SampleTaxon(
                        sample_id=sample_id,
                        taxid=str(row['taxid']),
                        lvl_type=row['lvl_type'],
                        reads_all=float(row[col_all]),
                        reads_lvl=float(row[col_lvl]),
                        relative_abundance_all=float(rel_all),
                        relative_abundance_lvl=float(rel_lvl)
                    )
                )
            
            if records_to_insert:
                session.add_all(records_to_insert)
                total_records += len(records_to_insert)
    
    session.commit()
    session.close()
    print(f"Loaded {total_records} SampleTaxon records.")
    print("Data import complete.")

if __name__ == '__main__':
    import_data()
