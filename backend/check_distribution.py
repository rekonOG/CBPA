import pandas as pd
import numpy as np

def check_distribution(file_path):
    print(f"Checking {file_path}")
    df = pd.read_csv(file_path)
    
    # Simulate backend heuristic scoring
    monetary = df['monetary']
    frequency = df['frequency']
    recency = df['recency']
    
    # Basic RFM visualization
    print(f"Recency: min={recency.min()}, max={recency.max()}, mean={recency.mean():.2f}")
    print(f"Frequency: min={frequency.min()}, max={frequency.max()}, mean={frequency.mean():.2f}")
    print(f"Monetary: min={monetary.min()}, max={monetary.max()}, mean={monetary.mean():.2f}")

    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    import joblib
    
    # Check predictions from our saved model!
    model = joblib.load("models/model.joblib")
    preprocessor = joblib.load("models/preprocessor.joblib")
    
    X = df[['recency', 'frequency', 'monetary', 'avgOrderValue', 'totalOrders']].fillna(0)
    X_scaled = preprocessor.transform(X)
    labels = model.predict(X_scaled)
    df['cluster'] = labels
    
    for c in range(4):
        cdf = df[df['cluster'] == c]
        print(f"\nCluster {c} ({len(cdf)} rows):")
        print(f"  Recency: {cdf['recency'].mean():.2f}")
        print(f"  Frequency: {cdf['frequency'].mean():.2f}")
        print(f"  Monetary: {cdf['monetary'].mean():.2f}")

if __name__ == "__main__":
    check_distribution("../dataset/customers_50k.csv")
