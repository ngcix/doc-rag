"""
Script to download/export the embedding model for offline use.

This script loads the model (from cache or internet) and saves it to a
portable "flat" directory structure in 'models/Alibaba-NLP_gte-multilingual-base'.

Usage:
    python download_model.py
"""
import os
import shutil
from pathlib import Path
from sentence_transformers import SentenceTransformer
from config.settings import settings

def export_model():
    model_name = settings.model.model_name
    models_dir = settings.model.model_cache_dir
    
    # Define local export path (replace slashes with underscores)
    safe_name = model_name.replace("/", "_")
    export_path = models_dir / safe_name
    
    print(f"Exporting model '{model_name}'...")
    print(f"Target directory: {export_path}")
    
    # Load model (uses HF cache automatically)
    try:
        model = SentenceTransformer(
            model_name, 
            cache_folder=str(models_dir),
            trust_remote_code=True
        )
        
        # Save to local directory
        model.save(str(export_path))
        
        print("\nSUCCESS!")
        print(f"Model saved to: {export_path}")
        print("\nTo use offline on another machine:")
        print(f"1. Copy the folder '{export_path}' to the 'models/' directory on the target machine.")
        print("2. The system will automatically detect and use the local model.")
        
    except Exception as e:
        print(f"\nERROR: Failed to export model: {e}")

if __name__ == "__main__":
    export_model()
