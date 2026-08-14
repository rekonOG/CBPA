import pandas as pd
import json
import joblib
import os
import sys

# Add the app directory to the python path so we can import from it
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.inference import _prepare_feature_frame, DEFAULT_FEATURE_COLUMNS
from app.services.ml_algorithm import select_best_unsupervised_model
from app.services.product_analysis import cluster_products

def train_customer_model(dataset_path, output_model_path, output_features_path):
    print(f"\n--- Training Customer Model on {dataset_path} ---")
    
    # 1. Load Data
    try:
        df = pd.read_csv(dataset_path)
        print(f"Loaded {len(df)} rows.")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    # 2. Prepare Feature Frame
    feature_columns = DEFAULT_FEATURE_COLUMNS.copy()
    feature_frame = _prepare_feature_frame(df, feature_columns)
    
    # 3. Select and train the best model
    print(f"Running model competition (K-Means vs Agglomerative vs DBSCAN)...")
    # Note: select_best_unsupervised_model scales the data internally
    selection_result = select_best_unsupervised_model(feature_frame)
    
    best_algo = selection_result.selected_algorithm
    best_score = selection_result.best_silhouette_score
    print(f"Winner: {best_algo} (Silhouette Score: {best_score})")
    print("Candidates evaluated:")
    for score in selection_result.candidate_scores:
        print(f"  - {score['algorithm']}: Score={score['silhouetteScore']}, Clusters={score['clusterCount']}, Noise={score.get('noisePoints', 0)}")
    
    # In order to save the model, we actually need to train a scikit-learn estimator object.
    # Our backend function select_best_unsupervised_model currently returns the *labels*, not the model object.
    # So we'll train a fresh model using the winning algorithm here to save it.
    from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    
    # Prepare matrix
    matrix = feature_frame.to_numpy(dtype=float)
    
    scaler = StandardScaler()
    scaled_matrix = scaler.fit_transform(matrix)
    
    if best_algo == "kmeans":
        model = KMeans(n_clusters=4, random_state=42, n_init=10)
    elif best_algo == "agglomerative":
        model = AgglomerativeClustering(n_clusters=4)
    elif best_algo == "dbscan":
        model = DBSCAN(eps=0.7, min_samples=3)
    else:
        # Fallback
        model = KMeans(n_clusters=4, random_state=42, n_init=10)
        
    print(f"Training {model.__class__.__name__} to save...")
    model.fit(scaled_matrix)
    
    # 4. Save Artifacts
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    
    joblib.dump(model, output_model_path)
    joblib.dump(scaler, output_model_path.replace("model.joblib", "preprocessor.joblib").replace("model_100k.joblib", "preprocessor_100k.joblib"))
    
    with open(output_features_path, "w") as f:
        json.dump(feature_columns, f)
        
    print(f"Successfully saved model to {output_model_path}")


def analyze_product_dataset(dataset_path):
    print(f"\n--- Analyzing Product Dataset on {dataset_path} ---")
    try:
        df = pd.read_csv(dataset_path)
        print(f"Loaded {len(df)} rows.")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return
        
    result = cluster_products(df)
    if result["available"]:
        print(f"Successfully clustered products. Found {result['optimalClusters']} clusters.")
        for profile in result["clusterProfiles"]:
            print(f"  - Cluster {profile['cluster_id']} ({profile['movement_label']}): {profile['products']} products, Avg Rev: ${profile['avg_total_revenue']}")
    else:
        print(f"Clustering failed: {result.get('warnings')}")

if __name__ == "__main__":
    # Test on 50k
    train_customer_model(
        "../dataset/customers_50k.csv", 
        "models/model.joblib", 
        "models/feature_columns.json"
    )
    
    # Test on 100k
    train_customer_model(
        "../dataset/customers_100k.csv", 
        "models/model_100k.joblib", 
        "models/feature_columns_100k.json"
    )
    
    # Test product clustering on 50k and 100k
    analyze_product_dataset("../dataset/products_50k.csv")
    analyze_product_dataset("../dataset/products_100k.csv")
    
    print("\nTraining completed.")
