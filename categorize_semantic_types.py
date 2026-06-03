"""
Add Semantic_Category column to the enriched CSV output.

This script reads the enriched CSV, maps each TUI to a high-level
clinical domain category, and saves the result with the new column.
"""
import pandas as pd

# ===== TUI → Semantic Category Mapping =====
TUI_TO_CATEGORY = {
    # Chemicals & Biochemistry
    "T116": "Chemicals & Biochemistry",
    "T109": "Chemicals & Biochemistry",
    "T114": "Chemicals & Biochemistry",
    "T197": "Chemicals & Biochemistry",
    "T123": "Chemicals & Biochemistry",
    "T196": "Chemicals & Biochemistry",
    "T167": "Chemicals & Biochemistry",
    "T104": "Chemicals & Biochemistry",
    "T120": "Chemicals & Biochemistry",
    "T103": "Chemicals & Biochemistry",

    # Pharmacology & Therapeutics
    "T121": "Pharmacology & Therapeutics",
    "T200": "Pharmacology & Therapeutics",
    "T195": "Pharmacology & Therapeutics",
    "T125": "Pharmacology & Therapeutics",
    "T127": "Pharmacology & Therapeutics",
    "T131": "Pharmacology & Therapeutics",

    # Diseases & Clinical Findings
    "T047": "Diseases & Clinical Findings",
    "T033": "Diseases & Clinical Findings",
    "T191": "Diseases & Clinical Findings",
    "T046": "Diseases & Clinical Findings",
    "T048": "Diseases & Clinical Findings",
    "T184": "Diseases & Clinical Findings",
    "T037": "Diseases & Clinical Findings",
    "T049": "Diseases & Clinical Findings",
    "T019": "Diseases & Clinical Findings",
    "T190": "Diseases & Clinical Findings",
    "T020": "Diseases & Clinical Findings",
    "T050": "Diseases & Clinical Findings",
    "T034": "Diseases & Clinical Findings",

    # Procedures & Diagnostics
    "T059": "Procedures & Diagnostics",
    "T061": "Procedures & Diagnostics",
    "T060": "Procedures & Diagnostics",
    "T058": "Procedures & Diagnostics",
    "T063": "Procedures & Diagnostics",
    "T062": "Procedures & Diagnostics",
    "T130": "Procedures & Diagnostics",

    # Genetics & Molecular Biology
    "T028": "Genetics & Molecular Biology",
    "T087": "Genetics & Molecular Biology",
    "T086": "Genetics & Molecular Biology",
    "T085": "Genetics & Molecular Biology",
    "T045": "Genetics & Molecular Biology",

    # Anatomy & Body Structures
    "T023": "Anatomy & Body Structures",
    "T025": "Anatomy & Body Structures",
    "T026": "Anatomy & Body Structures",
    "T024": "Anatomy & Body Structures",
    "T029": "Anatomy & Body Structures",
    "T030": "Anatomy & Body Structures",
    "T031": "Anatomy & Body Structures",
    "T022": "Anatomy & Body Structures",
    "T018": "Anatomy & Body Structures",
    "T017": "Anatomy & Body Structures",
    "T021": "Anatomy & Body Structures",

    # Biological Functions & Processes
    "T044": "Biological Functions & Processes",
    "T043": "Biological Functions & Processes",
    "T042": "Biological Functions & Processes",
    "T039": "Biological Functions & Processes",
    "T040": "Biological Functions & Processes",
    "T038": "Biological Functions & Processes",
    "T070": "Biological Functions & Processes",
    "T067": "Biological Functions & Processes",
    "T041": "Biological Functions & Processes",

    # Organisms
    "T005": "Organisms",
    "T007": "Organisms",
    "T204": "Organisms",
    "T002": "Organisms",
    "T015": "Organisms",
    "T004": "Organisms",
    "T013": "Organisms",
    "T014": "Organisms",
    "T012": "Organisms",
    "T011": "Organisms",
    "T194": "Organisms",
    "T001": "Organisms",
    "T008": "Organisms",
    "T016": "Organisms",
    "T010": "Organisms",

    # Immunology
    "T129": "Immunology",
    "T192": "Immunology",
    "T126": "Immunology",

    # Devices & Materials
    "T074": "Devices & Materials",
    "T073": "Devices & Materials",
    "T122": "Devices & Materials",
    "T075": "Devices & Materials",
    "T203": "Devices & Materials",
    "T072": "Devices & Materials",

    # Concepts & Measurements
    "T081": "Concepts & Measurements",
    "T201": "Concepts & Measurements",
    "T080": "Concepts & Measurements",
    "T079": "Concepts & Measurements",
    "T082": "Concepts & Measurements",
    "T169": "Concepts & Measurements",
    "T032": "Concepts & Measurements",
    "T078": "Concepts & Measurements",
    "T077": "Concepts & Measurements",
    "T071": "Concepts & Measurements",
    "T102": "Concepts & Measurements",

    # Knowledge & Classification
    "T170": "Knowledge & Classification",
    "T185": "Knowledge & Classification",
    "T171": "Knowledge & Classification",

    # People & Organizations
    "T097": "People & Organizations",
    "T093": "People & Organizations",
    "T098": "People & Organizations",
    "T092": "People & Organizations",
    "T101": "People & Organizations",
    "T099": "People & Organizations",
    "T094": "People & Organizations",
    "T100": "People & Organizations",
    "T096": "People & Organizations",
    "T095": "People & Organizations",

    # Activities & Behaviors
    "T052": "Activities & Behaviors",
    "T056": "Activities & Behaviors",
    "T055": "Activities & Behaviors",
    "T054": "Activities & Behaviors",
    "T053": "Activities & Behaviors",
    "T057": "Activities & Behaviors",
    "T051": "Activities & Behaviors",

    # Regulation & Governance
    "T091": "Regulation & Governance",
    "T083": "Regulation & Governance",
    "T168": "Regulation & Governance",
    "T065": "Regulation & Governance",
    "T089": "Regulation & Governance",
    "T064": "Regulation & Governance",
    "T066": "Regulation & Governance",
    "T090": "Regulation & Governance",
    "T068": "Regulation & Governance",
    "T069": "Regulation & Governance",
}


def add_semantic_category(input_file, output_file=None):
    """Read enriched CSV, add Semantic_Category column, save."""
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file, sep='|', low_memory=False)
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

    # Map TUI → Category
    df["Semantic_Category"] = df["TUI"].map(TUI_TO_CATEGORY)

    mapped = df["Semantic_Category"].notna().sum()
    total_with_tui = df["TUI"].notna().sum()
    unmapped_tuis = df[df["TUI"].notna() & df["Semantic_Category"].isna()]["TUI"].unique()

    print(f"  Categorized: {mapped}/{total_with_tui} rows with TUI")
    if len(unmapped_tuis) > 0:
        print(f"  WARNING: {len(unmapped_tuis)} TUI(s) not mapped: {list(unmapped_tuis)}")

    # Category distribution
    print("\n  Category Distribution:")
    cat_counts = df["Semantic_Category"].dropna().value_counts()
    for cat, count in cat_counts.items():
        pct = count / mapped * 100
        print(f"    {count:>8}  ({pct:5.1f}%)  {cat}")

    # Save
    if output_file is None:
        output_file = input_file  # overwrite in-place
    df.to_csv(output_file, sep='|', index=False)
    print(f"\n  Saved to {output_file} ({len(df.columns)} columns)")
    return df


if __name__ == "__main__":
    input_path = r"c:\Users\ahmad\Downloads\Aberv\MetainventoryAuxiliary_Version1.0.0_with_tui.csv"
    add_semantic_category(input_path)
