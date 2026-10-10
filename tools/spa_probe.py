#!/usr/bin/env python3
"""Arctic Spa local probe (Customer Portal WebSocket, YOC 3.x firmware).

Connects to ws://<host>:8765, sends {"query": 0}, and prints the full snapshot
the spa returns (live / sett / const / error / status). Read-only.

Usage:
    python3 spa_probe.py 192.168.1.50
    python3 spa_probe.py 192.168.1.50 3     # re-query 3 times, 2s apart

Dependencies:
    pip install aiohttp
"""
import asyncio
import json
import sys

PORT = 8765


async def probe(host, queries):
    import aiohttp

    url = f"ws://{host}:{PORT}"
    sections = {}
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url, heartbeat=30) as ws:
            print(f"[connected] {url} -> sending {{'query': 0}}\n")
            for n in range(queries):
                await ws.send_str(json.dumps({"query": 0}))
                deadline = asyncio.get_event_loop().time() + 3
                while asyncio.get_event_loop().time() < deadline:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                    except asyncio.TimeoutError:
                        break
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    p = json.loads(msg.data)
                    if isinstance(p, dict) and p.get("action") == "publish":
                        sections[p.get("topic")] = p.get("data")
                if queries > 1:
                    print(f"[query {n + 1}/{queries}] sections: {list(sections)}")
                    await asyncio.sleep(2)
    for topic, data in sections.items():
        print(f"\n===== {topic} =====")
        print(json.dumps(data, indent=2, sort_keys=True))


def main():
    if len(sys.argv) < 2:
        print("usage: python3 spa_probe.py <spa-ip> [query-count]")
        sys.exit(1)
    host = sys.argv[1]
    queries = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run(probe(host, queries))


if __name__ == "__main__":
    main()
