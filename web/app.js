document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const configForm = document.getElementById("config-form");
    const apiKeyInput = document.getElementById("api-key");
    const csvFileSelect = document.getElementById("csv-file");
    const startBtn = document.getElementById("start-btn");
    
    const configCard = document.getElementById("config-card");
    const statsContainer = document.getElementById("stats-container");
    const progressCard = document.getElementById("progress-card");
    const matchesCard = document.getElementById("matches-card");
    const successCard = document.getElementById("success-card");
    
    // Stats elements
    const statTotal = document.getElementById("stat-total");
    const statMissing = document.getElementById("stat-missing");
    const statLocal = document.getElementById("stat-local");
    const statApi = document.getElementById("stat-api");
    
    // Progress elements
    const progressStatus = document.getElementById("progress-status");
    const progressPercent = document.getElementById("progress-percent");
    const progressFill = document.getElementById("progress-fill");
    const progressText = document.getElementById("progress-text");
    const timerText = document.getElementById("timer-text");
    
    // Table elements
    const matchesTbody = document.getElementById("matches-tbody");
    const unmatchedTbody = document.getElementById("unmatched-tbody");
    const matchedCount = document.getElementById("matched-count");
    const unmatchedCount = document.getElementById("unmatched-count");
    const successFilepath = document.getElementById("success-filepath");
    
    // State Variables
    let pollInterval = null;
    let startTime = null;
    let timerInterval = null;
    const renderedMatches = new Set(); // Keep track of rendered items to animate new ones
    const renderedFailures = new Set(); // Keep track of rendered unmatched items to animate new ones

    // Tab switching logic
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(pane => {
                pane.classList.remove("active");
                pane.style.display = "none";
            });
            
            btn.classList.add("active");
            const targetTab = btn.getAttribute("data-tab");
            const targetPane = document.getElementById(`pane-${targetTab}`);
            if (targetPane) {
                targetPane.classList.add("active");
                targetPane.style.display = "block";
            }
        });
    });

    // Load available files on load
    fetchFiles();

    // Check if configuration already has default key
    fetch("/api/status")
        .then(res => res.json())
        .then(data => {
            // Pre-fill key if server has it (e.g. from script CONFIGURATION block)
            // It might be empty or a UUID. If it's a real key, display it masked.
            // Wait, we can check if it's set on backend.
        });
        
    // API key must be entered by the user
    apiKeyInput.value = "";

    function fetchFiles() {
        fetch("/api/files")
            .then(res => res.json())
            .then(data => {
                csvFileSelect.innerHTML = "";
                if (data.files && data.files.length > 0) {
                    data.files.forEach(file => {
                        const opt = document.createElement("option");
                        opt.value = file;
                        opt.textContent = file;
                        csvFileSelect.appendChild(opt);
                    });
                    startBtn.disabled = false;
                } else {
                    const opt = document.createElement("option");
                    opt.value = "";
                    opt.textContent = "No CSV files found in directory!";
                    csvFileSelect.appendChild(opt);
                    csvFileSelect.disabled = true;
                    startBtn.disabled = true;
                }
            })
            .catch(err => {
                console.error("Error fetching files:", err);
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = "Error scanning directory!";
                csvFileSelect.appendChild(opt);
            });
    }

    // Form submission
    configForm.addEventListener("submit", (e) => {
        e.preventDefault();
        
        const apiKey = apiKeyInput.value.trim();
        const selectedFile = csvFileSelect.value;
        
        if (!apiKey || !selectedFile) return;
        
        startBtn.disabled = true;
        startBtn.textContent = "Configuring...";

        // 1. Send Configuration
        fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                api_key: apiKey,
                selected_file: selectedFile
            })
        })
        .then(res => {
            if (!res.ok) throw new Error("Configuration failed on server");
            return res.json();
        })
        .then(() => {
            startBtn.textContent = "Launching pipeline...";
            // 2. Start Enrichment Task
            return fetch("/api/start", { method: "POST" });
        })
        .then(res => {
            if (!res.ok) throw new Error("Failed to start enrichment thread");
            return res.json();
        })
        .then(() => {
            // UI Transition
            configCard.style.display = "none";
            statsContainer.style.display = "grid";
            progressCard.style.display = "block";
            matchesCard.style.display = "block";
            
            // Start Timer
            startTime = Date.now();
            timerInterval = setInterval(updateTimer, 1000);
            
            // Start Polling Status
            pollInterval = setInterval(pollStatus, 500);
        })
        .catch(err => {
            alert("Error: " + err.message);
            startBtn.disabled = false;
            startBtn.textContent = "Start Enrichment Process";
        });
    });

    function updateTimer() {
        if (!startTime) return;
        const elapsedSecs = Math.floor((Date.now() - startTime) / 1000);
        
        let timeStr = "";
        if (elapsedSecs < 60) {
            timeStr = `${elapsedSecs}s`;
        } else {
            const mins = Math.floor(elapsedSecs / 60);
            const secs = elapsedSecs % 60;
            timeStr = `${mins}m ${secs}s`;
        }
        timerText.textContent = `Elapsed: ${timeStr}`;
    }

    function pollStatus() {
        fetch("/api/status")
            .then(res => res.json())
            .then(data => {
                // Update stats counts
                statTotal.textContent = data.total_rows.toLocaleString() || "-";
                statMissing.textContent = data.missing_cui_count.toLocaleString() || "-";
                statLocal.textContent = data.resolved_locally.toLocaleString() || "-";
                statApi.textContent = data.unique_terms_to_query.toLocaleString() || "-";
                
                // Update tab counts
                matchedCount.textContent = data.api_matched_count || 0;
                unmatchedCount.textContent = data.api_unmatched_count || 0;
                
                // Update progress bar
                progressPercent.textContent = `${data.progress_percent}%`;
                progressFill.style.width = `${data.progress_percent}%`;
                progressText.textContent = data.progress_text;
                
                // Update progress status header depending on state
                if (data.status === "running") {
                    progressStatus.textContent = "Processing Enrichment...";
                } else if (data.status === "success") {
                    handleSuccess(data.output_file);
                } else if (data.status === "error") {
                    handleError(data.error_message);
                }
                
                // Update live matches list
                if (data.recent_matches && data.recent_matches.length > 0) {
                    renderMatches(data.recent_matches);
                }
                
                // Update live unmatched list
                if (data.failed_matches && data.failed_matches.length > 0) {
                    renderFailures(data.failed_matches);
                }
            })
            .catch(err => {
                console.error("Status polling failed:", err);
            });
    }

    function renderMatches(matches) {
        // Remove empty row if present
        const emptyRow = matchesTbody.querySelector(".empty-row");
        if (emptyRow) {
            matchesTbody.innerHTML = "";
        }
        
        // Render matches (in reverse order so newest are appended at the top)
        for (let i = matches.length - 1; i >= 0; i--) {
            const match = matches[i];
            const matchKey = `${match.sf}_${match.lf}_${match.cui}_${match.tui}`;
            
            if (!renderedMatches.has(matchKey)) {
                renderedMatches.add(matchKey);
                
                const tr = document.createElement("tr");
                tr.classList.add("new-row");
                
                const tdSF = document.createElement("td");
                tdSF.innerHTML = `<strong>${escapeHtml(match.sf)}</strong>`;
                
                const tdLF = document.createElement("td");
                tdLF.textContent = match.lf;
                
                const tdCUI = document.createElement("td");
                tdCUI.innerHTML = `<code style="color: var(--accent-blue);">${escapeHtml(match.cui)}</code>`;
                
                const tdTUI = document.createElement("td");
                tdTUI.textContent = match.tui;
                
                const tdSem = document.createElement("td");
                tdSem.textContent = match.sem_type;
                
                tr.appendChild(tdSF);
                tr.appendChild(tdLF);
                tr.appendChild(tdCUI);
                tr.appendChild(tdTUI);
                tr.appendChild(tdSem);
                
                // Insert at the top of the table
                matchesTbody.insertBefore(tr, matchesTbody.firstChild);
                
                // Keep only top 50 rows in DOM
                if (matchesTbody.children.length > 50) {
                    matchesTbody.removeChild(matchesTbody.lastChild);
                }
            }
        }
    }

    function renderFailures(failures) {
        // Remove empty row if present
        const emptyRow = unmatchedTbody.querySelector(".empty-row");
        if (emptyRow) {
            unmatchedTbody.innerHTML = "";
        }
        
        // Render failures (in reverse order so newest are appended at the top)
        for (let i = failures.length - 1; i >= 0; i--) {
            const fail = failures[i];
            const failKey = `${fail.sf}_${fail.lf}_${fail.reason}`;
            
            if (!renderedFailures.has(failKey)) {
                renderedFailures.add(failKey);
                
                const tr = document.createElement("tr");
                tr.classList.add("new-fail-row");
                
                const tdSF = document.createElement("td");
                tdSF.innerHTML = `<strong>${escapeHtml(fail.sf)}</strong>`;
                
                const tdLF = document.createElement("td");
                tdLF.textContent = fail.lf;
                
                const tdReason = document.createElement("td");
                tdReason.innerHTML = `<span style="color: #f87171;">${escapeHtml(fail.reason)}</span>`;
                
                tr.appendChild(tdSF);
                tr.appendChild(tdLF);
                tr.appendChild(tdReason);
                
                // Insert at the top of the table
                unmatchedTbody.insertBefore(tr, unmatchedTbody.firstChild);
                
                // Keep only top 50 rows in DOM
                if (unmatchedTbody.children.length > 50) {
                    unmatchedTbody.removeChild(unmatchedTbody.lastChild);
                }
            }
        }
    }

    function handleSuccess(outputFile) {
        clearInterval(pollInterval);
        clearInterval(timerInterval);
        
        progressCard.style.display = "none";
        successCard.style.display = "flex";
        successFilepath.textContent = outputFile;
    }

    function handleError(errorMsg) {
        clearInterval(pollInterval);
        clearInterval(timerInterval);
        
        progressCard.style.display = "none";
        configCard.style.display = "block";
        startBtn.disabled = false;
        startBtn.textContent = "Start Enrichment Process";
        
        alert("Enrichment Failed: " + errorMsg);
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});
