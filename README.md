# Briefly AI

An AI-powered prototype that turns a crowded financial inbox into an on-demand audio briefing. Select reports from your inbox, apply smart filters, and generate a concise morning brief you can listen to on the go.

## Features

- **Single inbox view** – Gmail-style layout with financial emails highlighted (light blue) and non-financial noise separated
- **Smart filters** – Auto-select by topic: Market Volatility, Tech & AI, Central Banks, Energy, Last 24 Hours, and more
- **AI synthesis** – LLM clusters related topics and produces a cohesive briefing script
- **Text-to-speech** – Audio output with configurable duration (1, 3, or 5 minutes)
- **Archive** – Past briefings stored in session for replay

## Requirements

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- [Groq](https://groq.com/) API key
- [gTTS](https://gtts.readthedocs.io/)

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

2. **Install dependencies**

   ```bash
   pip install streamlit pandas groq gtts
   ```

3. **Create the data file** (if not already present)

   ```bash
   python setup_data.py
   ```

4. **Configure the Groq API key**

   Create a `.streamlit/secrets.toml` file:

   ```toml
   GROQ_API_KEY = "your-groq-api-key-here"
   ```

## Run

```bash
python -m streamlit run main_app.py
```

Open the app in your browser at `http://localhost:8501`.

## Project structure

| File / folder  | Description                                     |
| -------------- | ----------------------------------------------- |
| `main_app.py`  | Streamlit UI, inbox view, filters, archive      |
| `logic.py`     | AI pipeline (Groq + gTTS), separate from UI     |
| `setup_data.py`| Generates `data.csv` with sample emails         |
| `data.csv`     | Email data (financial + noise)                  |
| `.streamlit/`  | Config and secrets (do not commit `secrets.toml`)|

## License

MIT
