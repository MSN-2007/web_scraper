import sys
import asyncio

# ANSI Color codes for styled terminal output
CLR_BLUE = "\033[94m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_RED = "\033[91m"
CLR_BOLD = "\033[1m"
CLR_RESET = "\033[0m"

def main():
    # Windows terminal support for ANSI colors
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

    print(f"{CLR_BLUE}{CLR_BOLD}")
    print("┌──────────────────────────────────────────────┐")
    print("│         ⚡ Crawl4AI Launcher Pad ⚡          │")
    print("└──────────────────────────────────────────────┘")
    print(CLR_RESET)
    
    print("Choose your preferred execution environment:")
    print(f"1. {CLR_BOLD}Web Dashboard (GUI/Browser Mode){CLR_RESET}")
    print("   Start the FastAPI server and automatically open the visual control panel.")
    print(f"2. {CLR_BOLD}Developer Console (TUI Wizard Mode){CLR_RESET}")
    print("   Run crawls, configure extraction parameters, and inspect outputs directly in the terminal.")
    print(f"3. {CLR_RED}Exit{CLR_RESET}")
    print("-" * 50)
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        if choice == "1":
            print(f"\n{CLR_GREEN}Starting FastAPI server on http://127.0.0.1:8000 ...{CLR_RESET}")
            # Try to open the browser automatically
            try:
                import webbrowser
                webbrowser.open("http://127.0.0.1:8000")
            except Exception:
                pass
                
            import uvicorn
            uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
            
        elif choice == "2":
            print(f"\n{CLR_GREEN}Launching Developer TUI Console...{CLR_RESET}")
            from tui import main as tui_main
            asyncio.run(tui_main())
            
        elif choice == "3":
            print(f"\n{CLR_YELLOW}Exited launcher. Happy scraping!{CLR_RESET}")
        else:
            print(f"{CLR_RED}Invalid option selected. Exiting.{CLR_RESET}")
            
    except KeyboardInterrupt:
        print(f"\n{CLR_YELLOW}Launcher terminated.{CLR_RESET}")

if __name__ == "__main__":
    main()
