import os
import sys
import time
import json
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd

# Global state for tracking background task progress
state_lock = threading.Lock()
state = {
    "status": "idle",           # idle, running, success, error
    "progress_percent": 0.0,
    "progress_text": "",
    "total_rows": 0,
    "missing_cui_count": 0,
    "resolved_locally": 0,
    "new_missing_cui_count": 0,
    "unique_terms_to_query": 0,
    "queried_terms_count": 0,
    "cui_details_total": 0,
    "cui_details_queried": 0,
    "recent_matches": [],       # list of dicts: {"sf": SF, "lf": LF, "cui": CUI, "tui": TUI, "sem_type": Semantic_Type}
    "failed_matches": [],       # list of dicts: {"sf": SF, "lf": LF, "reason": Reason}
    "api_matched_count": 0,
    "api_unmatched_count": 0,
    "error_message": "",
    "output_file": ""
}

# Configuration saved by user
config = {
    "api_key": "",
    "selected_file": ""
}

# ===== Rate Limiter for API throughput =====
class RateLimiter:
    """Thread-safe rate limiter. Allows max_per_second requests globally."""
    def __init__(self, max_per_second=20):
        self.min_interval = 1.0 / max_per_second
        self.lock = threading.Lock()
        self.last_time = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            wait_time = self.min_interval - (now - self.last_time)
            if wait_time > 0:
                time.sleep(wait_time)
            self.last_time = time.time()

rate_limiter = RateLimiter(max_per_second=20)

# ===== TUI → Semantic Category Mapping =====
TUI_TO_CATEGORY = {
    # Chemicals & Biochemistry
    "T116": "Chemicals & Biochemistry", "T109": "Chemicals & Biochemistry",
    "T114": "Chemicals & Biochemistry", "T197": "Chemicals & Biochemistry",
    "T123": "Chemicals & Biochemistry", "T196": "Chemicals & Biochemistry",
    "T167": "Chemicals & Biochemistry", "T104": "Chemicals & Biochemistry",
    "T120": "Chemicals & Biochemistry", "T103": "Chemicals & Biochemistry",
    # Pharmacology & Therapeutics
    "T121": "Pharmacology & Therapeutics", "T200": "Pharmacology & Therapeutics",
    "T195": "Pharmacology & Therapeutics", "T125": "Pharmacology & Therapeutics",
    "T127": "Pharmacology & Therapeutics", "T131": "Pharmacology & Therapeutics",
    # Diseases & Clinical Findings
    "T047": "Diseases & Clinical Findings", "T033": "Diseases & Clinical Findings",
    "T191": "Diseases & Clinical Findings", "T046": "Diseases & Clinical Findings",
    "T048": "Diseases & Clinical Findings", "T184": "Diseases & Clinical Findings",
    "T037": "Diseases & Clinical Findings", "T049": "Diseases & Clinical Findings",
    "T019": "Diseases & Clinical Findings", "T190": "Diseases & Clinical Findings",
    "T020": "Diseases & Clinical Findings", "T050": "Diseases & Clinical Findings",
    "T034": "Diseases & Clinical Findings",
    # Procedures & Diagnostics
    "T059": "Procedures & Diagnostics", "T061": "Procedures & Diagnostics",
    "T060": "Procedures & Diagnostics", "T058": "Procedures & Diagnostics",
    "T063": "Procedures & Diagnostics", "T062": "Procedures & Diagnostics",
    "T130": "Procedures & Diagnostics",
    # Genetics & Molecular Biology
    "T028": "Genetics & Molecular Biology", "T087": "Genetics & Molecular Biology",
    "T086": "Genetics & Molecular Biology", "T085": "Genetics & Molecular Biology",
    "T045": "Genetics & Molecular Biology",
    # Anatomy & Body Structures
    "T023": "Anatomy & Body Structures", "T025": "Anatomy & Body Structures",
    "T026": "Anatomy & Body Structures", "T024": "Anatomy & Body Structures",
    "T029": "Anatomy & Body Structures", "T030": "Anatomy & Body Structures",
    "T031": "Anatomy & Body Structures", "T022": "Anatomy & Body Structures",
    "T018": "Anatomy & Body Structures", "T017": "Anatomy & Body Structures",
    "T021": "Anatomy & Body Structures",
    # Biological Functions & Processes
    "T044": "Biological Functions & Processes", "T043": "Biological Functions & Processes",
    "T042": "Biological Functions & Processes", "T039": "Biological Functions & Processes",
    "T040": "Biological Functions & Processes", "T038": "Biological Functions & Processes",
    "T070": "Biological Functions & Processes", "T067": "Biological Functions & Processes",
    "T041": "Biological Functions & Processes",
    # Organisms
    "T005": "Organisms", "T007": "Organisms", "T204": "Organisms",
    "T002": "Organisms", "T015": "Organisms", "T004": "Organisms",
    "T013": "Organisms", "T014": "Organisms", "T012": "Organisms",
    "T011": "Organisms", "T194": "Organisms", "T001": "Organisms",
    "T008": "Organisms", "T016": "Organisms", "T010": "Organisms",
    # Immunology
    "T129": "Immunology", "T192": "Immunology", "T126": "Immunology",
    # Devices & Materials
    "T074": "Devices & Materials", "T073": "Devices & Materials",
    "T122": "Devices & Materials", "T075": "Devices & Materials",
    "T203": "Devices & Materials", "T072": "Devices & Materials",
    # Concepts & Measurements
    "T081": "Concepts & Measurements", "T201": "Concepts & Measurements",
    "T080": "Concepts & Measurements", "T079": "Concepts & Measurements",
    "T082": "Concepts & Measurements", "T169": "Concepts & Measurements",
    "T032": "Concepts & Measurements", "T078": "Concepts & Measurements",
    "T077": "Concepts & Measurements", "T071": "Concepts & Measurements",
    "T102": "Concepts & Measurements",
    # Knowledge & Classification
    "T170": "Knowledge & Classification", "T185": "Knowledge & Classification",
    "T171": "Knowledge & Classification",
    # People & Organizations
    "T097": "People & Organizations", "T093": "People & Organizations",
    "T098": "People & Organizations", "T092": "People & Organizations",
    "T101": "People & Organizations", "T099": "People & Organizations",
    "T094": "People & Organizations", "T100": "People & Organizations",
    "T096": "People & Organizations", "T095": "People & Organizations",
    # Activities & Behaviors
    "T052": "Activities & Behaviors", "T056": "Activities & Behaviors",
    "T055": "Activities & Behaviors", "T054": "Activities & Behaviors",
    "T053": "Activities & Behaviors", "T057": "Activities & Behaviors",
    "T051": "Activities & Behaviors",
    # Regulation & Governance
    "T091": "Regulation & Governance", "T083": "Regulation & Governance",
    "T168": "Regulation & Governance", "T065": "Regulation & Governance",
    "T089": "Regulation & Governance", "T064": "Regulation & Governance",
    "T066": "Regulation & Governance", "T090": "Regulation & Governance",
    "T068": "Regulation & Governance", "T069": "Regulation & Governance",
}

def query_uts_search_api(term, search_type, api_key):
    """Query UTS with rate limiting and retry on 429/connection errors."""
    url = "https://uts-ws.nlm.nih.gov/rest/search/current"
    params = {
        "apiKey": api_key,
        "string": term,
        "searchType": search_type
    }
    for attempt in range(3):
        rate_limiter.wait()
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                time.sleep(1.0 * (attempt + 1))  # Back off on rate limit
                continue
            if response.status_code == 200:
                results = response.json().get("result", {}).get("results", [])
                if results:
                    return results[0].get("ui")
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(0.5 * (attempt + 1))
            continue
        except Exception:
            pass
        return None
    return None

def get_cui_from_term(term, api_key, sf=""):
    """7-stage comprehensive UMLS CUI lookup."""
    original = term

    # ===== STAGE 0a: Greek letter normalization =====
    cleaned = term
    # Insert separator when Greek letter is concatenated with word (e.g. βglycerophosphate → beta-glycerophosphate)
    for greek, latin in [('\u03b1', 'alpha'), ('\u03b2', 'beta'), ('\u03b3', 'gamma'),
                          ('\u03b4', 'delta'), ('\u03b5', 'epsilon'), ('\u03ba', 'kappa'), ('\u03bc', 'mu')]:
        cleaned = re.sub(greek + r'(?=[a-zA-Z])', latin + '-', cleaned)
        cleaned = cleaned.replace(greek, latin)

    # ===== STAGE 0b: Spelling corrections =====
    cleaned = cleaned.replace("arabiofuranosyl", "arabinofuranosyl")
    cleaned = cleaned.replace("cyclohexylenedinintrilo", "cyclohexylenedinitrilo")
    cleaned = cleaned.replace("methoxynaphtyl", "methoxynaphthyl")

    # ===== STAGE 0c: Amino acid abbreviation expansion =====
    cleaned = re.sub(r'\bArg(\d)', r'arginine-\1', cleaned)
    cleaned = re.sub(r'\bLys(\d)', r'lysine-\1', cleaned)

    # ===== STAGE 0d: Chemical name normalizations =====
    cleaned = re.sub(r'naphthalene[- ]?\d*[- ]?sulph?on(?:ate|ic acid)', 'naphthalenesulfonic acid', cleaned, flags=re.I)
    cleaned = re.sub(r'[iI]soquinolin(?:yl)?[- ]sulfonyl', 'Isoquinolinesulfonyl', cleaned)
    cleaned = cleaned.replace("(strept)avidin", "streptavidin")
    cleaned = re.sub(r'\bbi[- ]?\d*[- ]?naphthyl', 'binaphthyl', cleaned, flags=re.I)
    cleaned = re.sub(r'\biodophenyl([a-zA-Z])', r'iodophenyl \1', cleaned, flags=re.I)
    cleaned = re.sub(r'\bhydroxy\s+([a-zA-Z])', r'hydroxy\1', cleaned, flags=re.I)

    # ===== STAGE 0e: Strip stereochemistry prefixes =====
    cleaned = re.sub(r'^[\(\[\{][+\-\u00b1/sSrRdDlLzZeExXyY\d,\'\u2032\s\*]+[\)\]\}][- ]?', '', cleaned)
    cleaned = re.sub(r'(?<![a-zA-Z])[LD]-(?=[a-zA-Z])', '', cleaned)

    # ===== STAGE 0f: Isotope handling =====
    isotope_map = {'C': 'Carbon', 'F': 'Fluorine', 'I': 'Iodine', 'P': 'Phosphorus',
                   'N': 'Nitrogen', 'O': 'Oxygen', 'H': 'Hydrogen', 'S': 'Sulfur'}
    def replace_isotope(m):
        mass = m.group(1)
        element = m.group(3)
        return isotope_map.get(element.upper(), element) + '-' + mass
    cleaned = re.sub(r'[\(\[\{](\d+m?)[\)\]\}]([- ]?)([A-Za-z]{1,2})(?=[- ]|$)', replace_isotope, cleaned)

    # Strip translated isotope names to leave just the compound
    cleaned_no_isotope = re.sub(r'\b(?:Carbon|Fluorine|Iodine|Technetium|Hydrogen|Phosphorus|Nitrogen|Oxygen|Sulfur)[- ]\d+m?\b[- ]?', '', cleaned, flags=re.I)

    # ===== STAGE 0g: Procedure words =====
    cleaned_no_proc = re.sub(r'\b(scintigraphy|scintigraph|scintigraphic|scan|scans|imaging|test|tests|assay|assays|therapy|spect|pet|ultrasound|mri|xray|radiography|breath test)\b', '', cleaned_no_isotope, flags=re.I)

    # ===== Finalize cleaning =====
    def _finalize(s):
        s = s.replace("-", " ")
        s = " ".join(s.split()).strip()
        if s.startswith("(") and s.endswith(")"): s = s[1:-1].strip()
        if s.startswith("[") and s.endswith("]"): s = s[1:-1].strip()
        return s.replace("[]", "").replace("()", "").strip()

    v_full = _finalize(cleaned)
    v_no_iso = _finalize(cleaned_no_isotope)
    v_no_proc = _finalize(cleaned_no_proc)
    v_concat = v_no_proc.replace(" ", "")

    # Deduplicate variants to avoid redundant API calls
    unique_variants = list(dict.fromkeys([v for v in [v_full, v_no_iso, v_no_proc] if v and len(v) >= 2]))

    # ===== STAGE 1: normalizedString =====
    for variant in unique_variants:
        cui = query_uts_search_api(variant, "normalizedString", api_key)
        if cui: return cui

    # ===== STAGE 2: words =====
    for variant in unique_variants:
        cui = query_uts_search_api(variant, "words", api_key)
        if cui: return cui

    # ===== STAGE 3: concatenated =====
    if v_concat and v_concat != v_no_proc and len(v_concat) > 2:
        cui = query_uts_search_api(v_concat, "normalizedString", api_key)
        if cui: return cui

    # ===== STAGE 4: original term (skip if same as a variant) =====
    if original not in unique_variants:
        cui = query_uts_search_api(original, "normalizedString", api_key)
        if cui: return cui
        cui = query_uts_search_api(original, "words", api_key)
        if cui: return cui

    # ===== STAGE 5: keyword extraction =====
    words = [w for w in re.split(r'[\s\-,;()[\]{}]+', v_no_proc) if len(w) > 4 and not w.isdigit()]
    if words:
        kw_query = " ".join(words)
        cui = query_uts_search_api(kw_query, "words", api_key)
        if cui: return cui

    # ===== STAGE 6: Short Form (abbreviation) fallback =====
    if sf and len(str(sf)) >= 2:
        for st in ["normalizedString", "approximate"]:
            cui = query_uts_search_api(str(sf), st, api_key)
            if cui: return cui

    # ===== STAGE 7: approximate search =====
    approx_variants = list(dict.fromkeys([v for v in [v_no_proc, v_full] if v and len(v) >= 2]))
    for variant in approx_variants:
        cui = query_uts_search_api(variant, "approximate", api_key)
        if cui: return cui

    return None

def get_tui_from_cui(cui, api_key):
    cui_normalized = str(cui).strip().upper()
    if not cui_normalized.startswith('C'):
        return None, None
        
    url = f"https://uts-ws.nlm.nih.gov/rest/content/current/CUI/{cui_normalized}"
    params = {"apiKey": api_key}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            semantic_types = data.get("result", {}).get("semanticTypes", [])
            if semantic_types:
                sem_type_info = semantic_types[0]
                sem_name = sem_type_info.get("name", "")
                uri = sem_type_info.get("uri", "")
                tui = uri.split("/")[-1] if uri else ""
                return tui, sem_name
        elif response.status_code == 401:
            with state_lock:
                state["error_message"] = "Invalid NLM API Key."
            return "ERROR_API_KEY", None
    except Exception:
        pass
    return None, None

def run_enrichment_thread():
    global state
    with state_lock:
        state["status"] = "running"
        state["progress_percent"] = 0.0
        state["progress_text"] = "Loading CSV file..."
        state["error_message"] = ""
        state["recent_matches"] = []
        state["failed_matches"] = []
        state["api_matched_count"] = 0
        state["api_unmatched_count"] = 0
    
    input_file = config["selected_file"]
    api_key = config["api_key"]
    
    try:
        df = pd.read_csv(input_file, sep='|', low_memory=False)
    except Exception as e:
        with state_lock:
            state["status"] = "error"
            state["error_message"] = f"Could not read CSV file: {str(e)}"
        return
        
    # Check for CUI column
    cui_col = ""
    for col in df.columns:
        if col.lower() in ["umls.cui", "cui", "umls_cui", "umls cui"]:
            cui_col = col
            break
            
    if not cui_col:
        with state_lock:
            state["status"] = "error"
            state["error_message"] = f"Could not find Concept ID column in CSV."
        return
        
    # Clean CUI column values
    df[cui_col] = df[cui_col].astype(str).str.strip()
    df.loc[df[cui_col].str.lower() == 'nan', cui_col] = None
    df.loc[df[cui_col] == '', cui_col] = None
    
    total_rows = int(len(df))
    missing_count = int(df[cui_col].isna().sum())
    
    with state_lock:
        state["total_rows"] = total_rows
        state["missing_cui_count"] = missing_count
        state["progress_text"] = "Propagating existing CUIs locally..."
        state["progress_percent"] = 5.0

    # Step A: Local propagation by clean_norm_lf
    def normalize_term(val):
        if pd.isna(val) or not isinstance(val, str):
            return ""
        val = val.lower().strip()
        val = val.replace("-", " ")
        return " ".join(val.split())
        
    norm_col = "clean_norm_lf"
    df[norm_col] = df["NormLF"].fillna(df["LF"]).apply(normalize_term)
    
    # Map clean_norm_lf to CUI based on existing non-null rows
    norm_to_cui = df.groupby(norm_col)[cui_col].first().dropna().to_dict()
    df[cui_col] = df[cui_col].fillna(df[norm_col].map(norm_to_cui))
    
    new_missing = int(df[cui_col].isna().sum())
    resolved_locally = int(missing_count - new_missing)
    
    with state_lock:
        state["resolved_locally"] = resolved_locally
        state["new_missing_cui_count"] = new_missing
        state["progress_percent"] = 10.0
        
    # Step B: API lookup for remaining unique concepts
    if new_missing > 0:
        missing_mask = df[cui_col].isna()
        norm_lf_to_search_term = df[missing_mask].groupby(norm_col)['LF'].first().dropna().to_dict()
        if "" in norm_lf_to_search_term:
            del norm_lf_to_search_term[""]
        unique_terms = list(norm_lf_to_search_term.values())
        
        with state_lock:
            state["unique_terms_to_query"] = len(unique_terms)
            state["queried_terms_count"] = 0
            state["progress_text"] = f"Searching CUIs for {len(unique_terms)} unique terms..."

        # Pre-compute SF values to avoid slow DataFrame lookups inside threads
        temp_sf_df = df.dropna(subset=[norm_col]).drop_duplicates(subset=[norm_col])
        norm_lf_to_sf = dict(zip(temp_sf_df[norm_col].astype(str), temp_sf_df["SF"].astype(str)))

        found_cuis = {}
        completed_count = [0]  # mutable counter for threads
        total_terms = len(norm_lf_to_search_term)
        
        def process_term(norm_lf, search_term, sf_val):
            """Process a single term — called from thread pool."""
            cui = get_cui_from_term(search_term, api_key, sf=sf_val)
            return norm_lf, search_term, sf_val, cui
        
        # Use ThreadPoolExecutor for concurrent API lookups
        WORKERS = 5
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {}
            for norm_lf, search_term in norm_lf_to_search_term.items():
                sf_val = norm_lf_to_sf.get(norm_lf, "")
                future = executor.submit(process_term, norm_lf, search_term, sf_val)
                futures[future] = norm_lf
            
            for future in as_completed(futures):
                norm_lf, search_term, sf_val, cui = future.result()
                completed_count[0] += 1
                
                if cui:
                    found_cuis[norm_lf] = cui
                    with state_lock:
                        state["api_matched_count"] += 1
                        match_log = {
                            "sf": str(sf_val),
                            "lf": str(search_term),
                            "cui": str(cui),
                            "tui": "-",
                            "sem_type": "Mapped CUI"
                        }
                        state["recent_matches"].append(match_log)
                        if len(state["recent_matches"]) > 40:
                            state["recent_matches"].pop(0)
                else:
                    with state_lock:
                        state["api_unmatched_count"] += 1
                        fail_log = {
                            "sf": str(sf_val),
                            "lf": str(search_term),
                            "reason": "No match found in UMLS"
                        }
                        state["failed_matches"].append(fail_log)
                        if len(state["failed_matches"]) > 40:
                            state["failed_matches"].pop(0)
                
                progress = 10.0 + completed_count[0] / total_terms * 40.0
                with state_lock:
                    state["queried_terms_count"] = completed_count[0]
                    state["progress_percent"] = round(progress, 1)
                    state["progress_text"] = f"CUI Search: {completed_count[0]}/{total_terms} terms ({WORKERS} parallel)"
        
        # Fill newly discovered CUIs back into DataFrame
        df[cui_col] = df[cui_col].fillna(df[norm_col].map(found_cuis))

    # Step C: Retrieve TUI details for unique CUIs
    unique_cuis = df[cui_col].dropna().unique()
    unique_cuis = [str(c).strip() for c in unique_cuis if str(c).strip() and str(c).strip().lower() != 'nan']
    
    with state_lock:
        state["cui_details_total"] = len(unique_cuis)
        state["cui_details_queried"] = 0
        state["progress_text"] = f"Querying Semantic Type details for {len(unique_cuis)} CUIs..."
        state["progress_percent"] = 50.0
    cui_to_tui = {}
    cui_to_semantic = {}
    
    temp_cui_df = df.dropna(subset=[cui_col]).drop_duplicates(subset=[cui_col])
    cui_to_sample = dict(zip(temp_cui_df[cui_col].astype(str), zip(temp_cui_df["SF"].astype(str), temp_cui_df["LF"].astype(str))))
    
    tui_completed = [0]
    tui_total = len(unique_cuis)
    error_flag = [False]
    
    def process_tui(cui_val):
        tui, sem_name = get_tui_from_cui(cui_val, api_key)
        return cui_val, tui, sem_name
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_tui, c) for c in unique_cuis]
        
        for future in as_completed(futures):
            cui_val, tui, sem_name = future.result()
            tui_completed[0] += 1
            
            if tui == "ERROR_API_KEY":
                with state_lock:
                    state["status"] = "error"
                    state["error_message"] = "Invalid NLM API Key."
                error_flag[0] = True
                executor.shutdown(wait=False, cancel_futures=True)
                return
                
            if tui:
                cui_to_tui[cui_val] = tui
                cui_to_semantic[cui_val] = sem_name
                
                if cui_val in cui_to_sample:
                    sf_val, lf_val = cui_to_sample[cui_val]
                    with state_lock:
                        match_log = {"sf": sf_val, "lf": lf_val, "cui": str(cui_val), "tui": str(tui), "sem_type": str(sem_name)}
                        state["recent_matches"].append(match_log)
                        if len(state["recent_matches"]) > 40: state["recent_matches"].pop(0)
                        
            progress = 50.0 + tui_completed[0] / tui_total * 45.0
            with state_lock:
                state["cui_details_queried"] = tui_completed[0]
                state["progress_percent"] = round(progress, 1)
                state["progress_text"] = f"Semantic Types: {tui_completed[0]}/{tui_total} CUIs (5 parallel)"
            
    df["TUI"] = df[cui_col].map(cui_to_tui)
    df["Semantic_Type"] = df[cui_col].map(cui_to_semantic)
    df["Semantic_Category"] = df["TUI"].map(TUI_TO_CATEGORY)
    
    with state_lock:
        state["progress_text"] = "Saving output CSV file..."
        state["progress_percent"] = 96.0
        
    df.drop(columns=[norm_col], inplace=True, errors='ignore')
    
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_with_tui{ext}"
    
    try:
        df.to_csv(output_file, sep='|', index=False)
        with state_lock:
            state["status"] = "success"
            state["progress_percent"] = 100.0
            state["progress_text"] = f"Enrichment completed!"
            state["output_file"] = output_file
    except Exception as e:
        with state_lock:
            state["status"] = "error"
            state["error_message"] = f"Could not save output file: {str(e)}"

# Custom Request Handler to handle API calls and serve frontend files
class AppRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence standard HTTP logs in stdout for cleaner CLI output
        pass

    def do_GET(self):
        # Serve Frontend Assets
        if self.path == "/" or self.path == "/index.html":
            self.serve_file("web/index.html", "text/html")
        elif self.path == "/style.css":
            self.serve_file("web/style.css", "text/css")
        elif self.path == "/app.js":
            self.serve_file("web/app.js", "application/javascript")
            
        # REST API endpoints
        elif self.path == "/api/files":
            csv_files = [f for f in os.listdir(".") if f.endswith(".csv") and "cleaned" not in f and "review" not in f]
            self.send_json({"files": csv_files})
        elif self.path == "/api/status":
            with state_lock:
                self.send_json(state)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""
        
        body = {}
        if content_length > 0:
            try:
                body = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_error_response(400, "Invalid JSON body")
                return
            
        if self.path == "/api/config":
            api_key = body.get("api_key", "").strip()
            selected_file = body.get("selected_file", "").strip()
            
            if not api_key:
                self.send_error_response(400, "API Key is required")
                return
            if not selected_file or not os.path.exists(selected_file):
                self.send_error_response(400, f"CSV File '{selected_file}' not found")
                return
                
            config["api_key"] = api_key
            config["selected_file"] = selected_file
            self.send_json({"status": "configured"})
            
        elif self.path == "/api/start":
            # Check if already running
            with state_lock:
                current_status = state["status"]
            if current_status == "running":
                self.send_error_response(400, "Enrichment is already running")
                return
                
            # Trigger background processing
            t = threading.Thread(target=run_enrichment_thread)
            t.daemon = True
            t.start()
            self.send_json({"status": "started"})
        else:
            self.send_response(404)
            self.end_headers()

    def serve_file(self, rel_path, mime_type):
        if not os.path.exists(rel_path):
            self.send_response(404)
            self.end_headers()
            return
            
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        with open(rel_path, "rb") as f:
            self.wfile.write(f.read())

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))

def main():
    # Make sure web directory and empty assets exist
    os.makedirs("web", exist_ok=True)
    
    port = 8000
    server = HTTPServer(("localhost", port), AppRequestHandler)
    print("=" * 60)
    print(f"Visual Abbreviations Enrichment Server started at:")
    print(f"-> http://localhost:{port}")
    print("=" * 60)
    print("Press Ctrl+C to stop the server.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping visual server...")
        server.server_close()

if __name__ == "__main__":
    main()
