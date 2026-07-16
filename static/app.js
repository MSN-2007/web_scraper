document.addEventListener("DOMContentLoaded", () => {
    const scrapeForm = document.getElementById("scrape-form");
    const startBtn = document.getElementById("start-btn");
    const btnText = startBtn.querySelector(".btn-text");
    const btnLoader = startBtn.querySelector(".btn-loader");
    
    const apiKeyInput = document.getElementById("api-key");
    const toggleKeyVisibilityBtn = document.getElementById("toggle-key-visibility");
    
    const consoleLogs = document.getElementById("console-logs");
    const clearConsoleBtn = document.getElementById("clear-console-btn");
    
    const filesListTbody = document.getElementById("files-list-tbody");
    const systemStatus = document.getElementById("system-status");

    // Schema and Prompt controls
    const schemaPromptInput = document.getElementById("schema-prompt");
    const applyPromptBtn = document.getElementById("apply-prompt-btn");
    const nlpLoader = applyPromptBtn.querySelector(".nlp-loader");
    const schemaChecklistContainer = document.getElementById("schema-checklist-container");

    // Toggle API Key visibility
    toggleKeyVisibilityBtn.addEventListener("click", () => {
        if (apiKeyInput.type === "password") {
            apiKeyInput.type = "text";
            toggleKeyVisibilityBtn.textContent = "🙈";
        } else {
            apiKeyInput.type = "password";
            toggleKeyVisibilityBtn.textContent = "👁️";
        }
    });

    // Clear logs console
    clearConsoleBtn.addEventListener("click", () => {
        consoleLogs.innerHTML = `<div class="log-line system-msg">Console logs cleared. Ready...</div>`;
    });

    // Write a line to the console logs
    function appendLog(message, type = "system-msg") {
        const line = document.createElement("div");
        line.className = `log-line ${type}`;
        
        // Format timestamp
        const now = new Date();
        const timeStr = now.toTimeString().split(" ")[0];
        
        line.innerHTML = `<span class="system-msg">[${timeStr}]</span> ${message}`;
        consoleLogs.appendChild(line);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Set UI state (scraping vs idle)
    function setScrapingState(isScraping) {
        if (isScraping) {
            startBtn.disabled = true;
            btnText.textContent = "Crawling & Processing...";
            btnLoader.classList.remove("hidden");
            
            systemStatus.innerHTML = `<span class="status-dot orange"></span> Scraping In Progress`;
            systemStatus.querySelector(".status-dot").style.color = "#ffa800";
        } else {
            startBtn.disabled = false;
            btnText.textContent = "Initiate Crawler Session";
            btnLoader.classList.add("hidden");
            
            systemStatus.innerHTML = `<span class="status-dot green"></span> Ready`;
            systemStatus.querySelector(".status-dot").style.color = "#00f29f";
        }
    }

    // Load available files list
    async function loadFilesList() {
        try {
            const response = await fetch("/api/files");
            if (!response.ok) throw new Error("Failed to load file list");
            
            const data = await response.json();
            
            if (!data.files || data.files.length === 0) {
                filesListTbody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="3">No datasets generated yet. Start a crawler session to compile data.</td>
                    </tr>
                `;
                return;
            }
            
            filesListTbody.innerHTML = "";
            data.files.forEach(file => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${file.filename}</strong></td>
                    <td><span class="system-msg">${file.folder}</span></td>
                    <td>
                        <a href="/api/download?folder=${encodeURIComponent(file.folder)}&file=${encodeURIComponent(file.filename)}" 
                           class="file-link" download>
                           Download CSV ⬇️
                        </a>
                    </td>
                `;
                filesListTbody.appendChild(tr);
            });
        } catch (error) {
            console.error("Error loading file list:", error);
            appendLog(`Error loading available files: ${error.message}`, "error");
        }
    }

    let schemaConfig = {};

    // Load initial schema definition from backend
    async function loadSchema() {
        try {
            const response = await fetch("/api/schema");
            if (!response.ok) throw new Error("Failed to fetch schema configuration");
            schemaConfig = await response.json();
            renderSchemaChecklist();
        } catch (error) {
            console.error("Error loading schema:", error);
            schemaChecklistContainer.innerHTML = `<div class="checklist-loading" style="color: var(--accent-pink);">Error loading library schema: ${error.message}</div>`;
        }
    }

    // Render interactive checklist items dynamically
    function renderSchemaChecklist() {
        if (!schemaConfig || Object.keys(schemaConfig).length === 0) {
            schemaChecklistContainer.innerHTML = `<div class="checklist-loading">No library fields available.</div>`;
            return;
        }

        schemaChecklistContainer.innerHTML = "";
        
        Object.entries(schemaConfig).forEach(([key, info]) => {
            const item = document.createElement("div");
            item.className = `schema-item ${info.active ? 'active' : ''}`;
            
            const isNameField = key === "name";
            const checkedAttr = info.active ? "checked" : "";
            const disabledAttr = isNameField ? "disabled" : "";

            item.innerHTML = `
                <div class="schema-checkbox-wrapper">
                    <input type="checkbox" id="check-${key}" ${checkedAttr} ${disabledAttr}>
                </div>
                <div class="schema-item-details">
                    <div class="schema-item-header">
                        <span class="schema-item-name">${key}</span>
                        <span class="schema-item-type">${info.type}</span>
                    </div>
                    <div class="schema-item-desc">${info.description}</div>
                </div>
            `;

            // Toggle item state on click
            if (!isNameField) {
                item.addEventListener("click", (e) => {
                    if (e.target.tagName === "INPUT") {
                        schemaConfig[key].active = e.target.checked;
                    } else {
                        const checkbox = item.querySelector("input[type='checkbox']");
                        checkbox.checked = !checkbox.checked;
                        schemaConfig[key].active = checkbox.checked;
                    }
                    
                    if (schemaConfig[key].active) {
                        item.classList.add("active");
                    } else {
                        item.classList.remove("active");
                    }
                });
            }

            schemaChecklistContainer.appendChild(item);
        });
    }

    // Apply Prompt mapping via Gemini NLP analysis
    applyPromptBtn.addEventListener("click", async () => {
        const promptText = schemaPromptInput.value.trim();
        const apiKey = apiKeyInput.value.trim();

        if (!promptText) {
            appendLog("Please enter a description of the data you want to extract.", "warning");
            return;
        }

        applyPromptBtn.disabled = true;
        nlpLoader.classList.remove("hidden");
        appendLog(`Analyzing extraction request: "${promptText}"`, "system-msg");

        try {
            const response = await fetch("/api/parse-schema", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    api_key: apiKey || null,
                    prompt: promptText,
                    schema_config: schemaConfig
                })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Server error ${response.status}`);
            }

            schemaConfig = await response.json();
            renderSchemaChecklist();
            
            const activeFields = Object.entries(schemaConfig)
                .filter(([_, info]) => info.active)
                .map(([key]) => key);
                
            appendLog(`Schema updated. Activated fields: ${activeFields.join(", ")}`, "success");
        } catch (error) {
            console.error("Error parsing schema:", error);
            appendLog(`Schema analysis failed: ${error.message}`, "error");
        } finally {
            applyPromptBtn.disabled = false;
            nlpLoader.classList.add("hidden");
        }
    });

    // Submit Scrape Request
    scrapeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const apiKey = apiKeyInput.value.trim();
        const url = document.getElementById("scrape-url").value.trim();
        const cssSelector = document.getElementById("css-selector").value.trim();
        const folderName = document.getElementById("folder-name").value.trim();
        const fileName = document.getElementById("file-name").value.trim();

        if (!url) {
            appendLog("Target URL is required.", "error");
            return;
        }

        setScrapingState(true);
        appendLog(`Initiating scraper connection to: ${url}`, "system-msg");
        appendLog(`Output location configured: ${folderName}/${fileName}`, "system-msg");

        try {
            const response = await fetch("/api/scrape", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    api_key: apiKey || null,
                    url: url,
                    css_selector: cssSelector || "div.resultbox",
                    folder_name: folderName || "scraped_data",
                    file_name: fileName || "venues.csv",
                    schema_config: schemaConfig
                })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Server returned error status ${response.status}`);
            }

            // Stream logs from the backend
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                
                // Keep the last partial line in the buffer
                buffer = lines.pop();
                
                for (const line of lines) {
                    if (line.trim().startsWith("data: ")) {
                        try {
                            const rawJson = line.replace("data: ", "").trim();
                            const logObj = JSON.parse(rawJson);
                            
                            // Map log status level to visual styling class
                            let cssClass = "running";
                            if (logObj.level === "INFO") cssClass = "running";
                            if (logObj.level === "SUCCESS") cssClass = "success";
                            if (logObj.level === "WARNING") cssClass = "warning";
                            if (logObj.level === "ERROR") cssClass = "error";
                            
                            appendLog(logObj.message, cssClass);
                        } catch (err) {
                            // If not JSON, print line content
                            appendLog(line, "running");
                        }
                    }
                }
            }
            
            appendLog("Scraping sequence completed.", "success");
        } catch (error) {
            console.error("Scraping execution failed:", error);
            appendLog(`Execution error: ${error.message}`, "error");
        } finally {
            setScrapingState(false);
            loadFilesList(); // Refresh datasets
        }
    });

    // Initial load
    loadSchema();
    loadFilesList();
});
