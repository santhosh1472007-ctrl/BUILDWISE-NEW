"""Seed 10 — PC cases."""

from models import db, PCCase, Brand


def _brand(name):
    return Brand.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not PCCase.query.filter_by(name=item["name"]).first():
            db.session.add(PCCase(**item))
    db.session.flush()


def seed():
    _add([
        dict(name="Fractal Pop Air", brand_id=_brand("Fractal Design").id if _brand("Fractal Design") else None, form_factor="ATX Mid Tower", supported_mobo_form_factors="Mini-ITX,Micro-ATX,ATX", gpu_clearance_mm=360, cpu_cooler_clearance_mm=165, max_radiator_front_mm=240, max_radiator_top_mm=240, max_radiator_rear_mm=120, psu_form_factor="ATX", drive_bays_35=2, drive_bays_25=2, side_panel_type="Mesh", color="Black", rgb_type="None", included_fans=3, msrp_usd=89),
        dict(name="NZXT H7 Flow", brand_id=_brand("NZXT").id if _brand("NZXT") else None, form_factor="ATX Mid Tower", supported_mobo_form_factors="Mini-ITX,Micro-ATX,ATX", gpu_clearance_mm=435, cpu_cooler_clearance_mm=166, max_radiator_front_mm=360, max_radiator_top_mm=280, max_radiator_rear_mm=120, psu_form_factor="ATX", drive_bays_35=2, drive_bays_25=2, side_panel_type="Tempered Glass", color="White", rgb_type="ARGB", included_fans=3, msrp_usd=159),
        dict(name="Phanteks Eclipse G360A", brand_id=_brand("Phanteks").id if _brand("Phanteks") else None, form_factor="ATX Mid Tower", supported_mobo_form_factors="Mini-ITX,Micro-ATX,ATX", gpu_clearance_mm=365, cpu_cooler_clearance_mm=165, max_radiator_front_mm=360, max_radiator_top_mm=240, max_radiator_rear_mm=120, psu_form_factor="ATX", drive_bays_35=2, drive_bays_25=2, side_panel_type="Mesh", color="Black", rgb_type="RGB", included_fans=3, msrp_usd=99),
        dict(name="Lian Li Lancool 205", brand_id=_brand("Lian Li").id if _brand("Lian Li") else None, form_factor="Micro-ATX", supported_mobo_form_factors="Mini-ITX,Micro-ATX", gpu_clearance_mm=340, cpu_cooler_clearance_mm=155, max_radiator_front_mm=240, max_radiator_top_mm=240, max_radiator_rear_mm=120, psu_form_factor="ATX", drive_bays_35=2, drive_bays_25=2, side_panel_type="Tempered Glass", color="Black", rgb_type="ARGB", included_fans=2, msrp_usd=109),
    ])
    db.session.commit()
