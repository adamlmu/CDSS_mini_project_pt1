#!/usr/bin/env python

import os
import asyncio
import random
import pandas as pd
from faker import Faker
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from app.database import Base, SessionLocal
from app.models import Loinc
from app import crud, schemas

# Sync
sync_url    = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
sync_engine = create_engine(sync_url, future=True)
SyncSession = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=sync_engine)

# Grabs LOINC from CSV
def seed_loinc_from_csv():
    try:
        df = pd.read_csv(
            "data/L_TableCore.csv",
            usecols=["LOINC_NUM","LONG_COMMON_NAME"],
            dtype=str
        ).dropna(subset=["LOINC_NUM","LONG_COMMON_NAME"])
    except Exception as e:
        print(f"Skipping LOINC seed ({e})", flush=True)
        return

    with SyncSession() as db:
        count = db.query(Loinc).count()
        if count > 0:
            print(f"LOINC already seeded ({count} rows), skipping.", flush=True)
            return

    print(f"Seeding {len(df)} LOINC entries from CSV...", flush=True)
    with SyncSession() as db:
        for _, r in df.iterrows():
            db.merge(Loinc(
                loinc_num   = r["LOINC_NUM"],
                common_name = r["LONG_COMMON_NAME"]
            ))
        db.commit()
    print("Local LOINC seeded.\n", flush=True)

seed_loinc_from_csv()

# Date functions
DATE_IN  = "%d/%m/%Y %H:%M"
DATE_BD  = "%d/%m/%Y"
DATE_OUT = "%d/%m/%Y %H:%M"

def safe_int(prompt: str) -> int:
    while True:
        s = input(prompt)
        try:
            return int(s)
        except ValueError:
            print("Incorrect input – please enter a whole number.", flush=True)

def safe_float(prompt: str) -> float:
    while True:
        s = input(prompt)
        try:
            return float(s)
        except ValueError:
            print("Incorrect input – please enter a numeric value.", flush=True)

def safe_date(prompt: str) -> datetime.date:
    while True:
        s = input(prompt)
        try:
            return datetime.strptime(s, DATE_BD).date()
        except ValueError:
            print("Incorrect input – use format dd/mm/YYYY.", flush=True)

def safe_datetime(prompt: str, allow_now: bool=False) -> datetime:
    while True:
        s = input(prompt)
        if allow_now and s.strip().lower() == "now":
            return datetime.utcnow()
        try:
            return datetime.strptime(s, DATE_IN)
        except ValueError:
            print("Incorrect input – use format dd/mm/YYYY HH:MM or 'now'.", flush=True)

def fmt(dt: datetime) -> str:
    return dt.strftime(DATE_OUT) if dt else "None"

fake = Faker()
PROJECT_DB_PATH = "data/project_db.xlsx"

# CLI interface
def print_menu():
    print("\nCDSS Terminal Interface", flush=True)
    print("1. Add Patient", flush=True)
    print("2. Add Observation", flush=True)
    print("3. Show Observation History", flush=True)
    print("4. Retroactive Update Observation", flush=True)
    print("5. Delete Latest Observation", flush=True)
    print("6. Create 10 NEW Fake Patients + Seed Observations from Excel", flush=True)
    print("7. Exit", flush=True)

async def add_patient():
    print("\n== Add Patient ==", flush=True)
    first  = input("First name: ").strip()
    last   = input("Last name : ").strip()
    gender = input("Gender (M/F): ").strip().upper()
    bd     = safe_date("Birth date (dd/mm/YYYY): ")
    data   = schemas.PatientCreate(first_name=first, last_name=last, gender=gender, birth_date=bd)
    async with SessionLocal() as db:
        p = await crud.create_patient(db, data)
    print(f"Created patient ID={p.patient_id}", flush=True)

async def add_observation():
    print("\n== Add Observation ==", flush=True)
    pid        = safe_int("Patient ID: ")
    loinc      = input("LOINC Code: ").strip()
    val        = safe_float("Value: ")
    start      = safe_datetime("Start (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    end_input  = input("End (dd/mm/YYYY HH:MM or now, empty skip): ").strip()
    if end_input.lower() == "now":
        end = datetime.utcnow()
    elif not end_input:
        end = None
    else:
        end = safe_datetime("End (dd/mm/YYYY HH:MM): ")
    data = schemas.ObservationCreate(
        patient_id=pid, loinc_num=loinc,
        value_num=val, start=start, end=end
    )
    async with SessionLocal() as db:
        o = await crud.create_observation(db, data)
    print(f"Created observation ID={o.obs_id}", flush=True)

async def show_history():
    print("\n== Observation History ==", flush=True)
    pid   = safe_int("Patient ID: ")
    loinc = input("LOINC Code: ").strip()
    since = safe_datetime("Since (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    until = safe_datetime("Until (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    async with SessionLocal() as db:
        name = await crud.get_loinc_name(db, loinc) or "(no name)"
        hist = await crud.observations_history(db, pid, loinc, since, until)
    if not hist:
        print("No results.", flush=True)
        return
    print(f"\nLOINC: {loinc} – {name}", flush=True)
    for o in hist:
        print(
            f"ID={o.obs_id} value={o.value_num} "
            f"valid=({fmt(o.valid_start)},{fmt(o.valid_end)}) "
            f"txn=({fmt(o.txn_start)},{fmt(o.txn_end)})",
            flush=True
        )

async def retro_update():
    print("\n== Retroactive Update ==", flush=True)
    name      = input("Patient full name (First Last): ").strip()
    loinc     = input("LOINC Code: ").strip()
    measured  = safe_datetime("Measured at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    txn_at    = safe_datetime("Update at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    new_val   = safe_float("New value: ")
    async with SessionLocal() as db:
        changed = await crud.retroactive_update(db, name, loinc, measured, txn_at, new_val)
    if not changed:
        print("No matching observation.", flush=True)
    else:
        old, new = changed
        common   = (await crud.get_loinc_name(db, loinc)) or "(no name)"
        print(f"\nLOINC: {loinc} – {common}", flush=True)
        print(f"[old] ID={old.obs_id} value={old.value_num} txn_end={fmt(old.txn_end)}", flush=True)
        print(f"[new] ID={new.obs_id} value={new.value_num} txn_start={fmt(new.txn_start)}", flush=True)

async def retro_delete():
    print("\n== Retroactive Delete ==", flush=True)
    name      = input("Patient full name (First Last): ").strip()
    loinc     = input("LOINC Code: ").strip()
    delete_at = safe_datetime("Delete at (dd/mm/YYYY HH:MM or now): ", allow_now=True)
    meas_i    = input("Measured at (optional, dd/mm/YYYY HH:MM or now; empty): ").strip()
    if meas_i.lower() == "now":
        measured = datetime.utcnow()
    elif not meas_i:
        measured = None
    else:
        measured = safe_datetime("Measured at (dd/mm/YYYY HH:MM): ")
    async with SessionLocal() as db:
        deleted = await crud.retroactive_delete(db, name, loinc, delete_at, measured)
    if not deleted:
        print("No matching observation.", flush=True)
    else:
        o      = deleted[0]
        common = (await crud.get_loinc_name(db, loinc)) or "(no name)"
        print(f"\nLOINC: {loinc} – {common}", flush=True)
        print(f"Deleted ID={o.obs_id} value={o.value_num} txn_end={fmt(o.txn_end)}", flush=True)

# 5) Create Fake Patients + Observations
async def create_fake():
    print("\n== Fake Patients + Seed Observations ==", flush=True)

    if not os.path.exists(PROJECT_DB_PATH):
        print(f"File not found: '{PROJECT_DB_PATH}'", flush=True)
        return

    try:
        df = pd.read_excel(PROJECT_DB_PATH, engine="openpyxl")
    except Exception as e:
        print(f"Could not load '{PROJECT_DB_PATH}': {e}", flush=True)
        return

    # DEBUG
    print(f"DEBUG: loaded {len(df)} rows with columns: {df.columns.tolist()}", flush=True)

    tests = df.to_dict("records")

    created_patients     = []
    created_observations = []

    async with SessionLocal() as db:
        for gender in ("M", "F"):
            for _ in range(5):
                # 1) create patient
                pdata = schemas.PatientCreate(
                    first_name = (fake.first_name_male() if gender=="M" else fake.first_name_female()),
                    last_name  = fake.last_name(),
                    gender     = gender,
                    birth_date = fake.date_of_birth(minimum_age=20, maximum_age=80)
                )
                patient = await crud.create_patient(db, pdata)
                created_patients.append((
                    patient.patient_id,
                    patient.first_name,
                    patient.last_name,
                    patient.gender
                ))

                # 2) pick up to 3 random test rows
                for t in random.sample(tests, min(3, len(tests))):
                    # match your actual column names exactly
                    code = t.get("LOINC-NUM")
                    val  = t.get("Value")
                    dt   = t.get("Valid start time")

                    # 3) skip incomplete rows
                    if pd.isna(code) or pd.isna(val) or pd.isna(dt):
                        continue

                    # guard against non‑numeric 'Value'
                    try:
                        num = float(val)
                    except (ValueError, TypeError):
                        print(f"  ⚠️ Skipping non-numeric value {val!r}", flush=True)
                        continue

                    start = pd.to_datetime(dt)
                    odata = schemas.ObservationCreate(
                        patient_id = patient.patient_id,
                        loinc_num  = str(code),
                        value_num  = num,
                        start      = start,
                        end        = start + pd.Timedelta(minutes=1)
                    )
                    obs = await crud.create_observation(db, odata)
                    created_observations.append((
                        obs.obs_id,
                        obs.patient_id,
                        obs.loinc_num,
                        obs.value_num
                    ))

    # summary
    print("\nPatients created:", flush=True)
    for pid, fn, ln, g in created_patients:
        print(f"  • ID={pid}  Name={fn} {ln}  Gender={g}", flush=True)

    print("\nObservations created:", flush=True)
    for oid, pid, lo, val in created_observations:
        print(f"  • ObsID={oid}  PatientID={pid}  LOINC={lo}  Value={val}", flush=True)

async def main():
    while True:
        print_menu()
        choice = input("Choose: ").strip()
        if   choice == "1": await add_patient()
        elif choice == "2": await add_observation()
        elif choice == "3": await show_history()
        elif choice == "4": await retro_update()
        elif choice == "5": await retro_delete()
        elif choice == "6": await create_fake()
        elif choice == "7": break
        else:
            print("Invalid choice, please try again.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
