"""
BuildWise Seed Runner
=====================
Run this once to populate the hardware database from scratch.
Usage:
    python seed/run_seed.py

The script is idempotent: ON CONFLICT DO NOTHING guards prevent
duplicates on repeated runs.
"""

import sys
import os

# Allow running from the project root or from inside seed/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db

SEED_MODULES = [
    "seed.s00_lookup_tables",
    "seed.s01_amd_cpus",
    "seed.s02_intel_cpus",
    "seed.s03_amd_gpus",
    "seed.s04_nvidia_gpus",
    "seed.s05_motherboards",
    "seed.s06_ram",
    "seed.s07_ssds",
    "seed.s08_psus",
    "seed.s09_cpu_coolers",
    "seed.s10_cases",
    "seed.s11_case_fans",
]


def run():
    app = create_app()
    with app.app_context():
        db.create_all()
        for module_name in SEED_MODULES:
            print(f"  ▶  Seeding {module_name} ...", end=" ", flush=True)
            try:
                module = __import__(module_name, fromlist=["seed"])
                module.seed()
                print("✓")
            except Exception as exc:
                print(f"✗  ERROR: {exc}")
                raise
        print("\n✅  All seed data loaded successfully.")


if __name__ == "__main__":
    run()
