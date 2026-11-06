# Competitor Analysis Agent

A Streamlit-based AI application for competitor research and marketing analysis.

## Features
- AI-generated competitor analysis reports
- Live web search
- Competitor discovery and classification
- Competitor strength scoring dashboard
- Evidence collection and research links
- SEO and keyword opportunity suggestions
- Digital marketing findings and a 30-day action plan
- Downloadable Markdown reports

## Technology Stack
- Python
- Streamlit
- Groq API
- DuckDuckGo Search (DDGS)
- Pandas
- python-dotenv

## Run the App
Open PowerShell in the project directory and run:

```powershell
python -m streamlit run .\advanced_app.py
```

## Project Modules
- dvanced_app.py - Main Streamlit application
- competitor_discovery.py - Competitor discovery
- competitor_scoring.py - Competitor scoring dashboard
- competitor_evidence.py - Evidence collection and research links

## Important Limitations
- Search results should be verified using their original sources.
- Keyword suggestions are not necessarily measured search-volume data.
- Do not invent competitor scores; use evidence-backed ratings.
- Evidence may not persist after the app restarts.

## Security
- Keep your .env file private.
- Never publish your actual API key.

## Project Status
The application has been run locally and the Python modules have passed a syntax compilation check.
