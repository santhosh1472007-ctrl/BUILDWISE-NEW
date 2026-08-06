"""Seed 11 — Case fans."""

from models import db, CaseFan, Brand


def _brand(name):
    return Brand.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not CaseFan.query.filter_by(name=item["name"]).first():
            db.session.add(CaseFan(**item))
    db.session.flush()


def seed():
    _add([
        dict(name="Noctua NF-P12 redux-1700 PWM", brand_id=_brand("Noctua").id if _brand("Noctua") else None, size_mm=120, bearing_type="SFD", connector_type="4-pin PWM", airflow_type="Static Pressure", rgb_type="None", max_rpm=1700, max_airflow_cfm=55.4, max_noise_dba=25.1, pack_count=1, msrp_usd=24),
        dict(name="Arctic P12 PWM PST", brand_id=_brand("Arctic").id if _brand("Arctic") else None, size_mm=120, bearing_type="Fluid Dynamic", connector_type="4-pin PWM", airflow_type="Static Pressure", rgb_type="None", max_rpm=1800, max_airflow_cfm=56.3, max_noise_dba=22.5, pack_count=1, msrp_usd=15),
        dict(name="be quiet! Pure Wings 3", brand_id=_brand("be quiet!").id if _brand("be quiet!") else None, size_mm=120, bearing_type="Fluid Dynamic", connector_type="4-pin PWM", airflow_type="Airflow", rgb_type="None", max_rpm=1500, max_airflow_cfm=48.8, max_noise_dba=20.5, pack_count=1, msrp_usd=14),
        dict(name="NZXT Aer RGB 2", brand_id=_brand("NZXT").id if _brand("NZXT") else None, size_mm=120, bearing_type="Fluid Dynamic", connector_type="4-pin PWM", airflow_type="Airflow", rgb_type="ARGB", max_rpm=1800, max_airflow_cfm=72.8, max_noise_dba=32.0, pack_count=1, msrp_usd=19),
    ])
    db.session.commit()
