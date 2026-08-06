"""Seed 07 — SSDs."""

from models import db, SSD, Brand


def _brand(name):
    return Brand.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not SSD.query.filter_by(name=item["name"]).first():
            db.session.add(SSD(**item))
    db.session.flush()


def seed():
    _add([
        dict(name="Samsung 990 Pro 2TB", brand_id=_brand("Samsung").id if _brand("Samsung") else None, interface="PCIe Gen4 x4", form_factor="M.2 2280", capacity_gb=2000, nand_type="TLC", seq_read_mbps=7450, seq_write_mbps=6900, tbw=1200, msrp_usd=229),
        dict(name="WD Black SN850X 1TB", brand_id=_brand("Western Digital").id if _brand("Western Digital") else None, interface="PCIe Gen4 x4", form_factor="M.2 2280", capacity_gb=1000, nand_type="TLC", seq_read_mbps=7300, seq_write_mbps=6600, tbw=600, msrp_usd=129),
        dict(name="Crucial T500 2TB", brand_id=_brand("Crucial").id if _brand("Crucial") else None, interface="PCIe Gen4 x4", form_factor="M.2 2280", capacity_gb=2000, nand_type="TLC", seq_read_mbps=7000, seq_write_mbps=5000, tbw=1200, msrp_usd=179),
        dict(name="Sabrent Rocket 4 Plus 2TB", brand_id=_brand("Sabrent").id if _brand("Sabrent") else None, interface="PCIe Gen4 x4", form_factor="M.2 2280", capacity_gb=2000, nand_type="TLC", seq_read_mbps=7000, seq_write_mbps=6600, tbw=1400, msrp_usd=199),
        dict(name="Kingston KC600 2TB", brand_id=_brand("Kingston").id if _brand("Kingston") else None, interface="SATA III", form_factor="2.5\"", capacity_gb=2000, nand_type="TLC", seq_read_mbps=550, seq_write_mbps=520, tbw=1200, msrp_usd=139),
        dict(name="Samsung 870 EVO 2TB", brand_id=_brand("Samsung").id if _brand("Samsung") else None, interface="SATA III", form_factor="2.5\"", capacity_gb=2000, nand_type="TLC", seq_read_mbps=560, seq_write_mbps=530, tbw=600, msrp_usd=149),
    ])
    db.session.commit()
