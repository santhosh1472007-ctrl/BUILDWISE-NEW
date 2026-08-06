"""Seed 05 — Motherboards."""

from models import db, Motherboard, Brand, CpuSocket, Chipset


def _get_brand(name):
    return Brand.query.filter_by(name=name).first()


def _get_socket(name):
    return CpuSocket.query.filter_by(name=name).first()


def _get_chipset(name):
    return Chipset.query.filter_by(name=name).first()


def _add(items):
    for item in items:
        if not Motherboard.query.filter_by(name=item["name"]).first():
            db.session.add(Motherboard(**item))
    db.session.flush()


def seed():
    am5 = _get_socket("AM5")
    am4 = _get_socket("AM4")
    lga1700 = _get_socket("LGA1700")
    lga1200 = _get_socket("LGA1200")
    lga1151 = _get_socket("LGA1151")

    x870e = _get_chipset("X870E")
    b650 = _get_chipset("B650")
    x570 = _get_chipset("X570")
    z790 = _get_chipset("Z790")
    b760 = _get_chipset("B760")
    z590 = _get_chipset("Z590")
    b365 = _get_chipset("B365")

    _add([
        dict(name="ASUS ROG Crosshair X870E Hero", brand_id=_get_brand("ASUS").id if _get_brand("ASUS") else None, socket_id=am5.id if am5 else None, chipset_id=x870e.id if x870e else None,
             form_factor="E-ATX", memory_type="DDR5", memory_slots=4, max_memory_gb=256, max_memory_speed_mhz=9200,
             pcie_x16_slots=2, pcie_x1_slots=2, m2_slots=5, m2_pcie_gen_slots="5,5,4,4,4", sata_ports=8,
             usb_c_rear_ports=2, wifi=True, wifi_standard="WiFi 7", bluetooth=True, bluetooth_version="5.4",
             vrm_phases=20, bios_flashback=True, msrp_usd=999),
        dict(name="MSI MAG X670E Tomahawk WiFi", brand_id=_get_brand("MSI").id if _get_brand("MSI") else None, socket_id=am5.id if am5 else None, chipset_id=_get_chipset("X670E").id if _get_chipset("X670E") else None,
             form_factor="ATX", memory_type="DDR5", memory_slots=4, max_memory_gb=128, max_memory_speed_mhz=6400,
             pcie_x16_slots=2, pcie_x1_slots=3, m2_slots=4, m2_pcie_gen_slots="5,4,4,4", sata_ports=6,
             usb_c_rear_ports=1, wifi=True, wifi_standard="WiFi 6E", bluetooth=True, bluetooth_version="5.3",
             vrm_phases=16, bios_flashback=False, msrp_usd=399),
        dict(name="Gigabyte B650 AORUS Elite AX", brand_id=_get_brand("Gigabyte").id if _get_brand("Gigabyte") else None, socket_id=am5.id if am5 else None, chipset_id=b650.id if b650 else None,
             form_factor="ATX", memory_type="DDR5", memory_slots=4, max_memory_gb=192, max_memory_speed_mhz=6400,
             pcie_x16_slots=2, pcie_x1_slots=2, m2_slots=3, m2_pcie_gen_slots="4,4,4", sata_ports=6,
             usb_c_rear_ports=1, wifi=True, wifi_standard="WiFi 6", bluetooth=True, bluetooth_version="5.2",
             vrm_phases=12, bios_flashback=False, msrp_usd=249),
        dict(name="ASRock B550 Steel Legend", brand_id=_get_brand("ASRock").id if _get_brand("ASRock") else None, socket_id=am4.id if am4 else None, chipset_id=x570.id if x570 else None,
             form_factor="ATX", memory_type="DDR4", memory_slots=4, max_memory_gb=128, max_memory_speed_mhz=5100,
             pcie_x16_slots=2, pcie_x1_slots=2, m2_slots=2, m2_pcie_gen_slots="4,4", sata_ports=6,
             usb_c_rear_ports=1, wifi=False, bluetooth=False,
             vrm_phases=10, bios_flashback=False, msrp_usd=189),
        dict(name="ASUS TUF Gaming Z790-Plus WiFi", brand_id=_get_brand("ASUS").id if _get_brand("ASUS") else None, socket_id=lga1700.id if lga1700 else None, chipset_id=z790.id if z790 else None,
             form_factor="ATX", memory_type="DDR5", memory_slots=4, max_memory_gb=128, max_memory_speed_mhz=7600,
             pcie_x16_slots=2, pcie_x1_slots=3, m2_slots=4, m2_pcie_gen_slots="4,4,4,4", sata_ports=6,
             usb_c_rear_ports=1, wifi=True, wifi_standard="WiFi 6", bluetooth=True, bluetooth_version="5.3",
             vrm_phases=14, bios_flashback=True, msrp_usd=279),
        dict(name="MSI PRO B760M-A WiFi", brand_id=_get_brand("MSI").id if _get_brand("MSI") else None, socket_id=lga1700.id if lga1700 else None, chipset_id=b760.id if b760 else None,
             form_factor="Micro-ATX", memory_type="DDR5", memory_slots=4, max_memory_gb=192, max_memory_speed_mhz=7200,
             pcie_x16_slots=1, pcie_x1_slots=2, m2_slots=2, m2_pcie_gen_slots="4,4", sata_ports=4,
             usb_c_rear_ports=1, wifi=True, wifi_standard="WiFi 6", bluetooth=True, bluetooth_version="5.3",
             vrm_phases=8, bios_flashback=False, msrp_usd=149),
        dict(name="Gigabyte Z590 AORUS Elite", brand_id=_get_brand("Gigabyte").id if _get_brand("Gigabyte") else None, socket_id=lga1200.id if lga1200 else None, chipset_id=z590.id if z590 else None,
             form_factor="ATX", memory_type="DDR4", memory_slots=4, max_memory_gb=128, max_memory_speed_mhz=5333,
             pcie_x16_slots=2, pcie_x1_slots=2, m2_slots=3, m2_pcie_gen_slots="4,4,3", sata_ports=6,
             usb_c_rear_ports=1, wifi=False, bluetooth=False,
             vrm_phases=12, bios_flashback=False, msrp_usd=199),
        dict(name="ASUS Prime H310M-E", brand_id=_get_brand("ASUS").id if _get_brand("ASUS") else None, socket_id=lga1151.id if lga1151 else None, chipset_id=b365.id if b365 else None,
             form_factor="Micro-ATX", memory_type="DDR4", memory_slots=2, max_memory_gb=64, max_memory_speed_mhz=2666,
             pcie_x16_slots=1, pcie_x1_slots=2, m2_slots=1, m2_pcie_gen_slots="3", sata_ports=4,
             usb_c_rear_ports=0, wifi=False, bluetooth=False,
             vrm_phases=4, bios_flashback=False, msrp_usd=79),
    ])
    db.session.commit()
