"""
BuildWise — SQLAlchemy Models
=============================================================
Normalized hardware database for a production-quality PC
component selector (similar to PCPartPicker).

Tables
------
  User              — application users (pre-existing)
  Brand             — component manufacturer lookup
  CpuSocket         — CPU socket types (AM4, AM5, LGA1700, …)
  Chipset           — motherboard chipsets linked to sockets
  CPU               — desktop processors (AMD + Intel)
  GPU               — discrete graphics cards (AMD + NVIDIA)
  Motherboard       — desktop motherboards
  RamKit            — RAM kits (DDR4 / DDR5)
  SSD               — solid-state drives
  PSU               — power supply units
  CpuCooler         — air coolers + AIO liquid coolers
  CoolerSocketSupport — junction: which sockets a cooler supports
  PCCase            — PC cases
  CaseFan           — case / chassis fans

Design decisions
----------------
  • All component tables include `glb_model_path` and `image_path`
    (both nullable) so the 3D Builder can reference 3-D assets
    later without a schema change.
  • Pricing columns (msrp_usd, current_price_usd, retailer_url,
    price_last_updated) are present but nullable — the existing
    dynamic pricing system keeps working unchanged.
  • ON CONFLICT / UNIQUE constraints prevent duplicate records.
  • Indexes on the columns most queried in compatibility checks.
  • SQLite-compatible column types are used where possible.
    (ARRAY is not available in SQLite, so multi-value columns use
    TEXT with comma-separated values and a Python property.)
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
# USER  (pre-existing — kept for backward compatibility)
# ─────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"

    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),  unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


# ─────────────────────────────────────────────────────────────
# LOOKUP — BRANDS
# ─────────────────────────────────────────────────────────────

class Brand(db.Model):
    """Component manufacturer / brand."""
    __tablename__ = "brands"

    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(100), unique=True, nullable=False)
    website = db.Column(db.String(255))

    def to_dict(self):
        return {"id": self.id, "name": self.name, "website": self.website}

    def __repr__(self):
        return f"<Brand {self.name}>"


# ─────────────────────────────────────────────────────────────
# LOOKUP — CPU SOCKETS
# ─────────────────────────────────────────────────────────────

class CpuSocket(db.Model):
    """CPU socket type — AM4, AM5, LGA1700, LGA1851, …"""
    __tablename__ = "cpu_sockets"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(30), unique=True, nullable=False)
    cpu_brand  = db.Column(db.String(10), nullable=False)  # 'AMD' | 'Intel'
    generation = db.Column(db.String(50))                  # e.g. 'Zen 4 / AM5'

    # Relationships
    chipsets = db.relationship("Chipset", back_populates="socket", lazy="dynamic")
    cpus     = db.relationship("CPU",     back_populates="socket", lazy="dynamic")
    mobos    = db.relationship("Motherboard", back_populates="socket", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "cpu_brand": self.cpu_brand}

    def __repr__(self):
        return f"<CpuSocket {self.name}>"


# ─────────────────────────────────────────────────────────────
# LOOKUP — CHIPSETS
# ─────────────────────────────────────────────────────────────

class Chipset(db.Model):
    """Motherboard chipset — X870E, B650, Z790, …"""
    __tablename__ = "chipsets"
    __table_args__ = (
        db.Index("ix_chipsets_socket_id", "socket_id"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(30), unique=True, nullable=False)
    socket_id            = db.Column(db.Integer, db.ForeignKey("cpu_sockets.id"), nullable=False)
    cpu_brand            = db.Column(db.String(10), nullable=False)  # 'AMD' | 'Intel'
    overclocking_support = db.Column(db.Boolean, default=False)
    pcie_gen             = db.Column(db.SmallInteger)                # 4 | 5
    max_ram_speed_mhz    = db.Column(db.Integer)                     # e.g. 8000
    tier                 = db.Column(db.String(20))                  # 'enthusiast'|'mid'|'entry'

    socket = db.relationship("CpuSocket", back_populates="chipsets")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "socket_id": self.socket_id,
            "cpu_brand": self.cpu_brand,
            "overclocking_support": self.overclocking_support,
            "pcie_gen": self.pcie_gen,
            "max_ram_speed_mhz": self.max_ram_speed_mhz,
        }

    def __repr__(self):
        return f"<Chipset {self.name}>"


# ─────────────────────────────────────────────────────────────
# CPU
# ─────────────────────────────────────────────────────────────

class CPU(db.Model):
    """Desktop processor — AMD Ryzen + Intel Core."""
    __tablename__ = "cpus"
    __table_args__ = (
        db.Index("ix_cpus_socket_id",   "socket_id"),
        db.Index("ix_cpus_brand",        "brand"),
        db.Index("ix_cpus_memory_type",  "memory_type"),
    )

    id                       = db.Column(db.Integer, primary_key=True)
    name                     = db.Column(db.String(150), unique=True, nullable=False)
    brand                    = db.Column(db.String(10),  nullable=False)  # 'AMD'|'Intel'
    socket_id                = db.Column(db.Integer, db.ForeignKey("cpu_sockets.id"), nullable=False)
    architecture             = db.Column(db.String(60))   # 'Zen 4'|'Raptor Lake'|…
    series                   = db.Column(db.String(60))   # 'Ryzen 9000'|'Core i9-14000'|…

    # Core specs
    cores                    = db.Column(db.SmallInteger, nullable=False)
    threads                  = db.Column(db.SmallInteger, nullable=False)
    base_clock_ghz           = db.Column(db.Numeric(4, 2), nullable=False)
    boost_clock_ghz          = db.Column(db.Numeric(4, 2))
    tdp_watts                = db.Column(db.SmallInteger, nullable=False)
    max_tdp_watts            = db.Column(db.SmallInteger)  # PL2 / PPT ceiling

    # Memory
    memory_type              = db.Column(db.String(10), nullable=False)  # 'DDR4'|'DDR5'|'DDR4/DDR5'
    max_memory_speed_mhz     = db.Column(db.Integer)       # official JEDEC max
    memory_channels          = db.Column(db.SmallInteger, default=2)

    # Expansion
    pcie_gen                 = db.Column(db.SmallInteger)  # PCIe gen from CPU (4|5)

    # Integrated graphics
    integrated_graphics      = db.Column(db.Boolean, default=False)
    igpu_model               = db.Column(db.String(80))
    igpu_cores               = db.Column(db.SmallInteger)

    # Misc
    cooler_included          = db.Column(db.String(80))    # 'Wraith Stealth'|'Not Included'|…
    has_unlocked_multiplier  = db.Column(db.Boolean, default=False)  # overclockable
    lithography_nm           = db.Column(db.SmallInteger)  # process node nm

    # 3D Builder assets
    glb_model_path           = db.Column(db.String(255))
    image_path               = db.Column(db.String(255))

    # Pricing (optional — dynamic system still works)
    msrp_usd                 = db.Column(db.Numeric(8, 2))
    current_price_usd        = db.Column(db.Numeric(8, 2))
    retailer_url             = db.Column(db.String(512))
    price_last_updated       = db.Column(db.DateTime(timezone=True))

    created_at               = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at               = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    socket = db.relationship("CpuSocket", back_populates="cpus")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "socket": self.socket.name if self.socket else None,
            "socket_id": self.socket_id,
            "architecture": self.architecture,
            "series": self.series,
            "cores": self.cores,
            "threads": self.threads,
            "base_clock_ghz": float(self.base_clock_ghz) if self.base_clock_ghz else None,
            "boost_clock_ghz": float(self.boost_clock_ghz) if self.boost_clock_ghz else None,
            "tdp_watts": self.tdp_watts,
            "max_tdp_watts": self.max_tdp_watts,
            "memory_type": self.memory_type,
            "max_memory_speed_mhz": self.max_memory_speed_mhz,
            "memory_channels": self.memory_channels,
            "pcie_gen": self.pcie_gen,
            "integrated_graphics": self.integrated_graphics,
            "igpu_model": self.igpu_model,
            "igpu_cores": self.igpu_cores,
            "cooler_included": self.cooler_included,
            "has_unlocked_multiplier": self.has_unlocked_multiplier,
            "lithography_nm": self.lithography_nm,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<CPU {self.name}>"


# ─────────────────────────────────────────────────────────────
# GPU
# ─────────────────────────────────────────────────────────────

class GPU(db.Model):
    """Discrete graphics card — AMD Radeon + NVIDIA GeForce."""
    __tablename__ = "gpus"
    __table_args__ = (
        db.Index("ix_gpus_brand",    "brand"),
        db.Index("ix_gpus_vram_gb",  "vram_gb"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(150), unique=True, nullable=False)
    brand                = db.Column(db.String(10),  nullable=False)  # 'AMD'|'NVIDIA'
    architecture         = db.Column(db.String(60))   # 'RDNA4'|'Blackwell'|…
    series               = db.Column(db.String(60))   # 'RX 9000'|'RTX 50'|…

    # Memory
    vram_gb              = db.Column(db.SmallInteger, nullable=False)
    vram_type            = db.Column(db.String(10))   # 'GDDR6'|'GDDR6X'|'GDDR7'
    bus_width_bits       = db.Column(db.SmallInteger) # 128|192|256|384

    # Performance
    base_clock_mhz       = db.Column(db.Integer)
    boost_clock_mhz      = db.Column(db.Integer)
    game_clock_mhz       = db.Column(db.Integer)      # AMD Game Clock
    tflops_fp32          = db.Column(db.Numeric(6, 2)) # approximate FP32 TFLOPS

    # Architecture-specific
    compute_units        = db.Column(db.SmallInteger)  # AMD: CUs
    shaders              = db.Column(db.Integer)       # AMD: SPs / NVIDIA: CUDA cores
    rt_cores             = db.Column(db.SmallInteger)  # NVIDIA RT cores
    tensor_cores         = db.Column(db.SmallInteger)  # NVIDIA Tensor cores
    ray_accelerators     = db.Column(db.SmallInteger)  # AMD Ray Accelerators
    ai_accelerators      = db.Column(db.SmallInteger)  # AMD AI Accelerators (RDNA4+)
    infinity_cache_mb    = db.Column(db.SmallInteger)  # AMD Infinity Cache

    # Power
    tdp_watts            = db.Column(db.SmallInteger, nullable=False)
    min_psu_watts        = db.Column(db.SmallInteger) # recommended minimum PSU
    # Power connectors as comma-separated: '8pin,8pin' | '16pin' | '6+2pin,6+2pin'
    power_connectors     = db.Column(db.String(100))

    # Physical
    card_length_mm       = db.Column(db.SmallInteger) # critical for case compatibility
    card_height_mm       = db.Column(db.SmallInteger)
    card_slots           = db.Column(db.Numeric(3, 1)) # 2.0 | 2.5 | 3.0 slot

    # PCIe
    pcie_interface       = db.Column(db.String(20))   # 'PCIe 4.0 x16' | 'PCIe 5.0 x16'

    # Feature flags
    ray_tracing          = db.Column(db.Boolean, default=True)
    dlss_version         = db.Column(db.String(10))   # '3.5'|'4'|None
    fsr_version          = db.Column(db.String(10))   # '3.1'|'4'|None
    has_12vhpwr          = db.Column(db.Boolean, default=False)

    # Display outputs as comma-separated: 'HDMI 2.1,DP 2.1,DP 2.1,DP 2.1'
    display_outputs      = db.Column(db.String(150))

    # 3D Builder assets
    glb_model_path       = db.Column(db.String(255))
    image_path           = db.Column(db.String(255))

    # Pricing
    msrp_usd             = db.Column(db.Numeric(8, 2))
    current_price_usd    = db.Column(db.Numeric(8, 2))
    retailer_url         = db.Column(db.String(512))
    price_last_updated   = db.Column(db.DateTime(timezone=True))

    created_at           = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at           = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    @property
    def power_connectors_list(self):
        if self.power_connectors:
            return [c.strip() for c in self.power_connectors.split(",")]
        return []

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "architecture": self.architecture,
            "series": self.series,
            "vram_gb": self.vram_gb,
            "vram_type": self.vram_type,
            "bus_width_bits": self.bus_width_bits,
            "boost_clock_mhz": self.boost_clock_mhz,
            "game_clock_mhz": self.game_clock_mhz,
            "tflops_fp32": float(self.tflops_fp32) if self.tflops_fp32 else None,
            "shaders": self.shaders,
            "compute_units": self.compute_units,
            "infinity_cache_mb": self.infinity_cache_mb,
            "tdp_watts": self.tdp_watts,
            "min_psu_watts": self.min_psu_watts,
            "power_connectors": self.power_connectors,
            "card_length_mm": self.card_length_mm,
            "card_slots": float(self.card_slots) if self.card_slots else None,
            "pcie_interface": self.pcie_interface,
            "ray_tracing": self.ray_tracing,
            "dlss_version": self.dlss_version,
            "fsr_version": self.fsr_version,
            "has_12vhpwr": self.has_12vhpwr,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<GPU {self.name}>"


# ─────────────────────────────────────────────────────────────
# MOTHERBOARD
# ─────────────────────────────────────────────────────────────

class Motherboard(db.Model):
    """Desktop motherboard."""
    __tablename__ = "motherboards"
    __table_args__ = (
        db.Index("ix_mobos_socket_id",   "socket_id"),
        db.Index("ix_mobos_chipset_id",  "chipset_id"),
        db.Index("ix_mobos_form_factor", "form_factor"),
        db.Index("ix_mobos_memory_type", "memory_type"),
    )

    id                      = db.Column(db.Integer, primary_key=True)
    name                    = db.Column(db.String(200), unique=True, nullable=False)
    brand_id                = db.Column(db.Integer, db.ForeignKey("brands.id"))
    socket_id               = db.Column(db.Integer, db.ForeignKey("cpu_sockets.id"), nullable=False)
    chipset_id              = db.Column(db.Integer, db.ForeignKey("chipsets.id"),    nullable=False)

    # Form factor: 'Mini-ITX' | 'Micro-ATX' | 'ATX' | 'E-ATX' | 'SSI-EEB'
    form_factor             = db.Column(db.String(20), nullable=False)

    # Memory
    memory_type             = db.Column(db.String(10), nullable=False)  # 'DDR4'|'DDR5'|'DDR4/DDR5'
    memory_slots            = db.Column(db.SmallInteger, nullable=False)
    max_memory_gb           = db.Column(db.SmallInteger)
    max_memory_speed_mhz    = db.Column(db.Integer)

    # Expansion
    pcie_x16_slots          = db.Column(db.SmallInteger, default=1)
    pcie_x1_slots           = db.Column(db.SmallInteger, default=0)
    m2_slots                = db.Column(db.SmallInteger, default=0)
    # M.2 PCIe generation as comma-separated per slot: '5,4,4' (3 slots, gen5+gen4+gen4)
    m2_pcie_gen_slots       = db.Column(db.String(30))
    sata_ports              = db.Column(db.SmallInteger, default=4)

    # Connectivity
    usb_c_rear_ports        = db.Column(db.SmallInteger, default=0)
    wifi                    = db.Column(db.Boolean, default=False)
    wifi_standard           = db.Column(db.String(20))  # 'WiFi 6'|'WiFi 6E'|'WiFi 7'
    bluetooth               = db.Column(db.Boolean, default=False)
    bluetooth_version       = db.Column(db.String(10))  # '5.2'|'5.3'|…

    # Power delivery
    vrm_phases              = db.Column(db.SmallInteger)
    bios_flashback          = db.Column(db.Boolean, default=False)

    # 3D Builder assets
    glb_model_path          = db.Column(db.String(255))
    image_path              = db.Column(db.String(255))

    # Pricing
    msrp_usd                = db.Column(db.Numeric(8, 2))
    current_price_usd       = db.Column(db.Numeric(8, 2))
    retailer_url            = db.Column(db.String(512))
    price_last_updated      = db.Column(db.DateTime(timezone=True))

    created_at              = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at              = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    brand   = db.relationship("Brand")
    socket  = db.relationship("CpuSocket", back_populates="mobos")
    chipset = db.relationship("Chipset")

    # Form factor hierarchy for case compatibility checks
    _FORM_FACTOR_RANK = {
        "Mini-ITX": 1, "Micro-ATX": 2, "ATX": 3, "E-ATX": 4, "SSI-EEB": 5
    }

    @property
    def form_factor_rank(self):
        return self._FORM_FACTOR_RANK.get(self.form_factor, 0)

    @property
    def m2_max_pcie_gen(self):
        """Return the highest PCIe gen supported by any M.2 slot."""
        if not self.m2_pcie_gen_slots:
            return 0
        try:
            return max(int(g.strip()) for g in self.m2_pcie_gen_slots.split(",") if g.strip())
        except ValueError:
            return 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "socket": self.socket.name if self.socket else None,
            "socket_id": self.socket_id,
            "chipset": self.chipset.name if self.chipset else None,
            "chipset_id": self.chipset_id,
            "form_factor": self.form_factor,
            "memory_type": self.memory_type,
            "memory_slots": self.memory_slots,
            "max_memory_gb": self.max_memory_gb,
            "max_memory_speed_mhz": self.max_memory_speed_mhz,
            "pcie_x16_slots": self.pcie_x16_slots,
            "m2_slots": self.m2_slots,
            "m2_pcie_gen_slots": self.m2_pcie_gen_slots,
            "sata_ports": self.sata_ports,
            "wifi": self.wifi,
            "wifi_standard": self.wifi_standard,
            "bluetooth": self.bluetooth,
            "vrm_phases": self.vrm_phases,
            "bios_flashback": self.bios_flashback,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<Motherboard {self.name}>"


# ─────────────────────────────────────────────────────────────
# RAM KIT
# ─────────────────────────────────────────────────────────────

class RamKit(db.Model):
    """RAM kit — brand, speed, capacity, generation."""
    __tablename__ = "ram_kits"
    __table_args__ = (
        db.Index("ix_ram_memory_type", "memory_type"),
        db.Index("ix_ram_speed_mhz",   "speed_mhz"),
    )

    id                     = db.Column(db.Integer, primary_key=True)
    name                   = db.Column(db.String(200), unique=True, nullable=False)
    brand_id               = db.Column(db.Integer, db.ForeignKey("brands.id"))
    memory_type            = db.Column(db.String(10), nullable=False)   # 'DDR4'|'DDR5'
    speed_mhz              = db.Column(db.Integer,    nullable=False)
    capacity_gb            = db.Column(db.SmallInteger, nullable=False)
    module_count           = db.Column(db.SmallInteger, nullable=False)  # 1|2|4
    capacity_per_module_gb = db.Column(db.SmallInteger)
    latency_cl             = db.Column(db.SmallInteger)  # CL timing
    voltage                = db.Column(db.Numeric(4, 3)) # e.g. 1.350 V
    rgb                    = db.Column(db.Boolean, default=False)
    form_factor            = db.Column(db.String(10), default="DIMM")  # 'DIMM'|'SO-DIMM'

    # 3D Builder assets
    glb_model_path         = db.Column(db.String(255))
    image_path             = db.Column(db.String(255))

    # Pricing
    msrp_usd               = db.Column(db.Numeric(8, 2))
    current_price_usd      = db.Column(db.Numeric(8, 2))
    retailer_url           = db.Column(db.String(512))
    price_last_updated     = db.Column(db.DateTime(timezone=True))

    created_at             = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at             = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    brand = db.relationship("Brand")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "memory_type": self.memory_type,
            "speed_mhz": self.speed_mhz,
            "capacity_gb": self.capacity_gb,
            "module_count": self.module_count,
            "capacity_per_module_gb": self.capacity_per_module_gb,
            "latency_cl": self.latency_cl,
            "voltage": float(self.voltage) if self.voltage else None,
            "rgb": self.rgb,
            "form_factor": self.form_factor,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<RamKit {self.name}>"


# ─────────────────────────────────────────────────────────────
# SSD
# ─────────────────────────────────────────────────────────────

class SSD(db.Model):
    """Solid-state drive — SATA and NVMe."""
    __tablename__ = "ssds"
    __table_args__ = (
        db.Index("ix_ssd_interface",   "interface"),
        db.Index("ix_ssd_form_factor", "form_factor"),
        db.Index("ix_ssd_capacity_gb", "capacity_gb"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(200), unique=True, nullable=False)
    brand_id             = db.Column(db.Integer, db.ForeignKey("brands.id"))

    # 'SATA III' | 'PCIe Gen3 x4' | 'PCIe Gen4 x4' | 'PCIe Gen5 x4'
    interface            = db.Column(db.String(30), nullable=False)
    # '2.5"' | 'M.2 2230' | 'M.2 2242' | 'M.2 2280' | 'M.2 22110'
    form_factor          = db.Column(db.String(20), nullable=False)

    capacity_gb          = db.Column(db.Integer,    nullable=False)
    nand_type            = db.Column(db.String(10)) # 'TLC'|'QLC'|'MLC'|'SLC'
    seq_read_mbps        = db.Column(db.Integer)
    seq_write_mbps       = db.Column(db.Integer)
    tbw                  = db.Column(db.Integer)    # Terabytes Written endurance

    # 3D Builder assets
    glb_model_path       = db.Column(db.String(255))
    image_path           = db.Column(db.String(255))

    # Pricing
    msrp_usd             = db.Column(db.Numeric(8, 2))
    current_price_usd    = db.Column(db.Numeric(8, 2))
    retailer_url         = db.Column(db.String(512))
    price_last_updated   = db.Column(db.DateTime(timezone=True))

    created_at           = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at           = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    brand = db.relationship("Brand")

    @property
    def pcie_gen(self):
        """Return PCIe generation integer, or None for SATA."""
        if "Gen5" in self.interface:
            return 5
        if "Gen4" in self.interface:
            return 4
        if "Gen3" in self.interface:
            return 3
        return None  # SATA

    @property
    def is_m2(self):
        return self.form_factor.startswith("M.2")

    @property
    def is_sata(self):
        return "SATA" in self.interface

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "interface": self.interface,
            "form_factor": self.form_factor,
            "capacity_gb": self.capacity_gb,
            "nand_type": self.nand_type,
            "seq_read_mbps": self.seq_read_mbps,
            "seq_write_mbps": self.seq_write_mbps,
            "pcie_gen": self.pcie_gen,
            "is_m2": self.is_m2,
            "is_sata": self.is_sata,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<SSD {self.name}>"


# ─────────────────────────────────────────────────────────────
# PSU
# ─────────────────────────────────────────────────────────────

class PSU(db.Model):
    """Power supply unit."""
    __tablename__ = "psus"
    __table_args__ = (
        db.Index("ix_psu_wattage",    "wattage"),
        db.Index("ix_psu_efficiency", "efficiency_rating"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(200), unique=True, nullable=False)
    brand_id             = db.Column(db.Integer, db.ForeignKey("brands.id"))

    wattage              = db.Column(db.SmallInteger, nullable=False)
    # '80+ White'|'80+ Bronze'|'80+ Silver'|'80+ Gold'|'80+ Platinum'|'80+ Titanium'
    efficiency_rating    = db.Column(db.String(20), nullable=False)
    # 'Non-Modular'|'Semi-Modular'|'Fully Modular'
    modular_type         = db.Column(db.String(20), nullable=False)
    # 'ATX'|'SFX'|'SFX-L'|'TFX'
    form_factor          = db.Column(db.String(10), nullable=False, default="ATX")

    # Connectors
    has_12vhpwr          = db.Column(db.Boolean, default=False)   # 16-pin 12VHPWR
    has_12v2x6           = db.Column(db.Boolean, default=False)   # new 12V-2x6
    pcie_6pin_count      = db.Column(db.SmallInteger, default=0)
    pcie_8pin_count      = db.Column(db.SmallInteger, default=0)  # 6+2-pin = 8-pin here
    eps_8pin_count       = db.Column(db.SmallInteger, default=1)  # CPU power
    sata_connectors      = db.Column(db.SmallInteger, default=4)
    atx_connector        = db.Column(db.Boolean, default=True)    # 24-pin ATX

    # Fan / noise
    fan_size_mm          = db.Column(db.SmallInteger)
    fanless              = db.Column(db.Boolean, default=False)

    # 3D Builder assets
    glb_model_path       = db.Column(db.String(255))
    image_path           = db.Column(db.String(255))

    # Pricing
    msrp_usd             = db.Column(db.Numeric(8, 2))
    current_price_usd    = db.Column(db.Numeric(8, 2))
    retailer_url         = db.Column(db.String(512))
    price_last_updated   = db.Column(db.DateTime(timezone=True))

    created_at           = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at           = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    brand = db.relationship("Brand")

    @property
    def efficiency_tier(self):
        """Numeric ranking of efficiency rating for sorting."""
        tiers = {
            "80+ White": 1, "80+ Bronze": 2, "80+ Silver": 3,
            "80+ Gold": 4, "80+ Platinum": 5, "80+ Titanium": 6
        }
        return tiers.get(self.efficiency_rating, 0)

    def can_power_build(self, cpu_tdp: int, gpu_tdp: int, headroom: float = 1.25) -> bool:
        """Return True if PSU wattage covers load with safety headroom."""
        required = (cpu_tdp + gpu_tdp) * headroom
        return self.wattage >= required

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "wattage": self.wattage,
            "efficiency_rating": self.efficiency_rating,
            "modular_type": self.modular_type,
            "form_factor": self.form_factor,
            "has_12vhpwr": self.has_12vhpwr,
            "has_12v2x6": self.has_12v2x6,
            "pcie_6pin_count": self.pcie_6pin_count,
            "pcie_8pin_count": self.pcie_8pin_count,
            "eps_8pin_count": self.eps_8pin_count,
            "sata_connectors": self.sata_connectors,
            "fanless": self.fanless,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<PSU {self.name}>"


# ─────────────────────────────────────────────────────────────
# CPU COOLER  ←→  SOCKET SUPPORT  (junction table)
# ─────────────────────────────────────────────────────────────

class CoolerSocketSupport(db.Model):
    """Junction table: which CPU sockets a cooler supports."""
    __tablename__ = "cooler_socket_support"

    cooler_id = db.Column(db.Integer, db.ForeignKey("cpu_coolers.id"), primary_key=True)
    socket_id = db.Column(db.Integer, db.ForeignKey("cpu_sockets.id"), primary_key=True)

    cooler = db.relationship("CpuCooler", back_populates="socket_support_entries")
    socket = db.relationship("CpuSocket")


class CpuCooler(db.Model):
    """CPU cooler — tower air cooler or AIO liquid cooler."""
    __tablename__ = "cpu_coolers"
    __table_args__ = (
        db.Index("ix_coolers_type",           "cooler_type"),
        db.Index("ix_coolers_radiator_size",  "radiator_size_mm"),
        db.Index("ix_coolers_tdp_rating",     "tdp_rating_watts"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(200), unique=True, nullable=False)
    brand_id             = db.Column(db.Integer, db.ForeignKey("brands.id"))

    # 'Air' | 'AIO'
    cooler_type          = db.Column(db.String(10), nullable=False)

    # Air cooler dimensions
    height_mm            = db.Column(db.SmallInteger)  # critical for case clearance

    # AIO dimensions
    radiator_size_mm     = db.Column(db.SmallInteger)  # 120|140|240|280|360|420

    # Performance
    tdp_rating_watts     = db.Column(db.SmallInteger, nullable=False)

    # Fans
    fan_size_mm          = db.Column(db.SmallInteger)
    fan_count            = db.Column(db.SmallInteger)

    # Aesthetics
    rgb                  = db.Column(db.Boolean, default=False)
    rgb_type             = db.Column(db.String(10))  # 'RGB'|'ARGB'|None

    # 3D Builder assets
    glb_model_path       = db.Column(db.String(255))
    image_path           = db.Column(db.String(255))

    # Pricing
    msrp_usd             = db.Column(db.Numeric(8, 2))
    current_price_usd    = db.Column(db.Numeric(8, 2))
    retailer_url         = db.Column(db.String(512))
    price_last_updated   = db.Column(db.DateTime(timezone=True))

    created_at           = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at           = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    brand               = db.relationship("Brand")
    socket_support_entries = db.relationship(
        "CoolerSocketSupport", back_populates="cooler",
        cascade="all, delete-orphan"
    )

    @property
    def supported_sockets(self):
        """Return list of CpuSocket objects this cooler supports."""
        return [entry.socket for entry in self.socket_support_entries]

    @property
    def supported_socket_names(self):
        return [entry.socket.name for entry in self.socket_support_entries]

    def supports_socket(self, socket_name: str) -> bool:
        return socket_name in self.supported_socket_names

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "cooler_type": self.cooler_type,
            "height_mm": self.height_mm,
            "radiator_size_mm": self.radiator_size_mm,
            "tdp_rating_watts": self.tdp_rating_watts,
            "fan_size_mm": self.fan_size_mm,
            "fan_count": self.fan_count,
            "rgb": self.rgb,
            "rgb_type": self.rgb_type,
            "supported_sockets": self.supported_socket_names,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<CpuCooler {self.name}>"


# ─────────────────────────────────────────────────────────────
# PC CASE
# ─────────────────────────────────────────────────────────────

class PCCase(db.Model):
    """PC chassis / tower case."""
    __tablename__ = "pc_cases"
    __table_args__ = (
        db.Index("ix_cases_form_factor",       "form_factor"),
        db.Index("ix_cases_gpu_clearance_mm",  "gpu_clearance_mm"),
        db.Index("ix_cases_psu_form_factor",   "psu_form_factor"),
    )

    id                        = db.Column(db.Integer, primary_key=True)
    name                      = db.Column(db.String(200), unique=True, nullable=False)
    brand_id                  = db.Column(db.Integer, db.ForeignKey("brands.id"))

    # 'Mini-ITX' | 'Micro-ATX' | 'ATX Mid Tower' | 'ATX Full Tower' | 'Super Tower'
    form_factor               = db.Column(db.String(30), nullable=False)

    # Motherboard support: comma-separated supported form factors
    # e.g. 'Mini-ITX,Micro-ATX,ATX'
    supported_mobo_form_factors = db.Column(db.String(100))

    # Clearances (mm)
    gpu_clearance_mm          = db.Column(db.SmallInteger)
    cpu_cooler_clearance_mm   = db.Column(db.SmallInteger)

    # Radiator support: maximum radiator size in mm (or 0 for none)
    max_radiator_front_mm     = db.Column(db.SmallInteger, default=0)
    max_radiator_top_mm       = db.Column(db.SmallInteger, default=0)
    max_radiator_rear_mm      = db.Column(db.SmallInteger, default=0)

    # PSU
    psu_form_factor           = db.Column(db.String(10), default="ATX")  # 'ATX'|'SFX'|'SFX-L'

    # Storage bays
    drive_bays_35             = db.Column(db.SmallInteger, default=0)
    drive_bays_25             = db.Column(db.SmallInteger, default=0)

    # Aesthetics
    side_panel_type           = db.Column(db.String(30))  # 'Tempered Glass'|'Mesh'|'Steel'
    color                     = db.Column(db.String(30))
    rgb_type                  = db.Column(db.String(10))  # 'None'|'RGB'|'ARGB'
    included_fans             = db.Column(db.SmallInteger, default=0)

    # 3D Builder assets
    glb_model_path            = db.Column(db.String(255))
    image_path                = db.Column(db.String(255))

    # Pricing
    msrp_usd                  = db.Column(db.Numeric(8, 2))
    current_price_usd         = db.Column(db.Numeric(8, 2))
    retailer_url              = db.Column(db.String(512))
    price_last_updated        = db.Column(db.DateTime(timezone=True))

    created_at                = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at                = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    brand = db.relationship("Brand")

    # Form factor hierarchy for comparison
    _MOBO_RANK = {
        "Mini-ITX": 1, "Micro-ATX": 2, "ATX": 3, "E-ATX": 4, "SSI-EEB": 5
    }

    @property
    def max_radiator_mm(self):
        """Return maximum radiator size supported anywhere in the case."""
        return max(
            self.max_radiator_front_mm or 0,
            self.max_radiator_top_mm or 0,
            self.max_radiator_rear_mm or 0,
        )

    @property
    def supported_mobo_list(self):
        if self.supported_mobo_form_factors:
            return [f.strip() for f in self.supported_mobo_form_factors.split(",")]
        return []

    def supports_mobo_form_factor(self, form_factor: str) -> bool:
        return form_factor in self.supported_mobo_list

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "form_factor": self.form_factor,
            "supported_mobo_form_factors": self.supported_mobo_list,
            "gpu_clearance_mm": self.gpu_clearance_mm,
            "cpu_cooler_clearance_mm": self.cpu_cooler_clearance_mm,
            "max_radiator_front_mm": self.max_radiator_front_mm,
            "max_radiator_top_mm": self.max_radiator_top_mm,
            "max_radiator_rear_mm": self.max_radiator_rear_mm,
            "max_radiator_mm": self.max_radiator_mm,
            "psu_form_factor": self.psu_form_factor,
            "drive_bays_35": self.drive_bays_35,
            "drive_bays_25": self.drive_bays_25,
            "side_panel_type": self.side_panel_type,
            "color": self.color,
            "rgb_type": self.rgb_type,
            "included_fans": self.included_fans,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<PCCase {self.name}>"


# ─────────────────────────────────────────────────────────────
# CASE FAN
# ─────────────────────────────────────────────────────────────

class CaseFan(db.Model):
    """Case / chassis fan."""
    __tablename__ = "case_fans"
    __table_args__ = (
        db.Index("ix_fans_size_mm",  "size_mm"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(200), unique=True, nullable=False)
    brand_id             = db.Column(db.Integer, db.ForeignKey("brands.id"))

    size_mm              = db.Column(db.SmallInteger, nullable=False)  # 80|92|120|140|180|200
    # 'Sleeve Bearing'|'Hydraulic Bearing'|'Rifle Bearing'|'FDB'|'Magnetic'|'Dual Ball'
    bearing_type         = db.Column(db.String(30))
    # '3-pin DC'|'4-pin PWM'|'ARGB 3-pin'|'RGB 4-pin'
    connector_type       = db.Column(db.String(30))
    # 'Airflow'|'Static Pressure'|'Hybrid'
    airflow_type         = db.Column(db.String(20))
    # 'None'|'RGB'|'ARGB'|'Infinity Mirror RGB'|'LCD'
    rgb_type             = db.Column(db.String(30), default="None")

    max_rpm              = db.Column(db.SmallInteger)
    max_airflow_cfm      = db.Column(db.Numeric(5, 1))
    max_noise_dba        = db.Column(db.Numeric(4, 1))

    # Pack size
    pack_count           = db.Column(db.SmallInteger, default=1)

    # 3D Builder assets
    glb_model_path       = db.Column(db.String(255))
    image_path           = db.Column(db.String(255))

    # Pricing
    msrp_usd             = db.Column(db.Numeric(8, 2))
    current_price_usd    = db.Column(db.Numeric(8, 2))
    retailer_url         = db.Column(db.String(512))
    price_last_updated   = db.Column(db.DateTime(timezone=True))

    created_at           = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at           = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    brand = db.relationship("Brand")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name if self.brand else None,
            "size_mm": self.size_mm,
            "bearing_type": self.bearing_type,
            "connector_type": self.connector_type,
            "airflow_type": self.airflow_type,
            "rgb_type": self.rgb_type,
            "max_rpm": self.max_rpm,
            "max_airflow_cfm": float(self.max_airflow_cfm) if self.max_airflow_cfm else None,
            "max_noise_dba": float(self.max_noise_dba) if self.max_noise_dba else None,
            "pack_count": self.pack_count,
            "image_path": self.image_path,
            "msrp_usd": float(self.msrp_usd) if self.msrp_usd else None,
            "current_price_usd": float(self.current_price_usd) if self.current_price_usd else None,
        }

    def __repr__(self):
        return f"<CaseFan {self.name}>"