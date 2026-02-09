
from src.scraper import extract_case_metadata
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    filename = "debug_case_v2.html"
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html = f.read()
            
        print(f"Loaded {len(html)} bytes from {filename}")
        
        # Test extraction
        data = extract_case_metadata(html)
        
        print("\n--- Extracted Metadata ---")
        for k, v in data.items():
            print(f"{k}: {v}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
