# OMOP Clinical Abbreviations — Enriched Dataset

> **A comprehensive mapping of biomedical abbreviations to their UMLS Concept IDs (CUIs), Semantic Type Identifiers (TUIs), and clinical domain categories.**

---

## Overview

This project enriches the [OMOP Clinical Abbreviations Metainventory](https://lhncbc.nlm.nih.gov/LSG/Projects/lvg/current/docs/userDoc/tools/Ab.html) with structured knowledge from the **Unified Medical Language System (UMLS)** via the NLM UTS API. Each abbreviation–long form pair is mapped to its corresponding UMLS Concept, Semantic Type, and a high-level **Clinical Domain Category** for downstream analysis.

### Dataset at a Glance

| Metric | Value |
|--------|-------|
| **Total Records** | 405,543 |
| **Unique Abbreviations (SF)** | 104,053 |
| **Unique Long Forms (LF)** | 170,426 |
| **Records with UMLS CUI** | 351,445 (86.7%) |
| **Records with TUI / Semantic Type** | 350,787 (86.5%) |
| **Unique Semantic Types** | 126 |
| **Clinical Domain Categories** | 15 |

---

## Files

| File | Description |
|------|-------------|
| `MetainventoryAuxiliary_Version1.0.0.csv` | Original input file (18 columns, pipe-delimited) |
| `MetainventoryAuxiliary_Version1.0.0_with_tui.csv` | **Enriched output** with TUI, Semantic Type, and Category (21 columns, pipe-delimited) |
| `enrich_abbreviations.py` | CLI enrichment script (standalone, interactive) |
| `ui_server.py` | Web UI server for visual enrichment with real-time progress |
| `web/` | Frontend assets (HTML, CSS, JS) for the visual enrichment UI |
| `README.md` | This file |

---

## Output Schema

The enriched output file (`*_with_tui.csv`) is **pipe-delimited** (`|`) and contains **21 columns**:

### Original Columns (from Metainventory)

| # | Column | Type | Description |
|---|--------|------|-------------|
| 1 | `GroupID` | int | Unique group identifier linking all expansions of one abbreviation |
| 2 | `RecordID` | int | Unique record identifier |
| 3 | `SF` | string | **Short Form** — the abbreviation itself (e.g., `ACE`) |
| 4 | `SFUI` | string | Short Form Unique Identifier |
| 5 | `NormSF` | string | Normalized Short Form |
| 6 | `LF` | string | **Long Form** — the full expansion (e.g., `angiotensin-converting enzyme`) |
| 7 | `LFUI` | string | Long Form Unique Identifier |
| 8 | `NormLF` | string | Normalized Long Form |
| 9 | `Source` | string | Data source (e.g., `UMLS`, `ADAM`, `PubMed`, `Vanderbilt Discharge Sums`) |
| 10 | `SFEUI` | string | Short Form Entry Unique Identifier |
| 11 | `LFEUI` | string | Long Form Entry Unique Identifier |
| 12 | `Type` | string | Abbreviation type (e.g., `acronym`, `abbreviation`) |
| 13 | `PrefSF` | string | Preferred Short Form flag |
| 14 | `Score` | float | Scoring metric from the original inventory |
| 15 | `Count` | int | Occurrence count in source corpus |
| 16 | `Frequency` | float | Relative frequency |
| 17 | `UMLS.CUI` | string | UMLS Concept Unique Identifier (e.g., `C0001962`) |
| 18 | `Modified` | string | Modification flag |

### Enriched Columns (added by this pipeline)

| # | Column | Type | Description |
|---|--------|------|-------------|
| 19 | `TUI` | string | UMLS **Semantic Type Identifier** (e.g., `T116`, `T047`) |
| 20 | `Semantic_Type` | string | Human-readable semantic type name (e.g., `Amino Acid, Peptide, or Protein`) |
| 21 | `Semantic_Category` | string | **High-level clinical domain** grouping (see [Semantic Categories](#semantic-categories) below) |

---

## Semantic Categories

The 126 UMLS Semantic Types are grouped into **15 clinically meaningful domain categories** for easier analysis, filtering, and visualization:

### 🧬 Chemicals & Biochemistry

Substances, molecules, and chemical entities.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T116 | Amino Acid, Peptide, or Protein | 107,598 |
| T109 | Organic Chemical | 31,306 |
| T114 | Nucleic Acid, Nucleoside, or Nucleotide | 4,608 |
| T197 | Inorganic Chemical | 578 |
| T123 | Biologically Active Substance | 500 |
| T196 | Element, Ion, or Isotope | 241 |
| T167 | Substance | 214 |
| T104 | Chemical Viewed Structurally | 152 |
| T120 | Chemical Viewed Functionally | 45 |
| T103 | Chemical | 10 |
| **Subtotal** | | **145,252** |

### 🧪 Pharmacology & Therapeutics

Drugs, pharmaceuticals, and therapeutic agents.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T121 | Pharmacologic Substance | 5,188 |
| T200 | Clinical Drug | 474 |
| T195 | Antibiotic | 37 |
| T125 | Hormone | 54 |
| T127 | Vitamin | 3 |
| T131 | Hazardous or Poisonous Substance | 194 |
| **Subtotal** | | **5,950** |

### 🏥 Diseases & Clinical Findings

Diseases, syndromes, symptoms, and clinical observations.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T047 | Disease or Syndrome | 24,304 |
| T033 | Finding | 11,740 |
| T191 | Neoplastic Process | 6,507 |
| T046 | Pathologic Function | 1,877 |
| T048 | Mental or Behavioral Dysfunction | 1,087 |
| T184 | Sign or Symptom | 641 |
| T037 | Injury or Poisoning | 670 |
| T049 | Cell or Molecular Dysfunction | 496 |
| T019 | Congenital Abnormality | 1,230 |
| T190 | Anatomical Abnormality | 319 |
| T020 | Acquired Abnormality | 128 |
| T050 | Experimental Model of Disease | 130 |
| T034 | Laboratory or Test Result | 3,029 |
| **Subtotal** | | **52,158** |

### 🔬 Procedures & Diagnostics

Clinical, laboratory, and diagnostic procedures.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T059 | Laboratory Procedure | 13,992 |
| T061 | Therapeutic or Preventive Procedure | 10,131 |
| T060 | Diagnostic Procedure | 6,664 |
| T058 | Health Care Activity | 1,775 |
| T063 | Molecular Biology Research Technique | 1,097 |
| T062 | Research Activity | 530 |
| T130 | Indicator, Reagent, or Diagnostic Aid | 1,241 |
| **Subtotal** | | **35,430** |

### 🧬 Genetics & Molecular Biology

Genes, genomics, and molecular-level entities.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T028 | Gene or Genome | 34,925 |
| T087 | Amino Acid Sequence | 435 |
| T086 | Nucleotide Sequence | 240 |
| T085 | Molecular Sequence | 4 |
| T045 | Genetic Function | 901 |
| **Subtotal** | | **36,505** |

### 🏗️ Anatomy & Body Structures

Body parts, organs, tissues, cells, and spatial anatomy.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T023 | Body Part, Organ, or Organ Component | 6,308 |
| T025 | Cell | 3,978 |
| T026 | Cell Component | 2,078 |
| T024 | Tissue | 513 |
| T029 | Body Location or Region | 772 |
| T030 | Body Space or Junction | 448 |
| T031 | Body Substance | 502 |
| T022 | Body System | 287 |
| T018 | Embryonic Structure | 180 |
| T017 | Anatomical Structure | 22 |
| T021 | Fully Formed Anatomical Structure | 9 |
| **Subtotal** | | **15,097** |

### ⚙️ Biological Functions & Processes

Physiological, molecular, and cellular functions.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T044 | Molecular Function | 5,053 |
| T043 | Cell Function | 1,455 |
| T042 | Organ or Tissue Function | 1,292 |
| T039 | Physiologic Function | 503 |
| T040 | Organism Function | 789 |
| T038 | Biologic Function | 128 |
| T070 | Natural Phenomenon or Process | 610 |
| T067 | Phenomenon or Process | 222 |
| T041 | Mental Process | 401 |
| **Subtotal** | | **10,453** |

### 🦠 Organisms

Microorganisms and living organisms.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T005 | Virus | 4,925 |
| T007 | Bacterium | 2,915 |
| T204 | Eukaryote | 2,149 |
| T002 | Plant | 1,608 |
| T015 | Mammal | 1,296 |
| T004 | Fungus | 810 |
| T013 | Fish | 372 |
| T014 | Reptile | 232 |
| T012 | Bird | 217 |
| T011 | Amphibian | 115 |
| T194 | Archaeon | 54 |
| T001 | Organism | 55 |
| T008 | Animal | 28 |
| T016 | Human | 10 |
| T010 | Vertebrate | 1 |
| **Subtotal** | | **14,787** |

### 🧫 Immunology

Immune system components and factors.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T129 | Immunologic Factor | 1,043 |
| T192 | Receptor | 494 |
| T126 | Enzyme | 11 |
| **Subtotal** | | **1,548** |

### 🩺 Devices & Materials

Medical devices, instruments, and biomedical materials.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T074 | Medical Device | 2,858 |
| T073 | Manufactured Object | 1,416 |
| T122 | Biomedical or Dental Material | 555 |
| T075 | Research Device | 73 |
| T203 | Drug Delivery Device | 39 |
| T072 | Physical Object | 25 |
| **Subtotal** | | **4,966** |

### 📊 Concepts & Measurements

Quantitative values, clinical attributes, and abstract concepts.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T081 | Quantitative Concept | 5,264 |
| T201 | Clinical Attribute | 4,119 |
| T080 | Qualitative Concept | 1,733 |
| T079 | Temporal Concept | 1,628 |
| T082 | Spatial Concept | 1,620 |
| T169 | Functional Concept | 1,364 |
| T032 | Organism Attribute | 515 |
| T078 | Idea or Concept | 417 |
| T077 | Conceptual Entity | 179 |
| T071 | Entity | 8 |
| T102 | Group Attribute | 12 |
| **Subtotal** | | **16,859** |

### 📚 Knowledge & Classification

Publications, classification systems, and intellectual products.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T170 | Intellectual Product | 5,991 |
| T185 | Classification | 262 |
| T171 | Language | 404 |
| **Subtotal** | | **6,657** |

### 👥 People & Organizations

People, groups, professional roles, and organizations.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T097 | Professional or Occupational Group | 740 |
| T093 | Health Care Related Organization | 619 |
| T098 | Population Group | 400 |
| T092 | Organization | 204 |
| T101 | Patient or Disabled Group | 116 |
| T099 | Family Group | 96 |
| T094 | Professional Society | 90 |
| T100 | Age Group | 45 |
| T096 | Group | 35 |
| T095 | Self-help or Relief Organization | 28 |
| **Subtotal** | | **2,373** |

### 🎓 Activities & Behaviors

Daily activities, behaviors, and occupational activities.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T052 | Activity | 231 |
| T056 | Daily or Recreational Activity | 150 |
| T055 | Individual Behavior | 112 |
| T054 | Social Behavior | 111 |
| T053 | Behavior | 22 |
| T057 | Occupational Activity | 143 |
| T051 | Event | 9 |
| **Subtotal** | | **778** |

### 🏛️ Regulation & Governance

Laws, government activities, education, and professional disciplines.

| TUI | Semantic Type | Records |
|-----|---------------|---------|
| T091 | Biomedical Occupation or Discipline | 530 |
| T083 | Geographic Area | 513 |
| T168 | Food | 333 |
| T065 | Educational Activity | 179 |
| T089 | Regulation or Law | 105 |
| T064 | Governmental or Regulatory Activity | 96 |
| T066 | Machine Activity | 82 |
| T090 | Occupation or Discipline | 73 |
| T068 | Human-caused Phenomenon or Process | 58 |
| T069 | Environmental Effect of Humans | 5 |
| **Subtotal** | | **1,974** |

---

## Category Distribution Summary

| Category | Records | % of Typed |
|----------|---------|------------|
| 🧬 Chemicals & Biochemistry | 145,252 | 41.4% |
| 🏥 Diseases & Clinical Findings | 52,158 | 14.9% |
| 🧬 Genetics & Molecular Biology | 36,505 | 10.4% |
| 🔬 Procedures & Diagnostics | 35,430 | 10.1% |
| 📊 Concepts & Measurements | 16,859 | 4.8% |
| 🏗️ Anatomy & Body Structures | 15,097 | 4.3% |
| 🦠 Organisms | 14,787 | 4.2% |
| ⚙️ Biological Functions & Processes | 10,453 | 3.0% |
| 📚 Knowledge & Classification | 6,657 | 1.9% |
| 🧪 Pharmacology & Therapeutics | 5,950 | 1.7% |
| 🩺 Devices & Materials | 4,966 | 1.4% |
| 👥 People & Organizations | 2,373 | 0.7% |
| 🏛️ Regulation & Governance | 1,974 | 0.6% |
| 🧫 Immunology | 1,548 | 0.4% |
| 🎓 Activities & Behaviors | 778 | 0.2% |

---

## Enrichment Pipeline

### How CUIs Are Resolved

The pipeline uses a **7-stage matching strategy** to maximize coverage:

```
Stage 0: Text Normalization
  ├── 0a. Greek letter expansion (β → beta-)
  ├── 0b. Spelling corrections
  ├── 0c. Amino acid abbreviation expansion (Arg8 → arginine-8)
  ├── 0d. Chemical name normalizations
  ├── 0e. Stereochemistry prefix stripping
  ├── 0f. Isotope translation ((99m)Tc → Tc 99m)
  └── 0g. Procedure word stripping (scintigraphy, scan, etc.)

Stage 1: normalizedString search (3 cleaned variants)
Stage 2: words search (3 cleaned variants)
Stage 3: Concatenated search (remove spaces)
Stage 4: Original term search (raw input fallback)
Stage 5: Keyword extraction (words > 4 chars)
Stage 6: Short Form (abbreviation) fallback
Stage 7: Approximate search (fuzzy matching)
```

### How TUIs Are Retrieved

After CUI resolution, each unique CUI is queried via the NLM UTS `/content/current/CUI/{CUI}` endpoint to retrieve its primary Semantic Type (TUI + name).

### Performance

- **5 parallel workers** for concurrent API lookups
- **Rate limiter** at 20 requests/second with exponential backoff on 429 errors
- **Vectorized pre-computation** for DataFrame lookups (eliminates O(N²) bottleneck)

---

## How to Run

### Prerequisites

```bash
pip install requests pandas
```

You also need a free **NLM UTS API Key** — sign up at [https://uts.nlm.nih.gov/uts/signup-login](https://uts.nlm.nih.gov/uts/signup-login).

### Option 1: Web UI (Recommended)

```bash
python ui_server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser. The UI provides:
- Real-time progress tracking
- Live matched/unmatched concept tabs
- Statistics dashboard

### Option 2: CLI Script

```bash
python enrich_abbreviations.py
```

Follow the interactive prompts to select a file and start enrichment.

---

## Data Sources

The original abbreviation inventory aggregates data from:

- **UMLS** — Unified Medical Language System
- **ADAM** — Another Database of Abbreviations in Medicine
- **PubMed** — Biomedical literature
- **Vanderbilt Discharge Sums** — Clinical discharge summaries
- **Columbia** — Columbia University clinical notes
- **MEDSTRACT** — Biomedical text mining corpus

---

## License & Attribution

- **Metainventory Source**: Lexical Systems Group, National Library of Medicine (NLM)
- **UMLS API**: National Library of Medicine UTS (Terms of Service apply)
- **Semantic Type Hierarchy**: UMLS Semantic Network, NLM

> ⚠️ **Note**: Use of the NLM UTS API requires acceptance of the [UMLS License Agreement](https://www.nlm.nih.gov/databases/umls.html). Ensure compliance before redistributing enriched data.
