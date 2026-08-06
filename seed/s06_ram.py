"""Seed 06 — RAM kits."""

from models import db, RamKit, Brand


def _brand(name):
    return Brand.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not RamKit.query.filter_by(name=item["name"]).first():
            db.session.add(RamKit(**item))
    db.session.flush()


def seed():
    _add([
        dict(name="Corsair Vengeance DDR5-6400 32GB", brand_id=_brand("Corsair").id if _brand("Corsair") else None, memory_type="DDR5", speed_mhz=6400, capacity_gb=32, module_count=2, capacity_per_module_gb=16, latency_cl=32, voltage=1.35, rgb=True, form_factor="DIMM", msrp_usd=149),
        dict(name="G.Skill Trident Z5 DDR5-6000 32GB", brand_id=_brand("G.Skill").id if _brand("G.Skill") else None, memory_type="DDR5", speed_mhz=6000, capacity_gb=32, module_count=2, capacity_per_module_gb=16, latency_cl=30, voltage=1.35, rgb=True, form_factor="DIMM", msrp_usd=139),
        dict(name="Kingston Fury Beast DDR5-5600 32GB", brand_id=_brand("Kingston").id if _brand("Kingston") else None, memory_type="DDR5", speed_mhz=5600, capacity_gb=32, module_count=2, capacity_per_module_gb=16, latency_cl=36, voltage=1.25, rgb=False, form_factor="DIMM", msrp_usd=119),
        dict(name="TeamGroup T-Create Expert DDR5-6400 32GB", brand_id=_brand("TeamGroup").id if _brand("TeamGroup") else None, memory_type="DDR5", speed_mhz=6400, capacity_gb=32, module_count=2, capacity_per_module_gb=16, latency_cl=34, voltage=1.35, rgb=True, form_factor="DIMM", msrp_usd=129),
        dict(name="Crucial DDR4-3200 16GB", brand_id=_brand("Crucial").id if _brand("Crucial") else None, memory_type="DDR4", speed_mhz=3200, capacity_gb=16, module_count=2, capacity_per_module_gb=8, latency_cl=22, voltage=1.2, rgb=False, form_factor="DIMM", msrp_usd=49),
        dict(name="Corsair Vengeance LPX DDR4-3600 16GB", brand_id=_brand("Corsair").id if _brand("Corsair") else None, memory_type="DDR4", speed_mhz=3600, capacity_gb=16, module_count=2, capacity_per_module_gb=8, latency_cl=18, voltage=1.35, rgb=False, form_factor="DIMM", msrp_usd=69),
        dict(name="G.Skill Ripjaws V DDR4-3200 32GB", brand_id=_brand("G.Skill").id if _brand("G.Skill") else None, memory_type="DDR4", speed_mhz=3200, capacity_gb=32, module_count=2, capacity_per_module_gb=16, latency_cl=16, voltage=1.35, rgb=False, form_factor="DIMM", msrp_usd=89),
        dict(name="Kingston Fury Beast DDR4-3200 64GB", brand_id=_brand("Kingston").id if _brand("Kingston") else None, memory_type="DDR4", speed_mhz=3200, capacity_gb=64, module_count=4, capacity_per_module_gb=16, latency_cl=16, voltage=1.35, rgb=False, form_factor="DIMM", msrp_usd=189),
    ])
    db.session.commit()
