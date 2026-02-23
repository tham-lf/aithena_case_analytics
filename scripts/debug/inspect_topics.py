import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


from bs4 import BeautifulSoup
import re

def inspect(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        
    print("--- Searching for Case Name Candidates ---")
    # Check for contentsOfFile
    div = soup.find("div", class_="contentsOfFile")
    if div:
        print("Found div.contentsOfFile!")
        print(f"Attributes: {div.attrs}")
    else:
        print("div.contentsOfFile NOT FOUND.")
        
    # Check for title class
    titles = soup.find_all(class_=re.compile("title", re.IGNORECASE))
    print(f"Found {len(titles)} elements with 'title' in class.")
    for t in titles[:3]:
        print(f"Class: {t.get('class')}, Text: {t.get_text()[:50]}")

    print("\n--- Searching for Area of Law ---")
    # Search for keywords
    keywords = ["Legal Topics", "Catchwords", "Categories", "Subject"]
    for k in keywords:
        elem = soup.find(string=re.compile(k, re.IGNORECASE))
        if elem:
            print(f"Found keyword '{k}':")
            parent = elem.parent
            print(f"Parent: {parent.name} Class: {parent.get('class')}")
            print(f"Parent Text: {parent.get_text()[:100]}")
            # Next sibling?
            nxt = parent.find_next()
            print(f"Next Element Text: {nxt.get_text()[:100] if nxt else 'None'}")
            print("-" * 20)
        else:
            print(f"Keyword '{k}' NOT FOUND.")

if __name__ == "__main__":
    inspect("debug_case_v2.html")
