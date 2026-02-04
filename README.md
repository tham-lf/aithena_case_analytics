# Singapore Court Case Analytics

A data pipeline and dashboard for scraping, storing, and analyzing Singapore High Court judgments from LawNet.

## Features
- **Scraper**: Fetches case details (Coram, Counsel, Outcome) and full text from LawNet OpenLaw.
- **Analytics**: "Area of Law" classification and cluster analysis.
- **Dashboard**: Interactive Streamlit app with research metrics and visualizations.
- **Database**: SQLite storage for offline access and persistence.

## Project Structure
- `pipeline.py`: Main entry point for scraping.
- `app.py`: Streamlit dashboard.
- `src/`: Core logic (`scraper`, `database`).
- `data/`: Database storage location.

## Installation

1. **Clone the repository** (if using Git):
   ```bash
   git clone <your-repo-url>
   cd case_analytics
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**:
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - (Optional) Edit `.env` to add your `OPENAI_API_KEY` if you plan to use LLM features in the future.

## Usage

### 1. Scrape Cases
Run the pipeline with a LawNet URL. This will scrape the case and save it to `data/cases.db`.
```bash
python pipeline.py "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+21?ref=sg-sc"
```
*   Use `--force` to re-scrape an existing case.

### 2. Run the Dashboard
Launch the Streamlit app to view analytics:
```bash
streamlit run app.py
```
The app will open in your browser at `http://localhost:8501`.

## Development
- **Database**: The SQLite DB is located at `data/cases.db`.
- **Customization**: Check `src/scraper.py` to adjust extraction logic.
