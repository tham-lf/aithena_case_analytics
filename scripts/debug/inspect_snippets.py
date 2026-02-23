import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def extract_snippet(filepath, keyword, window=500):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            idx = content.find(keyword)
            if idx != -1:
                start = max(0, idx - window)
                end = min(len(content), idx + window + len(keyword))
                print(f"--- Snippet around '{keyword}' ---")
                print(content[start:end])
                print("---------------------------------")
            else:
                print(f"Keyword '{keyword}' not found.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    extract_snippet("debug_case_v2.html", "Decision Date")
    extract_snippet("debug_case_v2.html", "Coram")
    extract_snippet("debug_case_v2.html", "Counsel Name(s)")
