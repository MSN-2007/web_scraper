# ⚡ Crawl4AI Intelligent Web Scraper Control Panel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0%2B-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Flash-orange?logo=google-gemini)](https://ai.google.dev/)

An open-source, asynchronous web scraping control panel built with Python. This application leverages **Crawl4AI** and the **Google Gemini API** to scrape dynamic, JavaScript-heavy listing directories and extract structured data automatically. 

It features an **AI-driven schema mapper**: describe what details you want to extract in simple everyday language, and the system automatically matches your intent to fields in the **Universal Scraper Library**, deactivating unnecessary fields to save API tokens and compile cleaner CSV files.

---

## ✨ Features

- **Asynchronous Crawling Engine**: Built on top of [Crawl4AI](https://docs.crawl4ai.com/) and Playwright to support concurrent page fetches with built-in evasion techniques.
- **Dynamic Pydantic Data Models**: Generates backend data schemas on-the-fly depending on which scraper fields are currently active.
- **Natural Language Schema Parsing**: Describe what you need in simple language (e.g. *"Give me hospital names, contact numbers, and website links"*), and Gemini will toggle the matching database fields automatically.
- **Universal Scraper Library**: Pre-built configurations for common directory listing elements:
  - Name, Physical Address, Phone Number, Operating Timings.
  - Ratings, Reviews Count, Website, Email Address, Pricing, Services, Description.
- **Premium Glassmorphic Dashboard**: A gorgeous, interactive dark-mode web console.
- **Live Terminal Logging**: Streams execution logs from the crawler instance in real time using Server-Sent Events (SSE).
- **On-Demand Dataset Export**: Generates and manages clean CSV outputs consisting strictly of your activated fields.

---

## 📂 Project Directory Structure

```
WEB_SCAPER/
├── config.py            # Central schema & default targets
├── main.py              # FastAPI server & crawler orchestrator
├── list_models.py       # Gemini API validation script
├── test_scraper.py      # Diagnostic crawl test script
├── models/
│   └── venue.py         # Dynamic and fallback Pydantic models
├── static/
│   ├── index.html       # Dashboard HTML structure
│   ├── app.js           # Front-end API interaction & rendering
│   └── style.css        # Premium dark-theme glassmorphism styles
├── utils/
│   ├── data_utils.py    # Deduplication & CSV compilation
│   └── scraper_utils.py # Crawl4AI configurations & extraction strategies
├── requirements.txt     # Dependency list
└── README.MD            # Project documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or higher.
- A Google Gemini API key (retrieve from [Google AI Studio](https://aistudio.google.com/)).

### 2. Installation & Setup

Clone the repository:
```bash
git clone https://github.com/MSN-2007/web_scraper.git
cd web_scraper
```

Follow the instructions matching your operating system to set up a virtual environment, install dependencies, and setup Crawl4AI's headless browser binaries:

#### 🖥️ Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install package dependencies
pip install -r requirements.txt

# Download required headless browsers
playwright install
```

#### 🍎 macOS (Terminal)
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install package dependencies
pip install -r requirements.txt

# Download required headless browsers
playwright install
```

#### 🐧 Linux (Ubuntu/Debian/Fedora)
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install package dependencies
pip install -r requirements.txt

# Download required headless browsers
playwright install

# Download Linux system dependency packages for headless rendering
playwright install-deps
```

### 3. Setup Environment Variables
Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 4. Running the Dashboard
Launch the FastAPI development server:

```bash
python main.py
```
Open your browser and navigate to `http://127.0.0.1:8000`.

---

## 🛠️ Usage Guide

1. **Configure Scraper Settings**:
   - **Target Web URL**: Enter the listing URL to crawl (e.g. Justdial, Yelp, maps, directories).
   - **CSS Selector**: Target the listing wrapper element (e.g., `div.resultbox` or `div.card`) to isolate the main contents.
   - **Output Paths**: Set target folders and CSV filenames.

2. **Select Extraction Fields**:
   - **AI Prompt Selector**: Type a request in the prompt text area (e.g., *"I need name, website, and customer ratings"*) and click **Apply Description ✨**. The dashboard will query Gemini to parse your phrase, activate matching fields, and deactivate others.
   - **Manual Adjustments**: Directly tick/untick items in the **Universal Field Library** checklist to tweak settings.

3. **Initiate Scrape**:
   - Input your Gemini API key (or leave blank to use the server-side `.env` key).
   - Click **Initiate Crawler Session**.
   - Watch logs stream live in the **Execution Console**.
   - Download compiled outputs directly from the **Output Databases** panel once the session finishes.

---

## ⚙️ Customizing the Schema Library

To add custom fields to the universal library, update `EXTRACTION_SCHEMA` inside [config.py](file:///c:/Users/sumiy/OneDrive/Desktop/projects/atomations/WEB_SCAPER/config.py):

```python
EXTRACTION_SCHEMA = {
    "field_name": {
        "active": True,                # Default status
        "type": "str",                 # Supported types: str, float, int, bool
        "description": "Simple language description for LLM mapping."
    }
}
```
The application dynamically updates the database export headers, Pydantic validation structures, UI checklist elements, and LLM prompt instructions based on this dictionary.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
