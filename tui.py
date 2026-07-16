import asyncio
import os
import json
import urllib.request
import urllib.error
import csv
from dotenv import load_dotenv

# Import our scraper utils and configs
from config import EXTRACTION_SCHEMA, REQUIRED_KEYS
from models.venue import get_dynamic_venue_model
from utils.data_utils import save_venues_to_csv
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    get_llm_strategy
)
from crawl4ai import AsyncWebCrawler

load_dotenv()

# ANSI Color codes for styled terminal output
CLR_HEADER = "\033[95m"
CLR_BLUE = "\033[94m"
CLR_CYAN = "\033[96m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_RED = "\033[91m"
CLR_BOLD = "\033[1m"
CLR_RESET = "\033[0m"

# State variables
current_url = "https://www.justdial.com/Zahirabad/Hospitals-in-Zaheerabad-Main-Road/nct-10253670"
css_selector = "div.resultbox"
folder_name = "scraped_data"
file_name = "venues.csv"
schema_config = json.loads(json.dumps(EXTRACTION_SCHEMA))  # Deep copy default schema
api_key = os.getenv("GEMINI_API_KEY", "")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    print(f"\n{CLR_HEADER}{CLR_BOLD}=== {title} ==={CLR_RESET}")

async def analyze_prompt_with_gemini(prompt_text):
    """
    Connects directly to Gemini API to parse natural language requirements
    and map them to active/deactivated schema fields.
    """
    global api_key
    token = api_key or os.getenv("GEMINI_API_KEY")
    if not token:
        print(f"{CLR_RED}Error: Gemini API Key is required. Set it in `.env` or input it in Settings.{CLR_RESET}")
        return
        
    print(f"\n{CLR_YELLOW}Querying Gemini NLP engine to analyze: '{prompt_text}'...{CLR_RESET}")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={token}"
    
    fields_info = {
        key: val.get("description", "")
        for key, val in schema_config.items()
    }
    
    prompt = (
        f"You are an AI assistant configured to map a user's natural language request to a scraping schema configuration.\n\n"
        f"User prompt: \"{prompt_text}\"\n\n"
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
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text_response = res_data["candidates"][0]["content"]["parts"][0]["text"]
            active_mapping = json.loads(text_response.strip())
            
            # Update schema config
            for key in schema_config.keys():
                if key == "name":
                    schema_config[key]["active"] = True
                else:
                    schema_config[key]["active"] = bool(active_mapping.get(key, False))
            
            print(f"{CLR_GREEN}Success! Schema updated successfully.{CLR_RESET}")
    except Exception as e:
        print(f"{CLR_RED}Failed to analyze prompt with Gemini: {e}{CLR_RESET}")

def display_schema_checklist():
    """
    Shows a structured list of schema fields and permits manual toggles.
    """
    while True:
        clear_screen()
        print_header("Universal Schema Field Library")
        print("Toggle active/inactive status of fields to scrape.\n")
        
        fields_list = list(schema_config.keys())
        for idx, key in enumerate(fields_list, start=1):
            info = schema_config[key]
            status_box = f"[{CLR_GREEN}X{CLR_RESET}]" if info["active"] else "[ ]"
            color = CLR_GREEN if info["active"] else CLR_RESET
            print(f"{idx:2d}. {status_box} {color}{key:<15}{CLR_RESET} ({info['type']}) - {info['description']}")
            
        print(f"\n{CLR_BOLD}0. Back to Main Menu{CLR_RESET}")
        
        choice = input("\nEnter field number to toggle (or 0 to return): ").strip()
        if choice == '0' or not choice:
            break
            
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(fields_list):
                toggle_key = fields_list[choice_idx]
                if toggle_key == "name":
                    print(f"{CLR_YELLOW}Notice: 'name' is the primary field and cannot be deactivated.{CLR_RESET}")
                    await_enter()
                else:
                    schema_config[toggle_key]["active"] = not schema_config[toggle_key]["active"]
            else:
                print(f"{CLR_RED}Invalid option index.{CLR_RESET}")
                await_enter()
        except ValueError:
            print(f"{CLR_RED}Please enter a numeric digits choice.{CLR_RESET}")
            await_enter()

async def run_crawler_session():
    """
    Launches the asynchronous Crawl4AI browser session, outputs real-time logs,
    and saves compile CSV outputs.
    """
    global api_key
    token = api_key or os.getenv("GEMINI_API_KEY")
    if not token:
        print(f"{CLR_RED}Error: Gemini API Key is required. Set it in `.env` or option 5.{CLR_RESET}")
        await_enter()
        return

    clear_screen()
    print_header("Crawler Execution Console")
    print(f"{CLR_BLUE}Target URL:{CLR_RESET} {current_url}")
    print(f"{CLR_BLUE}CSS Selector:{CLR_RESET} {css_selector}")
    print(f"{CLR_BLUE}Output Path:{CLR_RESET} {folder_name}/{file_name}")
    
    active_fields = [k for k, v in schema_config.items() if v.get("active", False)]
    print(f"{CLR_BLUE}Scraping fields:{CLR_RESET} {', '.join(active_fields)}")
    print("-" * 50)
    
    print(f"{CLR_YELLOW}Initializing browser configuration...{CLR_RESET}")
    browser_config = get_browser_config()
    
    print(f"{CLR_YELLOW}Generating dynamic Pydantic model...{CLR_RESET}")
    schema_model = get_dynamic_venue_model(schema_config)
    
    print(f"{CLR_YELLOW}Configuring Gemini extraction strategy...{CLR_RESET}")
    llm_strategy = get_llm_strategy(api_key=token, schema_config=schema_config, schema_model=schema_model)
    session_id = "tui_crawl_session"
    
    page_number = 1
    all_venues = []
    seen_names = set()
    
    os.makedirs(folder_name, exist_ok=True)
    csv_filepath = os.path.join(folder_name, file_name)
    
    print(f"{CLR_GREEN}Launching AsyncWebCrawler...{CLR_RESET}\n")
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            while True:
                print(f"{CLR_CYAN}[PAGE {page_number}]{CLR_RESET} Loading and processing...")
                
                # Fetch and process data
                venues, no_results_found = await fetch_and_process_page(
                    crawler,
                    page_number,
                    current_url,
                    css_selector,
                    llm_strategy,
                    session_id,
                    REQUIRED_KEYS,
                    seen_names
                )
                
                if no_results_found:
                    print(f"{CLR_GREEN}Received 'No Results Found' message. Ending crawl loop.{CLR_RESET}")
                    break
                    
                if not venues:
                    print(f"{CLR_YELLOW}No more records extracted. Ending crawl loop.{CLR_RESET}")
                    break
                    
                all_venues.extend(venues)
                print(f"{CLR_GREEN}[SUCCESS]{CLR_RESET} Extracted {len(venues)} venues from Page {page_number}. (Total: {len(all_venues)})")
                
                page_number += 1
                await asyncio.sleep(2)  # Polite delay
                
        if all_venues:
            save_venues_to_csv(all_venues, csv_filepath, fieldnames=active_fields)
            print(f"\n{CLR_GREEN}{CLR_BOLD}★ Crawling completed successfully!{CLR_RESET}")
            print(f"Saved {len(all_venues)} structured items in '{csv_filepath}'.")
        else:
            print(f"\n{CLR_YELLOW}No items were extracted. CSV file not generated.{CLR_RESET}")
            
    except Exception as e:
        print(f"\n{CLR_RED}Fatal Error during crawl: {e}{CLR_RESET}")
        
    await_enter()

def await_enter():
    input(f"\nPress {CLR_BOLD}[Enter]{CLR_RESET} to continue...")

def update_settings():
    global current_url, css_selector, folder_name, file_name, api_key
    while True:
        clear_screen()
        print_header("Scraper Configuration Settings")
        print(f"1. Target URL:   {CLR_CYAN}{current_url}{CLR_RESET}")
        print(f"2. CSS Selector: {CLR_CYAN}{css_selector}{CLR_RESET}")
        print(f"3. Output Folder:{CLR_CYAN}{folder_name}{CLR_RESET}")
        print(f"4. Output File:  {CLR_CYAN}{file_name}{CLR_RESET}")
        print(f"5. Gemini Key:   {CLR_CYAN}{'********' if api_key else 'Not Loaded (Falls back to env)'}{CLR_RESET}")
        print(f"\n{CLR_BOLD}0. Back to Main Menu{CLR_RESET}")
        
        choice = input("\nSelect setting to modify (0-5): ").strip()
        if choice == '0' or not choice:
            break
        elif choice == '1':
            current_url = input("Enter new Target URL: ").strip() or current_url
        elif choice == '2':
            css_selector = input("Enter new CSS Selector: ").strip() or css_selector
        elif choice == '3':
            folder_name = input("Enter Output Folder: ").strip() or folder_name
        elif choice == '4':
            file_name = input("Enter Output Filename: ").strip() or file_name
        elif choice == '5':
            api_key = input("Enter Gemini API Key: ").strip() or api_key

async def main():
    global schema_config
    while True:
        clear_screen()
        print(f"{CLR_BLUE}{CLR_BOLD}")
        print("┌──────────────────────────────────────────────┐")
        print("│   ⚡ Crawl4AI Developer TUI Control Panel ⚡  │")
        print("└──────────────────────────────────────────────┘")
        print(CLR_RESET)
        
        print(f"{CLR_BOLD}Active Configurations:{CLR_RESET}")
        print(f"- Target URL:   {CLR_CYAN}{current_url}{CLR_RESET}")
        print(f"- CSS Selector: {CLR_CYAN}{css_selector}{CLR_RESET}")
        print(f"- Save Path:    {CLR_CYAN}{folder_name}/{file_name}{CLR_RESET}")
        
        active_fields = [k for k, v in schema_config.items() if v.get("active", False)]
        print(f"- Active Keys:  {CLR_GREEN}{', '.join(active_fields)}{CLR_RESET}")
        
        print("\n" + "=" * 50)
        print(f"{CLR_BOLD}Main Menu Options:{CLR_RESET}")
        print(f"1. {CLR_BOLD}Set Target URL & File Paths{CLR_RESET}")
        print(f"2. {CLR_BOLD}Enter NLP Extraction Request (Simple Language){CLR_RESET}")
        print(f"3. {CLR_BOLD}Configure Schema Fields Checklist{CLR_RESET}")
        print(f"4. {CLR_GREEN}{CLR_BOLD}Initiate Scraper Session 🚀{CLR_RESET}")
        print(f"5. {CLR_RED}Exit{CLR_RESET}")
        print("=" * 50)
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            update_settings()
        elif choice == '2':
            print_header("Describe What to Scrape (Simple Language)")
            prompt = input("Describe required data (e.g., 'I want name, address, website'): ").strip()
            if prompt:
                await analyze_prompt_with_gemini(prompt)
                await_enter()
        elif choice == '3':
            display_schema_checklist()
        elif choice == '4':
            await run_crawler_session()
        elif choice == '5':
            print(f"\n{CLR_YELLOW}Exited developer panel. Happy coding!{CLR_RESET}")
            break
        else:
            print(f"{CLR_RED}Invalid option selected.{CLR_RESET}")
            await_enter()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_YELLOW}Control Panel Terminated.{CLR_RESET}")
