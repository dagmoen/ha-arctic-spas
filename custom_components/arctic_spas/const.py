"""Constants and the reverse-engineered data model for Arctic Spas (local).

Local interface (YOC 3.x firmware), verified live plus cross-checked against the
Android app `com.crazedcoders.globalspa` and the community integration
jkol/ha-arctic-spas:

* Transport: the spa's on-board "Customer Portal" WebSocket, ws://<host>:8765.
* On connect, send {"query": 0} to get a full dump; the server replies with
  envelopes {"action":"publish","topic":"live"|"sett"|"const"|"error"|"status",
  "data":{...}}. Re-send {"query":0} to refresh (request/response).
* Commands are sent as plain JSON on the same socket, e.g. {"setTSP": 100},
  {"P1next": 1}. Only known fields are accepted.
"""
from __future__ import annotations

DOMAIN = "arctic_spas"

DEFAULT_PORT = 8765
QUERY = {"query": 0}
TELEMETRY_SECTIONS = ("live", "sett", "const", "error", "status")

# Config entry data keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SPA_GUID = "spa_guid"

# How often to re-query the spa for a fresh snapshot (seconds).
SCAN_INTERVAL_SECONDS = 15

# Temperature limits (whole degrees Fahrenheit), from the app BuildConfig.
MIN_TEMP_F = 59
MAX_TEMP_F = 104

# Watts per raw `Current` ADC unit (calibrated against a meter by jkol).
POWER_CALIBRATION = 1.87

# SpaBoy water-chemistry indicator colours (enum order from the app).
SPABOY_COLORS = ["LOW", "CAUTION_LOW", "OK", "CAUTION_HIGH", "HIGH"]

# live `Filter` status enum.
FILTER_STATUS = {
    0: "idle", 1: "purge", 2: "filtering", 3: "suspended",
    4: "overtemperature", 5: "resuming", 6: "boost", 7: "sanitize",
}
# live `H1`/`H2` heater status enum.
HEATER_STATUS = {0: "idle", 1: "warmup", 2: "heating", 3: "cooldown"}
# live `P1`..`P5` pump speed: 0 off, 1 low, 2 high; some firmware uses 15=low, 100=high.
PUMP_SPEED = {0: "off", 1: "low", 2: "high", 15: "low", 100: "high"}

# error bitmask: bit N (in the 64-bit err64 / Upper+Lower word) -> label.
# From the app's BitmaskErrorCodes enum (com.crazedcoders.globalspa).
ERROR_BITS = {
    0: "ER00 No Flow", 1: "ER01 Flow Switch", 2: "ER02 Heater Over Temp",
    3: "ER03 Spa Over Temp", 4: "ER04 Spa Temp Probe", 5: "ER05 Spa High Limit",
    6: "ER06 EEPROM", 7: "ER07 Freeze Protect", 8: "ER08 pH High",
    9: "ER09 Heater Probe Disconnected", 10: "ER10 Heater Probe Test Failed",
    11: "ER11 SpaBoy Comms Error", 12: "ER12 Heater/Spa Cal",
    13: "ER13 Heater Way Above Spa", 14: "ER14 ORP Not Responding",
    15: "ER15 pH Low (<6.5)",
    20: "P1 Low No Current", 21: "P1 High No Current", 22: "P2 No Current",
    23: "P3 No Current", 24: "SDS No Current", 25: "YESS No Current",
    26: "Onzen No Current", 27: "Heater 1 No Current", 28: "Heater 2 No Current",
}


def decode_errors(error_section: dict | None) -> list[str]:
    """Decode an `error` payload into a list of active error labels.

    The payload carries a 64-bit mask as a hex string in `err64`, or split
    across `Upper_ERR_Word` + `Lower_ERR_Word` (concatenated hex).
    """
    if not error_section:
        return []
    raw = error_section.get("err64")
    if not raw:
        upper = error_section.get("Upper_ERR_Word")
        lower = error_section.get("Lower_ERR_Word")
        if upper is None or lower is None:
            return []
        raw = f"{upper}{lower}"
    try:
        code = int(str(raw), 16)
    except (ValueError, TypeError):
        return []
    return [label for bit, label in ERROR_BITS.items() if code & (1 << bit)]


def equipment_installed(get, cfg, section=None, field=None) -> bool:
    """Decide whether to create an entity.

    If the spec names a `cfg*` install flag, require it to be truthy — a missing
    or False flag means the hardware is not fitted, so don't create the entity
    (strict, to avoid exposing equipment the spa doesn't have). With no cfg flag,
    fall back to whether the field is being reported at all.
    """
    if cfg is not None:
        return bool(get("sett", cfg))
    if section and field:
        return get(section, field) is not None
    return True


# ---------------------------------------------------------------------------
# Switch / toggle equipment. See coordinator for how state/commands are routed.
#   key, name, field (in `live`), command (keys to set), cfg (sett install flag,
#   None = create when field present), on_values (None => >0 is on), icon
# ---------------------------------------------------------------------------
# Pump 1 is a 2-speed (off/low/high) cycle pump handled by select.py, not here.
SWITCHES = [
    {"key": "pump2", "name": "Pump 2", "field": "P2", "command": ["P2next"], "cfg": "cfgP2", "on_values": None, "icon": "mdi:pump"},
    {"key": "pump3", "name": "Pump 3", "field": "P3", "command": ["P3next"], "cfg": "cfgP3", "on_values": None, "icon": "mdi:pump"},
    {"key": "pump4", "name": "Pump 4", "field": "P4", "command": ["P4next"], "cfg": "cfgP4", "on_values": None, "icon": "mdi:pump"},
    {"key": "pump5", "name": "Pump 5", "field": "P5", "command": ["P5next"], "cfg": "cfgP5", "on_values": None, "icon": "mdi:pump"},
    {"key": "blower1", "name": "Blower 1", "field": "BL1", "command": ["Bl1next"], "cfg": "cfgB1", "on_values": None, "icon": "mdi:weather-windy"},
    {"key": "blower2", "name": "Blower 2", "field": "BL2", "command": ["Bl2next"], "cfg": "cfgB2", "on_values": None, "icon": "mdi:weather-windy"},
    {"key": "lights", "name": "Lights", "field": "Li", "command": ["Linext"], "cfg": "cfgLi", "on_values": [1, 15], "icon": "mdi:lightbulb"},
    {"key": "fogger", "name": "Fogger", "field": "Fogger", "command": ["Fgnext"], "cfg": "cfgFG", "on_values": [1], "icon": "mdi:weather-fog"},
    {"key": "sds", "name": "SDS", "field": "SDS", "command": ["SDSnext"], "cfg": "cfgSDS", "on_values": [1], "icon": "mdi:air-filter"},
    {"key": "yess", "name": "YESS", "field": "Yess", "command": ["YESSnext"], "cfg": "cfgYESS", "on_values": [1], "icon": "mdi:power"},
    {"key": "onzen", "name": "Onzen", "field": "On", "command": ["Onznext"], "cfg": "cfgOn", "on_values": [1], "icon": "mdi:water-opacity"},
    {"key": "ozone", "name": "Ozone", "field": "Oz", "command": ["OzPeak1", "OzPeak2"], "cfg": "cfgOzP1", "on_values": None, "icon": "mdi:air-purifier"},
    {"key": "spaboy_boost", "name": "SpaBoy Boost", "field": "sbBoost", "command": ["SBboost"], "cfg": "cfgSB", "on_values": None, "icon": "mdi:flash"},
    {"key": "all_on", "name": "All On", "field": "AllOn", "command": ["allOn"], "cfg": None, "on_values": [1], "icon": "mdi:power"},
]

# Pump-1 speed model (cycle button off -> low -> high -> off; P1next advances).
PUMP1_SPEEDS = ["off", "low", "high"]


def pump1_speed(value) -> str | None:
    """Map a live P1 value to off/low/high."""
    if value is None:
        return None
    v = int(value)
    if v == 0:
        return "off"
    if v >= 100 or v == 2:
        return "high"
    return "low"  # 15, 1, or any other on-value


# ---------------------------------------------------------------------------
# Numeric / text sensors. section is "live" or "sett".
# ---------------------------------------------------------------------------
SENSORS = [
    {"key": "water_temp", "name": "Water Temperature", "section": "live", "field": "STemp",
     "device_class": "temperature", "unit": "°F", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"key": "spaboy_ph", "name": "SpaBoy pH Level", "section": "live", "field": "sbpH", "cfg": "cfgSB",
     "divisor": 100, "state_class": "measurement", "icon": "mdi:ph"},
    # SpaBoy measures sanitizer strength as ORP in millivolts (not chlorine ppm);
    # named "Chlorine Level" to match the app's framing.
    {"key": "spaboy_orp", "name": "SpaBoy Chlorine Level", "section": "live", "field": "sbORP", "cfg": "cfgSB",
     "unit": "mV", "state_class": "measurement", "icon": "mdi:water-check"},
    {"key": "power", "name": "Power", "section": "live", "field": "Current",
     "multiplier": POWER_CALIBRATION, "round": 0, "device_class": "power", "unit": "W",
     "state_class": "measurement", "icon": "mdi:flash"},
    {"key": "spaboy_electrode_wear", "name": "SpaBoy Electrode Wear", "section": "live", "field": "sbWear", "cfg": "cfgSB",
     "unit": "%", "state_class": "measurement", "icon": "mdi:percent", "category": "diagnostic"},
    {"key": "spaboy_cell_temp", "name": "SpaBoy Cell Temperature", "section": "live", "field": "sbTemp", "cfg": "cfgSB",
     "device_class": "temperature", "unit": "°C", "state_class": "measurement", "category": "diagnostic"},
    {"key": "spaboy_input_voltage", "name": "SpaBoy Input Voltage", "section": "live", "field": "sbVin", "cfg": "cfgSB",
     "divisor": 1000, "device_class": "voltage", "unit": "V", "state_class": "measurement", "category": "diagnostic"},
    {"key": "heater_outlet_temp", "name": "Heater Outlet Temperature", "section": "live", "field": "HTemp",
     "device_class": "temperature", "unit": "°F", "state_class": "measurement", "category": "diagnostic"},
    {"key": "filtration_frequency", "name": "Filtration Frequency", "section": "sett", "field": "FF",
     "state_class": "measurement", "icon": "mdi:calendar-clock", "category": "diagnostic"},
    {"key": "filtration_duration", "name": "Filtration Duration", "section": "sett", "field": "FD",
     "unit": "h", "state_class": "measurement", "icon": "mdi:timer-outline", "category": "diagnostic"},
]

# Enum sensors computed from an integer field via a map.
ENUM_SENSORS = [
    {"key": "filter_status", "name": "Filter Status", "section": "live", "field": "Filter",
     "map": FILTER_STATUS, "icon": "mdi:air-filter"},
    {"key": "heater1", "name": "Heater 1", "section": "live", "field": "H1", "cfg": "cfgH1",
     "map": HEATER_STATUS, "icon": "mdi:radiator", "category": "diagnostic"},
    {"key": "heater2", "name": "Heater 2", "section": "live", "field": "H2", "cfg": "cfgH2",
     "map": HEATER_STATUS, "icon": "mdi:radiator", "category": "diagnostic"},
    {"key": "spaboy_ph_status", "name": "SpaBoy pH Status", "section": "live", "field": "sbpHind", "cfg": "cfgSB",
     "map": {i: v for i, v in enumerate(SPABOY_COLORS)}, "icon": "mdi:ph"},
    {"key": "spaboy_orp_status", "name": "SpaBoy Chlorine Status", "section": "live", "field": "sbORPind", "cfg": "cfgSB",
     "map": {i: v for i, v in enumerate(SPABOY_COLORS)}, "icon": "mdi:water-check"},
]


# ---------------------------------------------------------------------------
# Binary sensors.
# ---------------------------------------------------------------------------
BINARY_SENSORS = [
    {"key": "heating", "name": "Heating", "field": "__heating__", "device_class": "heat", "icon": "mdi:radiator"},
    {"key": "filtering", "name": "Filtering", "field": "__filtering__", "icon": "mdi:air-filter"},
    {"key": "exhaust", "name": "Exhaust", "section": "live", "field": "Fan", "cfg": "cfgEx", "device_class": "running", "icon": "mdi:fan"},
    {"key": "spaboy_producing", "name": "SpaBoy Producing", "section": "live", "field": "sbProducing", "cfg": "cfgSB", "device_class": "running", "icon": "mdi:water-sync"},
    {"key": "spaboy_connected", "name": "SpaBoy Connected", "section": "live", "field": "SBConnected", "cfg": "cfgSB", "device_class": "connectivity", "category": "diagnostic"},
    {"key": "rfid_connected", "name": "RFID Connected", "section": "live", "field": "RFIDConnected", "cfg": "cfgRFID", "device_class": "connectivity", "category": "diagnostic"},
    {"key": "economy", "name": "Economy Mode", "section": "live", "field": "Econ", "icon": "mdi:leaf"},
    {"key": "error", "name": "Error", "field": "__error__", "device_class": "problem", "icon": "mdi:alert"},
]
