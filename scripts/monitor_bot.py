#!/usr/bin/env python3
"""
V22 Bot Health Monitor
======================
Lightweight, read-only health check for the live trading bot.
Run on VPS: python3 monitor_bot.py
"""

import os, sys, json, subprocess
from datetime import datetime

BOT_PROCESS_NAME = "main_v22_metaapi.py"
BOT_LOG = "/root/bot_output.log"
STATE_FILE = "/root/My-AI-trading-Bot/logs/bot_state.json"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def ok(t):  return f"{GREEN}{t}{RESET}"
def er(t):  return f"{RED}{t}{RESET}"
def wa(t):  return f"{YELLOW}{t}{RESET}"
def cy(t):  return f"{CYAN}{t}{RESET}"
def bo(t):  return f"{BOLD}{t}{RESET}"

def hr(title):
    print(f"\n{cy('='*45)}")
    print(f"  {bo(cy(title))}")
    print(f"{cy('='*45)}")

def check_process():
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        for line in r.stdout.split("\n"):
            if BOT_PROCESS_NAME in line and "grep" not in line:
                parts = line.split()
                return {"running": True, "pid": parts[1], "cpu": parts[2], "mem": parts[3]}
        return {"running": False, "pid": None}
    except Exception as e:
        return {"running": False, "pid": None, "error": str(e)}

def check_log():
    res = {"timestamp": None, "balance": None, "errors": [], "cycle": None}
    try:
        with open(BOT_LOG, "r") as f: lines = f.readlines()
    except:
        return res
    for line in reversed(lines[-40:]):
        line = line.strip()
        if not res["timestamp"]:
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    datetime.strptime(line[:19], fmt)
                    res["timestamp"] = line[:19]
                except: pass
        if "Balance: $" in line and not res["balance"]:
            try: res["balance"] = float(line.split("Balance: $")[1].split()[0])
            except: pass
        if ("ERROR" in line or "CRITICAL" in line) and len(res["errors"]) < 5:
            res["errors"].append(line[:120])
        if "Cycle #" in line and not res["cycle"]:
            try: res["cycle"] = line.split("Cycle #")[1].split()[0]
            except: pass
    return res

def check_state():
    r = {"exists": False, "positions": 0, "halted": False}
    if not os.path.exists(STATE_FILE): return r
    r["exists"] = True
    try:
        s = json.load(open(STATE_FILE))
        r["positions"] = len(s.get("positions", []))
        if s.get("halt_until"): r["halted"] = True
    except: pass
    return r

def uptime(pid):
    try:
        ut = float(open("/proc/uptime").read().split()[0])
        st = int(open(f"/proc/{pid}/stat").read().split()[21])
        sec = ut - (st / 100)
        h, m = int(sec//3600), int((sec%3600)//60)
        return f"{h}h {m}m"
    except: return None

def main():
    print()
    print(cy("=" * 45))
    print(f"  {bo(cy('V22 BOT HEALTH MONITOR'))}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(cy("=" * 45))

    hr("1. PROCESS STATUS")
    p = check_process()
    if p["running"]:
        ut = uptime(p["pid"])
        u = f"({ok(ut)})" if ut else ""
        print(f"  Status:  {ok('RUNNING')}")
        print(f"  PID:     {ok(p['pid'])} {u}")
        print(f"  CPU:     {p['cpu']}%  MEM: {p['mem']}%")
    else:
        print(f"  Status:  {er('NOT RUNNING')}")

    hr("2. LOG ANALYSIS")
    l = check_log()
    ts = l.get("timestamp") or "N/A"
    bal = f"${l['balance']:.2f}" if l.get("balance") else "N/A"
    cyc = l.get("cycle") or "N/A"
    print(f"  Last Log:  {ts}")
    print(f"  Balance:   {ok(bal)}")
    print(f"  Cycle:     {cyc}")
    if l["errors"]:
        err_count = len(l["errors"])
        print(f"\n  {er(f'{err_count} ERRORS:')}")
        for e in l["errors"]: print(f"    {er('!')} {e}")
    else:
        print(f"  Errors:    {ok('None in last 40 lines')}")

    hr("3. STATE FILE")
    s = check_state()
    if s["exists"]:
        pc = s["positions"]
        ps = ok("0") if pc == 0 else wa(str(pc))
        print(f"  File:      {ok('Exists')}")
        print(f"  Positions: {ps}")
        print(f"  Halted:    {wa('YES') if s['halted'] else ok('No')}")
    else:
        print(f"  File:  {wa('Not found (fresh start?)')}")

    hr("SUMMARY")
    healthy = p["running"] and l.get("balance") is not None and not l["errors"]
    if healthy:      print(f"  {ok('System is HEALTHY')}")
    elif p["running"]: print(f"  {wa('Running but has errors')}")
    else:              print(f"  {er('System is DOWN - investigate')}")
    print()

if __name__ == "__main__":
    main()