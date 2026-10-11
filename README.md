# Arctic Spas (Local) — Home Assistant integration

Control an Arctic Spas hot tub **locally** from Home Assistant — no cloud
account, no internet dependency. It talks to the spa's on-board "Customer
Portal" WebSocket server on your LAN. Unofficial; not affiliated with Arctic Spas.

## Requirements

- Spa with **YOC 3.x firmware** (the generation that runs the local WebSocket
  server on **port 8765**). Verified against YOC 3.1.66 / LPC 1.2.66 /
  SpaBoy 1.0.35.
- Home Assistant 2024.1+.
- Spa reachable from Home Assistant on the network (same subnet, or routed).

Not sure if your spa qualifies? Run `tools/spa_probe.py <spa-ip>` — if it prints
a `live` section, you're good.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/dagmoen/ha-arctic-spas`, category **Integration**.
2. Install **Arctic Spas (Local)**, restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** → *Arctic Spas (Local)* →
   confirm the discovered spa, or enter its IP.

## Entities

- **Climate** — water temperature (current + setpoint, heat-only, °F), with
  heating/idle action from the heater state.
- **Pump 1 (select)** — off / low / high. Pump 1 is a 2-speed cycle pump
  (`P1next` just advances off→low→high→off), so the select presses the cycle the
  right number of times to reach your choice, and always shows the **active
  speed** — including when the spa drops to low on its own for circulation.
- **Switches** — pumps 2–5, blowers, lights, fogger, SDS, YESS, Onzen, ozone,
  SpaBoy boost, All On. Only installed equipment is created (from `cfg*` flags).
- **Button** — Filter Boost (one-shot timed cycle).
- **Sensors** — water temp, **power (W)**, SpaBoy pH & chlorine (ORP mV), filter status,
  heater status, filtration schedule, an **error** summary (decoded fault
  names), plus diagnostics (electrode wear, cell temp, input voltage,
  heater-outlet temp).
- **Binary sensors** — heating, filtering, error (with `active_errors` list),
  SpaBoy producing/connected, economy.

## How it works

Reverse-engineered from the official app `com.crazedcoders.globalspa` and
verified live; cross-checked against the community project
[jkol/ha-arctic-spas](https://github.com/jkol/ha-arctic-spas).

- **Transport:** `ws://<spa-ip>:8765` (the spa's Customer Portal server).
- **Read:** on connect the integration sends `{"query": 0}`; the spa replies
  with a full snapshot as envelopes
  `{"action":"publish","topic":"live"|"sett"|"const"|"error"|"status","data":{…}}`.
  It re-queries every 15 s to keep state fresh (request/response — the spa does
  **not** stream on a timer).
- **Control:** commands are plain JSON on the same socket, e.g. `{"setTSP":100}`,
  `{"P1next":1}`, `{"Linext":0}`. Only known fields are accepted. After a command
  the integration re-queries immediately so HA reflects the change within ~0.5 s.
- **Scaling (verified):** temperatures are whole °F; `sbpH` ÷100 (847 → 8.47);
  `sbORP` in mV; power = `Current × 1.87` W (meter-calibrated); pump `15`=low,
  `100`/`2`=high.

## Known hardware limitations

- **Pump 1 "off" during heating/filtration.** When the spa is heating or
  filtering it forces pump 1 to low and won't let it be turned off. The select
  will show `low` and, if you ask for `off` in that state, it stops cleanly
  rather than cycling the pump (it simply can't be turned off until the spa
  finishes). This matches the official app.
- **Light color isn't readable.** Lights expose on/off only. The bulb cycles
  color on each "on" (same as the app), but the active color is not reported in
  the local telemetry, so there's no color state/picker in Home Assistant.

## Security

The spa's local server has **no authentication** — anyone on the network can
read and control it. Keep the spa on a trusted LAN/VLAN.

## Credits

Field semantics and the power calibration were cross-checked against
[jkol/ha-arctic-spas](https://github.com/jkol/ha-arctic-spas); cloud-based
alternatives include [rgerrans/arctic_spa](https://github.com/rgerrans/arctic_spa)
and [pashdown/arctic_spa](https://github.com/pashdown/arctic_spa).

## Status

v0.2 — local WebSocket transport. Read + control verified end-to-end against a
real spa.
