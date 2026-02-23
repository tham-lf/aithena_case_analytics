import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


from bs4 import BeautifulSoup

def inspect_structure(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
        # Find where "Decision Date" is
        target = soup.find(string=lambda t: t and "Decision Date" in t)
        if target:
            print("--- Parent of 'Decision Date' ---")
            parent = target.parent
            print(parent.prettify())
            print("--- Next Sibling of Parent ---")
            print(parent.find_next_sibling().prettify() if parent.find_next_sibling() else "None")
            print("--------------------------------")
            
        # Find Coram
        target = soup.find(string=lambda t: t and "Coram" in t)
        if target:
            print("--- Parent of 'Coram' ---")
            parent = target.parent
            print(parent.prettify())
            print("--- Next Sibling of Parent ---")
            print(parent.find_next_sibling().prettify() if parent.find_next_sibling() else "None")
            print("--------------------------------")

        # Find Counsel
        target = soup.find(string=lambda t: t and "Counsel Name" in t)
        if target:
            print("--- Parent of 'Counsel Name' ---")
            parent = target.parent
            print(parent.prettify())
            print("--- Next Sibling of Parent ---")
            print(parent.find_next_sibling().prettify() if parent.find_next_sibling() else "None")
            print("--------------------------------")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_structure("debug_case_v2.html")
