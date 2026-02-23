import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


from src.scraper import extract_case_metadata
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(base_dir, "debug_case_v2.html")
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
