"""Seed 00 — Lookup tables: Brands, CPU Sockets, Chipsets."""

from models import db, Brand, CpuSocket, Chipset


def _get_or_create_brand(name, website=None):
    obj = Brand.query.filter_by(name=name).first()
    if not obj:
        obj = Brand(name=name, website=website)
        db.session.add(obj)
        db.session.flush()
    return obj


def _get_or_create_socket(name, cpu_brand, generation=None):
    obj = CpuSocket.query.filter_by(name=name).first()
    if not obj:
        obj = CpuSocket(name=name, cpu_brand=cpu_brand, generation=generation)
        db.session.add(obj)
        db.session.flush()
    return obj


def seed():
    # ── Brands ──────────────────────────────────────────────────────────
    brands = [
        # CPU / GPU
        ("AMD",           "https://www.amd.com"),
        ("Intel",         "https://www.intel.com"),
        ("NVIDIA",        "https://www.nvidia.com"),
        # Motherboard / AIB
        ("ASUS",          "https://www.asus.com"),
        ("MSI",           "https://www.msi.com"),
        ("Gigabyte",      "https://www.gigabyte.com"),
        ("ASRock",        "https://www.asrock.com"),
        # RAM
        ("Corsair",       "https://www.corsair.com"),
        ("G.Skill",       "https://www.gskill.com"),
        ("Kingston",      "https://www.kingston.com"),
        ("Crucial",       "https://www.crucial.com"),
        ("TeamGroup",     "https://www.teamgroupinc.com"),
        ("ADATA",         "https://www.adata.com"),
        ("Patriot",       "https://www.patriotmemory.com"),
        ("Silicon Power", "https://www.silicon-power.com"),
        ("Lexar",         "https://www.lexar.com"),
        ("GeIL",          "https://www.geil.com.tw"),
        ("PNY",           "https://www.pny.com"),
        # SSD
        ("Samsung",       "https://www.samsung.com"),
        ("Western Digital","https://www.westerndigital.com"),
        ("Seagate",       "https://www.seagate.com"),
        ("ADATA / XPG",   "https://www.adata.com"),
        ("Sabrent",       "https://www.sabrent.com"),
        ("Silicon Power", "https://www.silicon-power.com"),
        # PSU
        ("Cooler Master", "https://www.coolermaster.com"),
        ("Seasonic",      "https://www.seasonic.com"),
        ("EVGA",          "https://www.evga.com"),
        ("Thermaltake",   "https://www.thermaltake.com"),
        ("DeepCool",      "https://www.deepcool.com"),
        ("NZXT",          "https://www.nzxt.com"),
        ("be quiet!",     "https://www.bequiet.com"),
        ("SilverStone",   "https://www.silverstonetek.com"),
        ("Antec",         "https://www.antec.com"),
        ("FSP",           "https://www.fspgroupusa.com"),
        # Coolers
        ("Noctua",        "https://www.noctua.at"),
        ("Thermalright",  "https://www.thermalright.com"),
        ("Scythe",        "https://www.scythe-eu.com"),
        ("ID-COOLING",    "https://www.idcooling.com"),
        ("Arctic",        "https://www.arctic.de"),
        ("Lian Li",       "https://www.lian-li.com"),
        # Cases
        ("Fractal Design","https://www.fractal-design.com"),
        ("Phanteks",      "https://www.phanteks.com"),
        ("Montech",       "https://www.montechpc.com"),
        ("HYTE",          "https://www.hyte.com"),
        ("Sharkoon",      "https://www.sharkoon.com"),
        ("HYTE",          "https://www.hyte.com"),
    ]

    for name, website in brands:
        existing = Brand.query.filter_by(name=name).first()
        if not existing:
            db.session.add(Brand(name=name, website=website))

    db.session.flush()

    # ── CPU Sockets ──────────────────────────────────────────────────────
    sockets = [
        # AMD
        ("AM5",    "AMD",   "Zen 4 / Zen 5 (Ryzen 7000/8000/9000)"),
        ("AM4",    "AMD",   "Zen / Zen+ / Zen 2 / Zen 3 (Ryzen 1000-5000)"),
        # Intel
        ("LGA1851","Intel", "Arrow Lake / Core Ultra 200"),
        ("LGA1700","Intel", "Alder Lake / Raptor Lake (Gen 12/13/14)"),
        ("LGA1200","Intel", "Comet Lake / Rocket Lake (Gen 10/11)"),
        ("LGA1151","Intel", "Coffee Lake / Kaby Lake (Gen 7/8/9)"),
    ]

    socket_objs = {}
    for name, brand, gen in sockets:
        obj = _get_or_create_socket(name, brand, gen)
        socket_objs[name] = obj

    db.session.flush()

    # ── Chipsets ─────────────────────────────────────────────────────────
    # (name, socket_name, cpu_brand, overclocking, pcie_gen, max_ram_mhz, tier)
    chipsets = [
        # ── AMD AM5 ──
        ("X870E", "AM5", "AMD", True,  5, 9200, "enthusiast"),
        ("X870",  "AM5", "AMD", True,  5, 8600, "high"),
        ("B850",  "AM5", "AMD", True,  5, 8600, "mid"),
        ("B840",  "AM5", "AMD", False, 4, 6400, "entry"),
        ("X670E", "AM5", "AMD", True,  5, 6400, "enthusiast"),
        ("X670",  "AM5", "AMD", True,  5, 6000, "high"),
        ("B650E", "AM5", "AMD", True,  5, 6400, "mid"),
        ("B650",  "AM5", "AMD", True,  4, 6000, "mid"),
        ("A620",  "AM5", "AMD", False, 4, 5200, "entry"),
        # ── AMD AM4 ──
        ("X570",  "AM4", "AMD", True,  4, 5100, "enthusiast"),
        ("B550",  "AM4", "AMD", True,  4, 5100, "mid"),
        ("A520",  "AM4", "AMD", False, 3, 4266, "entry"),
        # ── Intel LGA1851 ──
        ("Z890",  "LGA1851", "Intel", True,  5, 9200, "enthusiast"),
        ("B860",  "LGA1851", "Intel", False, 5, 6400, "mid"),
        ("H810",  "LGA1851", "Intel", False, 4, 5600, "entry"),
        # ── Intel LGA1700 ──
        ("Z790",  "LGA1700", "Intel", True,  5, 8400, "enthusiast"),
        ("Z690",  "LGA1700", "Intel", True,  5, 7000, "enthusiast"),
        ("B760",  "LGA1700", "Intel", False, 4, 7200, "mid"),
        ("B660",  "LGA1700", "Intel", False, 4, 4800, "mid"),
        ("H770",  "LGA1700", "Intel", False, 4, 5600, "mid"),
        ("H670",  "LGA1700", "Intel", False, 4, 4800, "mid"),
        ("H610",  "LGA1700", "Intel", False, 4, 4800, "entry"),
        # ── Intel LGA1200 ──
        ("Z590",  "LGA1200", "Intel", True,  4, 5333, "enthusiast"),
        ("B560",  "LGA1200", "Intel", False, 4, 5000, "mid"),
        ("H570",  "LGA1200", "Intel", False, 4, 4800, "mid"),
        ("H510",  "LGA1200", "Intel", False, 3, 4600, "entry"),
        # ── Intel LGA1151 ──
        ("Z390",  "LGA1151", "Intel", True,  3, 4266, "enthusiast"),
        ("B365",  "LGA1151", "Intel", False, 3, 4000, "mid"),
        ("H370",  "LGA1151", "Intel", False, 3, 4000, "mid"),
        ("H310",  "LGA1151", "Intel", False, 3, 2666, "entry"),
    ]

    for (name, socket_name, cpu_brand, oc, pcie, ram_mhz, tier) in chipsets:
        existing = Chipset.query.filter_by(name=name).first()
        if not existing:
            s = socket_objs.get(socket_name)
            if s:
                db.session.add(Chipset(
                    name=name,
                    socket_id=s.id,
                    cpu_brand=cpu_brand,
                    overclocking_support=oc,
                    pcie_gen=pcie,
                    max_ram_speed_mhz=ram_mhz,
                    tier=tier,
                ))

    db.session.commit()
