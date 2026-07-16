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
current_url = "https://datoms.io/cold-storage-monitoring/"
css_selector = "body"
folder_name = "scraped_data"
file_name = "scraped_output.csv"
schema_config = json.loads(json.dumps(EXTRACTION_SCHEMA))  # Deep copy default schema
api_key = os.getenv("GEMINI_API_KEY", "")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    print(f"\n{CLR_HEADER}{CLR_BOLD}=== {title} ==={CLR_RESET}")

def await_enter():
    input(f"\nPress {CLR_BOLD}[Enter]{CLR_RESET} to continue...")

async def run_setup_wizard():
    """
    Step-by-step developer TUI setup wizard matching the OpenClaw / Hermes flow.
    """
    global api_key, current_url, css_selector, folder_name, file_name, schema_config
    
    clear_screen()
    print(f"{CLR_BLUE}{CLR_BOLD}")
    print("┌──────────────────────────────────────────────┐")
    print("│   ⚡ Crawl4AI Step-by-Step Scraper Wizard ⚡  │")
    print("└──────────────────────────────────────────────┘")
    print(CLR_RESET)

    # Step 1: API / Credentials
    print_header("Step 1: Credentials & API Keys")
    env_key = os.getenv("GEMINI_API_KEY", "")
    key_hint = f" [Default: ...{env_key[-8:]}]" if env_key else ""
    user_key = input(f"Enter Gemini API Key{key_hint}: ").strip()
    if user_key:
        api_key = user_key
    elif env_key:
        api_key = env_key

    # Step 2: Target URL
    print_header("Step 2: Target Web URL")
    url_input = input(f"Enter URL to scrape [Default: {current_url}]: ").strip()
    if url_input:
        current_url = url_input

    # Step 3: CSS Selector
    print_header("Step 3: Target CSS Selector")
    selector_input = input(f"Enter CSS Selector [Default: {css_selector}]: ").strip()
    if selector_input:
        css_selector = selector_input

    # Step 4: Information / Fields to Scrape (Space then Enter)
    print_header("Step 4: Fields to Scrape")
    print("Enter the fields/information you want to extract, separated by spaces (then press Enter).")
    print(f"E.g., '{CLR_GREEN}name address phone_number capacity{CLR_RESET}'")
    print(f"Current default library: {', '.join(schema_config.keys())}\n")
    
    fields_line = input("Fields to extract: ").strip()
    if fields_line:
        fields_list = fields_line.split()
        
        # Deactivate all existing fields first (except name which is required)
        for key in schema_config.keys():
            schema_config[key]["active"] = (key == "name")
            
        # Activate matching fields or dynamically create new custom fields
        for field in fields_list:
            field_lower = field.lower()
            if field_lower in schema_config:
                schema_config[field_lower]["active"] = True
            else:
                # Add custom field dynamically ("if other we need we can add in other")
                schema_config[field_lower] = {
                    "active": True,
                    "type": "str",
                    "description": f"The extracted {field_lower} details from the webpage content."
                }
                print(f"  -> Added new custom field: '{CLR_YELLOW}{field_lower}{CLR_RESET}'")

    # Step 5: Location to Store Data
    print_header("Step 5: Output Storage Location")
    f_folder = input(f"Enter output folder [Default: {folder_name}]: ").strip()
    if f_folder:
        folder_name = f_folder
        
    f_file = input(f"Enter CSV file name [Default: {file_name}]: ").strip()
    if f_file:
        file_name = f_file

    # Review settings
    await display_summary_and_confirm()

async def display_summary_and_confirm():
    clear_screen()
    print_header("Scraper Configuration Summary")
    print(f"{CLR_BLUE}Gemini API Key: {CLR_RESET}{'Set (credentials loaded)' if api_key else CLR_RED + 'Missing!' + CLR_RESET}")
    print(f"{CLR_BLUE}Target URL:     {CLR_RESET}{current_url}")
    print(f"{CLR_BLUE}CSS Selector:   {CLR_RESET}{css_selector}")
    print(f"{CLR_BLUE}Storage Path:   {CLR_RESET}{folder_name}/{file_name}")
    
    active_fields = [k for k, v in schema_config.items() if v.get("active", False)]
    print(f"{CLR_BLUE}Active Fields:  {CLR_RESET}{CLR_GREEN}{', '.join(active_fields)}{CLR_RESET}")
    print("-" * 50)
    
    confirm = input(f"\n{CLR_BOLD}Start scraping session now? (y/n): {CLR_RESET}").strip().lower()
    if confirm == 'y' or confirm == 'yes':
        await run_crawler_session()
    else:
        print(f"\n{CLR_YELLOW}Scrape aborted. Returning to settings menu.{CLR_RESET}")
        await_enter()

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
        print(f"{CLR_RED}Error: Gemini API Key is required to run the session.{CLR_RESET}")
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
                print(f"{CLR_GREEN}[SUCCESS]{CLR_RESET} Extracted {len(venues)} items from Page {page_number}. (Total: {len(all_venues)})")
                
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
    # Run the setup wizard on startup
    await run_setup_wizard()
    
    # After the setup wizard, let user repeat or change configurations
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
        print(f"{CLR_BOLD}Options Menu:{CLR_RESET}")
        print(f"1. {CLR_BOLD}Run Setup Wizard Again ⚡{CLR_RESET}")
        print(f"2. {CLR_BOLD}Modify Specific Settings (API Key, URL, folder, etc.){CLR_RESET}")
        print(f"3. {CLR_BOLD}View / Toggle Schema Library Checklist{CLR_RESET}")
        print(f"4. {CLR_GREEN}{CLR_BOLD}Initiate Scraper Session 🚀{CLR_RESET}")
        print(f"5. {CLR_RED}Exit{CLR_RESET}")
        print("=" * 50)
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            await run_setup_wizard()
        elif choice == '2':
            update_settings()
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
