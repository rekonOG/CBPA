import pandas as pd
from app.services.inference import run_segmentation, load_inference_artifacts
from pathlib import Path

def debug_segmentation():
    df = pd.read_csv("../dataset/customers_50k.csv")
    artifacts = load_inference_artifacts(Path("models"), "v1")
    
    res = run_segmentation(df, artifacts, df)
    
    print("Segment counts:")
    for segment in res.segment_mix:
        print(f"{segment['name']}: {segment['value']}")
        
    print(res.customers.head())
    
if __name__ == "__main__":
    debug_segmentation()
