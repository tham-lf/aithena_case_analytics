
def extract_lines(filepath, keywords, context=5):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            for k in keywords:
                if k in line:
                    print(f"--- Found '{k}' at line {i+1} ---")
                    # Print context lines
                    start = max(0, i - 1)
                    end = min(len(lines), i + context + 1)
                    for j in range(start, end):
                        print(f"{j+1}: {lines[j].strip()[:200]}") # Truncate long lines
                    print("---------------------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_lines("debug_case_v2.html", ["Decision Date", "Coram", "Case Name", "Counsel Name(s)"])
