# Tickermood

**Tickermood** is a Python package that provides market sentiment analysis for stock tickers based on news from multiple sources. It combines web scraping techniques with large language models (LLMs) using the [LangChain](https://www.langchain.com/) and [LangGraph](https://www.langgraph.dev/) frameworks to generate sentiment scores for given tickers.

---

## 📦 Installation

Install Tickermood via pip:

```bash
pip install tickermood
```

> **Note**: To use Tickermood locally, [Ollama](https://ollama.com/) must be installed. Alternatively, you can use the OpenAI API by providing your API key.

---

## 🚀 Usage

### Programmatic Usage

```python
from tickermood import TickerMood

ticker_mood = TickerMood.from_symbols(["AAPL", "GOOGL", "MSFT"])
ticker_mood.run()
```

### CLI Usage

```bash
tickermood run AAPL GOOGL MSFT
```

This will:
- Fetch the latest news for the specified tickers
- Run LLM agents to analyze the news
- Provide a sentiment score for each ticker

Results are stored in a SQLite database.

![Tickermood Output](docs/img/img.png)

---

## 🗃️ Database

Tickermood creates a SQLite database in the current directory named `tickermood.db` if it doesn't already exist. It includes:
- Sentiment ratings (e.g., Buy, Hold, Sell)
- Price targets
- Summaries of the fetched news articles

---

## ⚙️ LLM Backend Options

### Default: Local LLM (Ollama)
- Runs LLMs locally for free
- Performance depends on your hardware

### Optional: OpenAI API
- Requires setting the `OPENAI_API_KEY` environment variable

Or, pass the key via CLI:

```bash
tickermood run AAPL GOOGL MSFT --openai_api_key_path /path/to/openai_api_key.txt
```

---

## 📝 License

MIT License