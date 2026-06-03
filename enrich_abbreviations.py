"""
OMOP Mapper — Abbreviation Enrichment Script
===========================================
This script reads the downloaded clinical abbreviations CSV file, extracts the
UMLS Concept Unique Identifiers (from the `UMLS.CUI` column), and queries the
National Library of Medicine (NLM) UTS API to append the correct TUI and Semantic Type.

Prerequisites:
  1. Install requests: `pip install requests`
  2. Sign up for a free NLM UTS account to get an API Key:
     https://uts.nlm.nih.gov/uts/signup-login
  3. Place your downloaded clinical abbreviations CSV in this folder.
"""

import os
import sys
import time
import requests
import pandas as pd
import re

# ==========================================
# CONFIGURATION
# ==========================================
# Paste your NLM UTS API Key here to run the script without prompting.
# Leave it empty ("") to be prompted in the terminal.
API_KEY = ""
# ==========================================

def query_uts_search_api(term, search_type, api_key):
    url = "https://uts-ws.nlm.nih.gov/rest/search/current"
    params = {
        "apiKey": api_key,
        "string": term,
        "searchType": search_type
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            results = response.json().get("result", {}).get("results", [])
            if results:
                return results[0].get("ui")
    except Exception:
        pass
    return None

def get_cui_from_term(term, api_key, sf=""):
    """7-stage comprehensive UMLS CUI lookup."""
    original = term

    # ===== STAGE 0a: Greek letter normalization =====
    cleaned = term
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

    # ===== STAGE 1: normalizedString =====
    for variant in [v_full, v_no_iso, v_no_proc]:
        if not variant or len(variant) < 2: continue
        cui = query_uts_search_api(variant, "normalizedString", api_key)
        if cui: return cui

    # ===== STAGE 2: words =====
    for variant in [v_full, v_no_iso, v_no_proc]:
        if not variant or len(variant) < 2: continue
        cui = query_uts_search_api(variant, "words", api_key)
        if cui: return cui

    # ===== STAGE 3: concatenated =====
    if v_concat and v_concat != v_no_proc and len(v_concat) > 2:
        cui = query_uts_search_api(v_concat, "normalizedString", api_key)
        if cui: return cui

    # ===== STAGE 4: original term =====
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
    for variant in [v_no_proc, v_full]:
        if not variant or len(variant) < 2: continue
        cui = query_uts_search_api(variant, "approximate", api_key)
        if cui: return cui

    return None

def get_tui_from_cui(cui, api_key):
    """
    Query NLM UTS API to retrieve Semantic Type (TUI and Name) for a given UMLS CUI.
    """
    # Normalize CUI (UMLS expects uppercase 'C' followed by numbers)
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
                # Extract first semantic type mapping
                sem_type_info = semantic_types[0]
                sem_name = sem_type_info.get("name", "")
                
                # Extract TUI from the URI (e.g. 'https://.../T047' -> 'T047')
                uri = sem_type_info.get("uri", "")
                tui = uri.split("/")[-1] if uri else ""
                
                return tui, sem_name
        elif response.status_code == 401:
            print("\n[ERROR] Invalid NLM API Key. Please verify your UTS API Key.")
            sys.exit(1)
    except Exception as e:
        # Silently fail for individual network timeouts, return None
        pass
        
    return None, None

def main():
    print("=" * 60)
    print("Clinical Abbreviations Enrichment Tool (CUI -> TUI)")
    print("=" * 60)
    
    # 1. Locate the input CSV file
    input_file = ""
    csv_files = [f for f in os.listdir(".") if f.endswith(".csv") and "cleaned" not in f and "review" not in f]
    
    if csv_files:
        if len(csv_files) == 1:
            input_file = csv_files[0]
            print(f"Auto-detected clinical abbreviations file: '{input_file}'")
        else:
            print("Multiple CSV files found in the directory:")
            for idx, file in enumerate(csv_files):
                print(f"  [{idx + 1}] {file}")
            choice = input(f"Please select a file (1-{len(csv_files)}): ").strip()
            try:
                input_file = csv_files[int(choice) - 1]
            except Exception:
                print("[ERROR] Invalid selection.")
                return
    else:
        input_file = input("Enter the path to your clinical abbreviations CSV file: ").strip()
        
    if not os.path.exists(input_file):
        print(f"[ERROR] File '{input_file}' not found.")
        return
        
    # 2. Read the CSV file
    try:
        df = pd.read_csv(input_file, sep='|', low_memory=False)
        print(f"Successfully loaded '{input_file}' ({len(df)} rows).")
    except Exception as e:
        print(f"[ERROR] Could not read CSV file: {e}")
        return
        
    # 3. Verify CUI column exists
    cui_col = ""
    # Check for common CUI column names (case-insensitive)
    for col in df.columns:
        if col.lower() in ["umls.cui", "cui", "umls_cui", "umls cui"]:
            cui_col = col
            break
            
    if not cui_col:
        print("\n[ERROR] Could not find a CUI column in the CSV file.")
        print(f"Available columns: {list(df.columns)}")
        print("Please verify that your CSV contains the auxiliary data with UMLS Concept IDs.")
        return
        
    print(f"Found Concept ID column: '{cui_col}'")
    
    # 4. Get NLM API Key first (needed for both search and detail lookup)
    api_key = API_KEY.strip()
    if not api_key:
        print("\nTo query NLM UTS, you need a free API Key.")
        print("Sign up / retrieve key: https://uts-ws.nlm.nih.gov/uts/signup-login")
        api_key = input("Please paste your NLM UTS API Key: ").strip()
        
    if not api_key:
        print("[ERROR] API Key is required to run the lookup.")
        return

    # Clean CUI column values
    df[cui_col] = df[cui_col].astype(str).str.strip()
    df.loc[df[cui_col].str.lower() == 'nan', cui_col] = None
    df.loc[df[cui_col] == '', cui_col] = None
    
    missing_count = df[cui_col].isna().sum()
    
    # 5. Handle missing CUIs via local propagation and NLM API fallback search
    if missing_count > 0:
        print(f"\n[INFO] {missing_count} rows are missing a UMLS Concept ID (CUI).")
        choice = input("Would you like to search the NLM API to find CUIs for these using their Long Form (LF) terms? (y/n): ").strip().lower()
        if choice == 'y':
            # Step A: Local propagation by clean_norm_lf (propagate existing CUIs to other records with the exact same concept)
            print("\nPropagating existing CUIs locally to identical concepts (using LF fallback)...")
            
            # Helper to normalize terms consistently
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
            
            new_missing = df[cui_col].isna().sum()
            resolved_locally = missing_count - new_missing
            print(f"-> Resolved {resolved_locally} missing CUIs locally via synonym propagation.")
            
            # Step B: API lookup for remaining unique concepts
            if new_missing > 0:
                missing_mask = df[cui_col].isna()
                # Get the first available English LF for each unique missing clean_norm_lf
                norm_lf_to_search_term = df[missing_mask].groupby(norm_col)['LF'].first().dropna().to_dict()
                if "" in norm_lf_to_search_term:
                    del norm_lf_to_search_term[""]
                unique_terms = list(norm_lf_to_search_term.values())
                
                print(f"-> {new_missing} rows still missing a CUI.")
                print(f"-> Grouped into {len(unique_terms)} unique terms for NLM API search.")
                
                confirm = input(f"Proceed with API search for these {len(unique_terms)} unique terms? (y/n): ").strip().lower()
                if confirm == 'y':
                    print(f"\nStarting API search for {len(unique_terms)} terms...")
                    found_cuis = {}
                    
                    for idx, (norm_lf, search_term) in enumerate(norm_lf_to_search_term.items()):
                        # Spacing requests to prevent getting rate-limited (max 20 reqs/sec)
                        time.sleep(0.06)
                        
                        cui = get_cui_from_term(search_term, api_key)
                        if cui:
                            found_cuis[norm_lf] = cui
                            
                        # Display progress
                        progress = (idx + 1) / len(unique_terms) * 100
                        sys.stdout.write(f"\rProgress: [{idx + 1}/{len(unique_terms)}] {progress:.1f}% | Search: {search_term[:20]:<20} -> CUI: {cui or 'None':<10}")
                        sys.stdout.flush()
                    
                    print(f"\n\nAPI Search completed. Discovered {len(found_cuis)} new CUIs.")
                    
                    # Fill the newly discovered CUIs back into the DataFrame
                    df[cui_col] = df[cui_col].fillna(df[norm_col].map(found_cuis))
            
            # Drop the temporary column so it isn't saved to the output CSV
            df.drop(columns=[norm_col], inplace=True, errors='ignore')

    # Filter unique, non-empty CUIs to optimize API calls
    unique_cuis = df[cui_col].dropna().unique()
    unique_cuis = [str(c).strip() for c in unique_cuis if str(c).strip() and str(c).strip().lower() != 'nan']
    print(f"\nIdentified {len(unique_cuis)} unique CUIs to query for TUI details.")
    
    if len(unique_cuis) == 0:
        print("[ERROR] No valid CUIs found in the CUI column.")
        return
        
    # 6. Run lookup with progress tracking
    print("\nStarting batch detail lookup from NLM API...")
    cui_to_tui = {}
    cui_to_semantic = {}
    
    start_time = time.time()
    
    for idx, cui in enumerate(unique_cuis):
        # Spacing requests to prevent getting rate-limited (UTS standard is max 20 requests/sec)
        time.sleep(0.06) 
        
        tui, sem_name = get_tui_from_cui(cui, api_key)
        if tui:
            cui_to_tui[cui] = tui
            cui_to_semantic[cui] = sem_name
            
        # Display progress
        progress = (idx + 1) / len(unique_cuis) * 100
        sys.stdout.write(f"\rProgress: [{idx + 1}/{len(unique_cuis)}] {progress:.1f}% | CUI: {cui:<10} -> TUI: {tui or 'None':<5}")
        sys.stdout.flush()
        
    elapsed = time.time() - start_time
    print(f"\n\nLookup completed in {elapsed:.1f} seconds.")
    print(f"Successfully mapped {len(cui_to_tui)} of {len(unique_cuis)} Concept IDs.")
    
    # 6. Map results back to the original DataFrame
    df["TUI"] = df[cui_col].map(cui_to_tui)
    df["Semantic_Type"] = df[cui_col].map(cui_to_semantic)
    
    # 7. Save output file
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_with_tui{ext}"
    try:
        df.to_csv(output_file, sep='|', index=False)
        print("=" * 60)
        print(f"SUCCESS: Saved enriched file to '{output_file}'!")
        print("Columns added: 'TUI' (e.g. T047) and 'Semantic_Type' (e.g. Disease or Syndrome).")
        print("=" * 60)
    except Exception as e:
        print(f"[ERROR] Could not save output file: {e}")

if __name__ == "__main__":
    main()
