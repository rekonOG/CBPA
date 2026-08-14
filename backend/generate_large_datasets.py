import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import uuid

def generate_customers(num_rows, output_path):
    print(f"Generating {num_rows} customers...")
    np.random.seed(num_rows)  # Different seed for different sizes
    
    # We want to create distinct clusters and vary their sizes based on the dataset
    if num_rows == 50000:
        # Skewed towards Loyal and At Risk
        c0 = int(num_rows * 0.15)
        c1 = int(num_rows * 0.40)
        c2 = int(num_rows * 0.35)
        c3 = num_rows - c0 - c1 - c2
    else:
        # Skewed towards High Value and Low Value
        c0 = int(num_rows * 0.30)
        c1 = int(num_rows * 0.15)
        c2 = int(num_rows * 0.15)
        c3 = num_rows - c0 - c1 - c2
        
    data = []
    
    # Cluster 0: High Value (Low Recency, High Freq, High Monetary)
    recency = np.random.randint(1, 15, size=c0)
    frequency = np.random.randint(20, 100, size=c0)
    monetary = frequency * np.random.uniform(50, 200, size=c0)
    avg_order_value = monetary / frequency
    total_orders = frequency
    
    df0 = pd.DataFrame({'recency': recency, 'frequency': frequency, 'monetary': monetary, 
                        'avgOrderValue': avg_order_value, 'totalOrders': total_orders})
    
    # Cluster 1: Loyal (Medium Recency, Medium Freq, Medium Monetary)
    recency = np.random.randint(10, 45, size=c1)
    frequency = np.random.randint(10, 50, size=c1)
    monetary = frequency * np.random.uniform(20, 80, size=c1)
    avg_order_value = monetary / frequency
    total_orders = frequency
    
    df1 = pd.DataFrame({'recency': recency, 'frequency': frequency, 'monetary': monetary, 
                        'avgOrderValue': avg_order_value, 'totalOrders': total_orders})
    
    # Cluster 2: At Risk (High Recency, Medium Freq, Medium Monetary)
    recency = np.random.randint(60, 120, size=c2)
    frequency = np.random.randint(5, 30, size=c2)
    monetary = frequency * np.random.uniform(20, 80, size=c2)
    avg_order_value = monetary / frequency
    total_orders = frequency
    
    df2 = pd.DataFrame({'recency': recency, 'frequency': frequency, 'monetary': monetary, 
                        'avgOrderValue': avg_order_value, 'totalOrders': total_orders})
                        
    # Cluster 3: Low Value (High Recency, Low Freq, Low Monetary)
    recency = np.random.randint(60, 365, size=c3)
    frequency = np.random.randint(1, 5, size=c3)
    monetary = frequency * np.random.uniform(5, 20, size=c3)
    avg_order_value = monetary / frequency
    total_orders = frequency
    
    df3 = pd.DataFrame({'recency': recency, 'frequency': frequency, 'monetary': monetary, 
                        'avgOrderValue': avg_order_value, 'totalOrders': total_orders})
                        
    final_df = pd.concat([df0, df1, df2, df3], ignore_index=True)
    
    # Shuffle
    final_df = final_df.sample(frac=1).reset_index(drop=True)
    
    # Add IDs
    final_df['id'] = [str(uuid.uuid4()) for _ in range(num_rows)]
    
    final_df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

def generate_products(num_rows, output_path):
    print(f"Generating {num_rows} product sales records...")
    np.random.seed(num_rows)
    
    num_products = num_rows // 100 # roughly 100 sales per product on average
    products = [f"Product_{i}" for i in range(num_products)]
    
    # Create product catalog
    catalog = {}
    for p in products:
        catalog[p] = np.random.uniform(10.0, 500.0) # price
        
    # Generate sales records
    base_date = datetime(2023, 1, 1)
    
    product_choices = np.random.choice(products, size=num_rows)
    quantities = np.random.randint(1, 10, size=num_rows)
    
    if num_rows == 50000:
        # Skew sales towards the end of the year
        days_offset = np.random.beta(a=5, b=2, size=num_rows) * 364
    else:
        # Skew sales towards the middle of the year
        days_offset = np.random.beta(a=3, b=3, size=num_rows) * 364
        
    dates = [base_date + timedelta(days=int(d), hours=int(np.random.randint(0, 23))) for d in days_offset]
    
    df = pd.DataFrame({
        'product': product_choices,
        'quantity': quantities,
        'date': dates
    })
    
    df['price'] = df['product'].map(catalog)
    df['revenue'] = df['quantity'] * df['price']
    
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    os.makedirs("../dataset", exist_ok=True)
    
    generate_customers(50000, "../dataset/customers_50k.csv")
    generate_customers(100000, "../dataset/customers_100k.csv")
    
    generate_products(50000, "../dataset/products_50k.csv")
    generate_products(100000, "../dataset/products_100k.csv")
    
    print("Done generating datasets.")
