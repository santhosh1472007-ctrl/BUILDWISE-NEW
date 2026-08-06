"""Seed 08 — Power supplies."""

from models import db, PSU, Brand


def _brand(name):
    return Brand.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not PSU.query.filter_by(name=item["name"]).first():
            db.session.add(PSU(**item))
    db.session.flush()


def seed():
    _add([
        dict(name="Corsair RM750e", brand_id=_brand("Corsair").id if _brand("Corsair") else None, wattage=750, efficiency_rating="80+ Gold", modular_type="Fully Modular", form_factor="ATX", has_12vhpwr=False, has_12v2x6=False, pcie_8pin_count=4, eps_8pin_count=2, sata_connectors=8, fan_size_mm=140, fanless=False, msrp_usd=119),
        dict(name="be quiet! Pure Power 12 M 850W", brand_id=_brand("be quiet!").id if _brand("be quiet!") else None, wattage=850, efficiency_rating="80+ Gold", modular_type="Fully Modular", form_factor="ATX", has_12vhpwr=False, has_12v2x6=False, pcie_8pin_count=6, eps_8pin_count=2, sata_connectors=8, fan_size_mm=140, fanless=False, msrp_usd=139),
        dict(name="MSI MAG A850GL PCIe5", brand_id=_brand("MSI").id if _brand("MSI") else None, wattage=850, efficiency_rating="80+ Gold", modular_type="Fully Modular", form_factor="ATX", has_12vhpwr=True, has_12v2x6=True, pcie_8pin_count=6, eps_8pin_count=2, sata_connectors=8, fan_size_mm=140, fanless=False, msrp_usd=169),
        dict(name="EVGA 600 BQ", brand_id=_brand("EVGA").id if _brand("EVGA") else None, wattage=600, efficiency_rating="80+ Bronze", modular_type="Non-Modular", form_factor="ATX", has_12vhpwr=False, has_12v2x6=False, pcie_8pin_count=2, eps_8pin_count=1, sata_connectors=4, fan_size_mm=120, fanless=False, msrp_usd=79),
        dict(name="Corsair RM1000e", brand_id=_brand("Corsair").id if _brand("Corsair") else None, wattage=1000, efficiency_rating="80+ Gold", modular_type="Fully Modular", form_factor="ATX", has_12vhpwr=True, has_12v2x6=True, pcie_8pin_count=8, eps_8pin_count=2, sata_connectors=8, fan_size_mm=140, fanless=False, msrp_usd=199),
    ])
    db.session.commit()
