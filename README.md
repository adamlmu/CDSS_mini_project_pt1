# CDSS_mini_project_pt1

A lightweight, **bitemporal clinical‑data warehouse** with an interactive Command‑Line Interface (CLI) demonstrating core Clinical Decision‑Support System (CDSS) capabilities required for the **“Temporal Reasoning in Medical IS” mini‑project – Part 1**.

It stores patients, laboratory observations (with full history), and a local copy of the LOINC dictionary; supports **history, retro‑update and retro‑delete** operations; and delivers CDSS functionality across all dimensions discussed in class.

---

## 1 How this repository satisfies the assignment

| Requirement (spec §) | Implementation |
|----------------------|----------------|
| At least **10 patients (5 M + 5 F) with multiple STATES** | `faker`‑driven seeder (`main ➜ option 6`) creates 10 demo patients with realistic gender balance and multi‑state vitals. |
| Full **LOINC concept dictionary** + return of *relevant rows only* | `app/L_TableCore.csv` loaded on first run; JOINs expose common names in every CLI query. |
| **2.1 History query**: for *patient × LOINC × [t1, t2]* | CLI option 3 – the query engine returns all rows where the VALID and TXN intervals intersect the requested window. |
| **2.2 Retro‑update** with audit trail | CLI option 4 – closes the current TXN interval and inserts a new row with the updated value. |
| **2.3 Retro‑delete** | CLI option 5 – sets `txn_end` on the chosen row; audit preserved. |
| `now` keyword / optional time | Input helpers default to *now* when HH:MM is omitted, or accept the literal `now`. |
| DSS **Dimensions** explanation | See § 5. |
| Architecture & User manual | This README. |

---

## 2 Project layout

```text
CDSS_mini_project_pt1/
├── environment.yml          # Conda definition (Python 3.11, SQLAlchemy 2, etc.)
├── main.py                   # Interactive terminal front‑end
├── data/                    # All mutable data lives outside the code package
│   ├── project_db.xlsx      # Example lab results for the demo seeder
│   └── L_TableCore.csv      # LOINC subset (code ↔ common name)
└── app/                     # Pure‑code Python package
    ├── __init__.py
    ├── config.py            # Reads .env → DATABASE_URL (SQLite fallback)
    ├── database.py          # Async SQLAlchemy engine & session factory
    ├── models.py            # ORM entities (Patient, Observation, Loinc)
    ├── schemas.py           # Pydantic DTOs for validation
    └── crud.py              # High‑level, bitemporal CRUD helpers

```

---

## 3 Installation - Clone & create the Conda environment

```bash
git clone https://github.com/itaysol/CDSS-Project.git
cd CDSS_mini_project_pt1
conda env create -f environment.yml
conda activate cdss_adam_itay         # name defined in the YAML
```

## 4 Running & using the CLI

```bash
python main.py
```

### 4.1 Menu overview

| Key | Operation | Example |
|-----|-----------|---------|
| 1  | Add patient | `1  →  “Alice Green”  →  F` |
| 2  | Add observation | `2 → patient id 1 → “1986‑10‑11 08:30” → “WBC” → 7800` |
| 3  | **Query history** | `3 → id 1 → “WBC” → 01/01/2020 → 31/12/2025` |
| 4  | **Retro‑update** | `4 → id 1 → “WBC” → 24/05/2016 10:00 → 8000` *(example in spec)* |
| 5  | **Retro‑delete** | `5 → id 2 → “PaCO2” → 17/05/2016` |
| 6  | Seed demo data | Generates 10 patients + vitals from `project_db.xlsx` |
| 7  | Exit |   |

#### Date/time shortcuts
* Omit the **time** part to default to `00:00`.
* Enter **`now`** in place of a full timestamp to reference the current time.

All input is validated by Pydantic; friendly error messages guide corrections.

---

## 5 CDSS dimension coverage

| CDSS dimension (lecture) | Implementation in this project |
|--------------------------|--------------------------------|
| **Temporal** reasoning | Bitemporal schema tracks both *clinical validity* and *database transaction* times. |
| **Knowledge‑base** vs **data‑driven** | Hybrid: medical codes (LOINC) act as structured knowledge; CRUD operates on raw data. |
| **Interactive** vs automatic | Fully **interactive CLI**; user triggers each decision step. |
| **Patient‑specific** vs population | Core queries are patient‑specific, but bulk export easily enables cohort analytics. |
| **Integrated** vs standalone | Designed as a plug‑in data service – switch RDBMS without code changes. |
| **Explanation / auditability** | Every change preserved via TXN intervals; history query exposes the audit trail. |

---

## 6 Data model details

### 6.1 `observations` – bitemporal fact

| Column | Type | Role |
|--------|------|------|
| `id` | PK | Surrogate |
| `patient_id` → `patients.id` | FK | Subject |
| `loinc_num` → `loinc.num` | FK | Lab code |
| `value` | Float | Measured result |
| `valid_start`, `valid_end` | DATETIME | **When the measurement applies** |
| `txn_start`, `txn_end` | DATETIME | **When the row existed in the DB** |

Updates never overwrite – they **close** the current TXN interval (`txn_end = now`)
and insert a fresh row.

### 6.2 Seed scripts

* **LOINC loader**: Inserts ~80 k rows on first run (fast CSV bulk copy).
* **Demo patients & states**: Under option 6.

## 7 Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `database is locked` | SQLite allows one writer – close other processes. |
| “No measurement found at this exact HH:MM” | Retro‑update/delete require an exact match, as per spec. |
| CLI hangs on first run | Large LOINC import – give it ~5 s. |
