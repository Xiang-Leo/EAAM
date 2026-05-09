import pandas as pd
import numpy as np
import os

def generate_mock_data():
    os.makedirs('data', exist_ok=True)
    
    # 1. Generate samples.csv
    np.random.seed(42)
    n_samples = 50
    sample_ids = [f'SAMP_{i:03d}' for i in range(1, n_samples + 1)]
    provinces = ['Shaanxi', 'Henan', 'Shandong', 'Sichuan', 'Guangdong']
    regions = ['North', 'Central', 'East', 'Southwest', 'South']
    dynasties = ['Shang', 'Zhou', 'Han', 'Tang', 'Ming']
    sexes = ['M', 'F', 'Unknown']
    subsistence = ['Agriculture', 'Pastoralism', 'Mixed']
    
    samples_data = {
        'sample_id': sample_ids,
        'province': np.random.choice(provinces, n_samples),
        'region': np.random.choice(regions, n_samples),
        'dynasty': np.random.choice(dynasties, n_samples),
        'period': ['Late'] * n_samples,
        'estimated_year': np.random.randint(-1000, 1500, n_samples),
        'sex': np.random.choice(sexes, n_samples, p=[0.4, 0.4, 0.2]),
        'subsistence_pattern': np.random.choice(subsistence, n_samples),
        'site_name': [f'Site_{chr(65+i%26)}' for i in range(n_samples)],
        'latitude': np.random.uniform(20.0, 40.0, n_samples),
        'longitude': np.random.uniform(100.0, 120.0, n_samples),
        'source': ['Mock Data'] * n_samples
    }
    
    samples_df = pd.DataFrame(samples_data)
    samples_df.to_csv('data/samples.csv', index=False)
    print("Generated data/samples.csv")
    
    # 2. Generate kraken2_raw.tsv
    n_taxa = 100
    taxids = [str(i) for i in range(1000, 1000 + n_taxa)]
    ranks = ['D', 'P', 'C', 'O', 'F', 'G', 'S'] * 15
    ranks = ranks[:n_taxa]
    names = [f'Taxon_{i}' for i in range(1000, 1000 + n_taxa)]
    
    kraken_data = {
        'perc': np.random.uniform(0, 10, n_taxa),
        'tot_all': np.random.randint(1000, 50000, n_taxa),
        'tot_lvl': np.random.randint(100, 10000, n_taxa),
        'lvl_type': ['-'] * n_taxa,
        'taxid': taxids,
        'name': names,
        'rank_custom': ranks # We'll replace with expected format later
    }
    
    # Add sample columns
    for sample_id in sample_ids:
        # Give some taxa zero reads
        reads_all = np.random.randint(0, 1000, n_taxa)
        mask = np.random.random(n_taxa) > 0.5
        reads_all[mask] = 0
        
        reads_lvl = (reads_all * np.random.uniform(0.1, 0.9, n_taxa)).astype(int)
        
        kraken_data[f'{sample_id}_all'] = reads_all
        kraken_data[f'{sample_id}_lvl'] = reads_lvl
        
    kraken_df = pd.DataFrame(kraken_data)
    
    # Rename rank_custom to rank for processing (in real data rank is not explicitly named, we map it. But let's assume it's in the table or can be mapped)
    # The prompt says: rank mapping rules: U -> unclassified, S -> species. We will put the original characters in a column.
    # Actually, Kraken report has a column typically named 'lvl_type' or similar for rank. The prompt says "lvl_type" is a column. Let's use 'lvl_type' as the rank column.
    kraken_df['lvl_type'] = ranks
    
    kraken_df.to_csv('data/kraken2_raw.tsv', sep='\t', index=False)
    print("Generated data/kraken2_raw.tsv")

if __name__ == '__main__':
    generate_mock_data()
