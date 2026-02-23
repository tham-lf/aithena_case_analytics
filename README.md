# Singapore Court Case Analytics

A data pipeline and dashboard for scraping, storing, and analyzing Singapore High Court judgments from LawNet.

## Features
- **Scraper**: Fetches case details (Coram, Counsel, Outcome) and full text from LawNet OpenLaw.
- **Analytics**: "Area of Law" classification and cluster analysis.
- **Dashboard**: Interactive Streamlit app with research metrics and visualizations.
- **Database**: PostgreSQL database storage (Supabase).

## Project Structure
- `pipeline.py`: Main entry point for scraping and ingestion.
- `app.py`: Streamlit dashboard.
- `src/`: Core logic (`scraper`, `database`, `extractor`).
- `scripts/db/`: Database seeding and migration scripts.
- `scripts/debug/`: HTML debugging and local extraction testing scripts.
- `notebooks/`: Jupyter notebooks for prototyping (Playwright interactions).
- `data/`: Storage for exported files (e.g. JSONL) and mock databases.

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
Run the pipeline with a LawNet URL. By default, this will scrape the case and save it to your configured PostgreSQL database.
```bash
python pipeline.py "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+21?ref=sg-sc"
```

**Options:**
*   Use `--force` to re-scrape an existing case.
*   Use `--jsonl <PATH>` to also append the scraped case data to a JSONL file.
*   Use `--no-db` to completely skip saving to the PostgreSQL database (useful for local testing).

Example for JSONL export without DB connection:
```bash
python pipeline.py "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc" --jsonl data/case_data.jsonl --no-db
```

### 2. Run the Dashboard
Launch the Streamlit app to view analytics:
```bash
streamlit run app.py
```
The app will open in your browser at `http://localhost:8501`.

## Development
- **Database**: The connection string is managed via the `DATABASE_URL` stored in your `.env` file. You can run `python scripts/db/seed_real_case.py` to test insertion.
- **Customization**: Check `src/scraper.py` and `src/extractor.py` to adjust extraction logic. Let `scripts/debug/fetch_debug_v2.py` download raw HTML for you to test local logic against.
