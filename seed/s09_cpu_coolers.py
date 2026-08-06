"""Seed 09 — CPU coolers."""

from models import db, CpuCooler, CoolerSocketSupport, Brand, CpuSocket


def _brand(name):
    return Brand.query.filter_by(name=name).first()


def _socket(name):
    return CpuSocket.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not CpuCooler.query.filter_by(name=item["name"]).first():
            db.session.add(CpuCooler(**item))
    db.session.flush()


def seed():
    am4 = _socket("AM4")
    am5 = _socket("AM5")
    lga1700 = _socket("LGA1700")
    lga1200 = _socket("LGA1200")
    lga1151 = _socket("LGA1151")

    _add([
        dict(name="Noctua NH-D15", brand_id=_brand("Noctua").id if _brand("Noctua") else None, cooler_type="Air", height_mm=165, tdp_rating_watts=250, fan_size_mm=140, fan_count=2, rgb=False, msrp_usd=129),
        dict(name="Thermalright Peerless Assassin 120 SE", brand_id=_brand("Thermalright").id if _brand("Thermalright") else None, cooler_type="Air", height_mm=155, tdp_rating_watts=210, fan_size_mm=120, fan_count=1, rgb=False, msrp_usd=49),
        dict(name="Arctic Freezer 36", brand_id=_brand("Arctic").id if _brand("Arctic") else None, cooler_type="Air", height_mm=157, tdp_rating_watts=210, fan_size_mm=120, fan_count=1, rgb=False, msrp_usd=54),
        dict(name="be quiet! Pure Rock 2", brand_id=_brand("be quiet!").id if _brand("be quiet!") else None, cooler_type="Air", height_mm=155, tdp_rating_watts=150, fan_size_mm=120, fan_count=1, rgb=False, msrp_usd=59),
        dict(name="NZXT Kraken X63", brand_id=_brand("NZXT").id if _brand("NZXT") else None, cooler_type="AIO", radiator_size_mm=280, tdp_rating_watts=250, fan_size_mm=140, fan_count=2, rgb=True, rgb_type="RGB", msrp_usd=169),
    ])

    for cooler_name, socket_names in {
        "Noctua NH-D15": ["AM4", "AM5", "LGA1700", "LGA1200", "LGA1151"],
        "Thermalright Peerless Assassin 120 SE": ["AM4", "AM5", "LGA1700", "LGA1200", "LGA1151"],
        "Arctic Freezer 36": ["AM4", "AM5", "LGA1700", "LGA1200", "LGA1151"],
        "be quiet! Pure Rock 2": ["AM4", "AM5", "LGA1700", "LGA1200", "LGA1151"],
        "NZXT Kraken X63": ["AM4", "AM5", "LGA1700", "LGA1200", "LGA1151"],
    }.items():
        cooler = CpuCooler.query.filter_by(name=cooler_name).first()
        if cooler:
            for socket_name in socket_names:
                socket = _socket(socket_name)
                if socket and not CoolerSocketSupport.query.filter_by(cooler_id=cooler.id, socket_id=socket.id).first():
                    db.session.add(CoolerSocketSupport(cooler_id=cooler.id, socket_id=socket.id))

    db.session.commit()
