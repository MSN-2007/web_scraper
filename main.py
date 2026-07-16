import asyncio
import os
import json
import uvicorn
from typing import Dict, Any, List, Optional

from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import REQUIRED_KEYS, EXTRACTION_SCHEMA
from models.venue import get_dynamic_venue_model
from utils.data_utils import (
    save_venues_to_csv,
)
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    get_llm_strategy,
)

load_dotenv()

# Define FastAPI application
app = FastAPI(title="Crawl4AI Web Scraper Control Panel")

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

# Mount static folder for CSS and JS
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """
    Serves the main control panel HTML page.
    """
    return FileResponse("static/index.html")

@app.get("/api/schema")
async def get_schema():
    """
    Serves the default EXTRACTION_SCHEMA definition to the client.
    """
    return EXTRACTION_SCHEMA

class ParseSchemaRequest(BaseModel):
    api_key: Optional[str] = None
    prompt: str
    schema_config: Dict[str, Any]

@app.post("/api/parse-schema")
async def parse_schema_prompt(request: ParseSchemaRequest):
    """
    Parses user simple language instructions to activate/deactivate schema keys using Gemini.
    """
    api_token = request.api_key or os.getenv("GEMINI_API_KEY")
    if not api_token:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key is required to parse the schema prompt. Please provide it in the input or environment."
        )

    import urllib.request
    import urllib.error
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_token}"
    
    fields_info = {
        key: val.get("description", "")
        for key, val in request.schema_config.items()
    }
    
    prompt = (
        f"You are an AI assistant configured to map a user's natural language request to a scraping schema configuration.\n\n"
        f"User prompt: \"{request.prompt}\"\n\n"
        f"Here is the list of available fields and their descriptions:\n"
        f"{json.dumps(fields_info, indent=2)}\n\n"
        f"For each field, determine if the user's request suggests they want to extract this field.\n"
        f"Always keep 'name' as true.\n"
        f"Respond ONLY with a JSON object where keys are the field names and values are booleans (true if active, false otherwise).\n"
        f"Do not include any explanation or markdown formatting."
    )
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        # Timeout after 15 seconds to prevent hanging
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text_response = res_data["candidates"][0]["content"]["parts"][0]["text"]
            active_mapping = json.loads(text_response.strip())
            
            # Update the schema config active fields
            updated_schema = {}
            for key, val in request.schema_config.items():
                updated_field = val.copy()
                if key == "name":
                    updated_field["active"] = True
                else:
                    updated_field["active"] = bool(active_mapping.get(key, False))
                updated_schema[key] = updated_field
            
            return updated_schema
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API parsing failed: {str(e)}"
        )

class ScrapeConfig(BaseModel):
    api_key: Optional[str] = None
    url: str
    css_selector: str = "div.resultbox"
    folder_name: str = "scraped_data"
    file_name: str = "venues.csv"
    schema_config: Optional[Dict[str, Any]] = None


async def crawl_venues_generator(
    url: str,
    css_selector: str,
    api_key: str,
    folder_name: str,
    file_name: str,
    schema_config: Optional[Dict[str, Any]] = None
):
    """
    Asynchronous generator that crawls pages and yields status updates in JSON.
    """
    yield json.dumps({"level": "INFO", "message": "Initializing browser configuration..."})
    browser_config = get_browser_config()
    
    if not schema_config:
        schema_config = EXTRACTION_SCHEMA
    
    # Generate the dynamic Pydantic model for this crawl
    schema_model = get_dynamic_venue_model(schema_config)
    
    yield json.dumps({"level": "INFO", "message": "Configuring Gemini LLM extraction strategy..."})
    llm_strategy = get_llm_strategy(api_key=api_key, schema_config=schema_config, schema_model=schema_model)
    session_id = "venue_crawl_session"

    # Initialize state variables
    page_number = 1
    all_venues = []
    seen_names = set()

    # Create target folder
    os.makedirs(folder_name, exist_ok=True)
    csv_filepath = os.path.join(folder_name, file_name)

    yield json.dumps({"level": "INFO", "message": f"Starting AsyncWebCrawler session..."})
    
    # Start the web crawler context
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            yield json.dumps({"level": "INFO", "message": f"Loading page {page_number} from target URL..."})
            
            # Fetch and process data from the current page
            venues, no_results_found = await fetch_and_process_page(
                crawler,
                page_number,
                url,
                css_selector,
                llm_strategy,
                session_id,
                REQUIRED_KEYS,
                seen_names,
            )

            if no_results_found:
                yield json.dumps({"level": "SUCCESS", "message": "No more venues found. Ending crawl."})
                break  # Stop crawling when "No Results Found" message appears

            if not venues:
                yield json.dumps({"level": "WARNING", "message": f"No venues extracted from page {page_number}. Ending crawl."})
                break  # Stop if no venues are extracted

            # Add the venues from this page to the total list
            all_venues.extend(venues)
            yield json.dumps({
                "level": "SUCCESS", 
                "message": f"Successfully extracted {len(venues)} venues from page {page_number}. (Total compiled: {len(all_venues)})"
            })
            
            page_number += 1  # Move to the next page

            # Pause between requests to be polite and avoid rate limits
            await asyncio.sleep(2)

    # Save the collected venues to a CSV file
    if all_venues:
        # Determine the header columns dynamically based on active fields in custom schema
        active_fields = [k for k, v in schema_config.items() if v.get("active", False)]
        save_venues_to_csv(all_venues, csv_filepath, fieldnames=active_fields)
        yield json.dumps({
            "level": "SUCCESS", 
            "message": f"Scraping completed. Saved {len(all_venues)} venues to '{csv_filepath}'."
        })
    else:
        yield json.dumps({"level": "WARNING", "message": "No venues were extracted during the crawl."})

    # Try to close/show usage stats
    try:
        llm_strategy.show_usage()
    except Exception:
        pass


@app.post("/api/scrape")
async def start_scrape(config: ScrapeConfig):
    """
    Triggers the scraping process and streams live terminal log updates to the client.
    """
    # Enforce API key existence
    api_token = config.api_key or os.getenv("GEMINI_API_KEY")
    if not api_token:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key is required. Please add it to the UI or set it in the environment variables."
        )

    async def event_generator():
        async for log_line in crawl_venues_generator(
            url=config.url,
            css_selector=config.css_selector,
            api_key=api_token,
            folder_name=config.folder_name,
            file_name=config.file_name,
            schema_config=config.schema_config
        ):
            yield f"data: {log_line}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/files")
async def list_files():
    """
    Scans the workspace directory recursively and returns all compiled CSV files.
    """
    csv_files = []
    ignored_dirs = {"venv", "__pycache__", "utils", "models", ".git", ".gemini", ".agents", "static"}
    
    for root, dirs, files in os.walk("."):
        # Modify dirs in-place to avoid entering ignored folders
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".csv"):
                relative_root = os.path.relpath(root, ".")
                folder = "root" if relative_root == "." else relative_root
                csv_files.append({
                    "filename": file,
                    "folder": folder
                })
                
    return {"files": csv_files}


@app.get("/api/download")
async def download_file(folder: str, file: str):
    """
    Serves a CSV file from a specified subfolder for downloading.
    """
    base_dir = "."
    if folder == "root":
        file_path = os.path.join(base_dir, file)
    else:
        # Sanitize folder path to prevent path traversal
        clean_folder = os.path.normpath(folder).replace("..", "")
        file_path = os.path.join(base_dir, clean_folder, file)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="The requested data file does not exist.")

    return FileResponse(path=file_path, filename=file, media_type="text/csv")


if __name__ == "__main__":
    print("\n--------------------------------------------------------------")
    print("🚀 Starting Crawl4AI Web Dashboard on http://127.0.0.1:8000")
    print("--------------------------------------------------------------\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
