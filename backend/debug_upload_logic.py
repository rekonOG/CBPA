import pandas as pd
from pathlib import Path
from app.services.inference import run_segmentation, load_inference_artifacts, _prepare_feature_frame, _prepare_engineered_feature_frame, _predict_with_artifacts
from app.services.data_preprocessing import InputPreprocessor
from app.services.preprocess import build_customer_frame

def debug():
    print("Loading 50k dataset...")
    with open("../dataset/customers_50k.csv", "rb") as f:
        file_bytes = f.read()
        
    input_preprocessor = InputPreprocessor()
    raw_frame, engineered_frame, engineered_input_array = input_preprocessor.load_uploaded_file(
        "customers_50k.csv",
        file_bytes,
    )
    
    customers, quality = build_customer_frame(raw_frame)
    artifacts = load_inference_artifacts(Path("models"), "v1")
    
    print(f"engineered_frame columns: {list(engineered_frame.columns)}")
    print(f"artifacts.feature_columns: {artifacts.feature_columns}")
    
    working = customers.copy()
    feature_frame_for_model = _prepare_feature_frame(working, artifacts.feature_columns)
    
    print(f"feature_frame_for_model columns: {list(feature_frame_for_model.columns)}")
    
    engineered_feature_frame = _prepare_engineered_feature_frame(engineered_frame)
    
    prediction_frames = [frame for frame in [feature_frame_for_model, engineered_feature_frame] if frame is not None]
    
    for i, prediction_frame in enumerate(prediction_frames):
        print(f"\nTrying prediction frame {i}...")
        try:
            raw_clusters = _predict_with_artifacts(prediction_frame, artifacts)
            print(f"Success! Found {len(set(raw_clusters))} unique clusters.")
            print(f"Cluster counts: {pd.Series(raw_clusters).value_counts().to_dict()}")
            break
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    debug()
