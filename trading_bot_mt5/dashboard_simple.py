"""V22 Bot Dashboard - Start/Stop/Restart. Zero dependencies."""
import os, sys, json, subprocess, signal, time
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_SCRIPT = os.path.join(BOT_DIR, "main_mt5.py")
STATE_FILE = os.path.join(BOT_DIR, "bot_state.json")
LOG_FILE = os.path.join(BOT_DIR, "bot_output.log")

bot_pid = None

def read_log(n=15):
    if not os.path.exists(LOG_FILE): return []
    try:
        with open(LOG_FILE, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [l.strip() for l in lines[-n:]]
    except:
        return []

def get_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api":
            return self.api_json()
        self.send_html()

    def api_json(self):
        running = False
        if bot_pid:
            try: os.kill(bot_pid, 0); running = True
            except: pass
        
        bal = eq = login = "?"
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                info = mt5.account_info()
                if info:
                    bal = f"{info.balance:.2f}"
                    eq = f"{info.equity:.2f}"
                    login = str(info.login)
                mt5.shutdown()
        except: pass
        
        s = get_state()
        d = {
            "running": running, "pid": bot_pid or 0,
            "balance": bal, "equity": eq, "login": login,
            "positions": len(s.get("positions", [])),
            "trades": len(s.get("trades_log", [])),
            "pnl": f"{s.get('daily_pnl',0):+.2f}",
            "log": read_log(15),
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(d).encode())

    def send_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">
<title>V22 Bot Control</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#1a1a2e;color:#eee;padding:20px;max-width:700px;margin:auto}
h1{color:#00d4aa;text-align:center;font-size:24px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.card{background:#16213e;border-radius:10px;padding:15px;margin-bottom:12px}
.ct{color:#00d4aa;font-weight:bold;font-size:14px;margin-bottom:10px}
.rw{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #0f3460}
.lb{color:#888;font-size:13px}.vl{font-weight:bold;font-size:13px}
.g{color:#00d4aa}.r{color:#e74c3c}
.btn{padding:10px 20px;font-size:15px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin:5px 8px}
.gb{background:#00d4aa;color:#111}.rb{background:#e74c3c;color:#fff}.ob{background:#f39c12;color:#111}
.bg{text-align:center;padding:10px 0}.bg form{display:inline}
.lg{background:#0a0a23;padding:10px;border-radius:8px;font-family:monospace;font-size:11px;color:#0f0;max-height:200px;overflow-y:auto;line-height:1.4}
.ft{text-align:center;color:#555;font-size:11px;margin-top:15px}
</style></head><body>
<h1>V22 Gold Bot</h1>
<div class="sub">MT5 Local - Dashboard Control</div>
<div class="card"><div class="ct">STATUS</div>
<div class="rw"><span class="lb">Bot</span><span class="vl" id="s"></span></div>
<div class="rw"><span class="lb">MT5 Login</span><span class="vl" id="l"></span></div>
<div class="rw"><span class="lb">Balance</span><span class="vl g" id="b"></span></div>
<div class="rw"><span class="lb">Equity</span><span class="vl g" id="e"></span></div>
<div class="rw"><span class="lb">Open Pos</span><span class="vl" id="p"></span></div>
<div class="rw"><span class="lb">Total Trades</span><span class="vl" id="t"></span></div>
<div class="rw"><span class="lb">Daily P&L</span><span class="vl" id="d"></span></div>
</div>
<div class="card bg"><div class="ct">CONTROLS</div>
<form method=POST action=/start><button class="btn gb">START</button></form>
<form method=POST action=/stop><button class="btn rb">STOP</button></form>
<form method=POST action=/restart><button class="btn ob">RESTART</button></form>
</div>
<div class="card"><div class="ct">RECENT LOG</div>
<div class="lg" id="log"></div></div>
<div class="ft">Auto-refresh every 5 seconds</div>
<script>
fetch('/api').then(r=>r.json()).then(d=>{
document.getElementById('s').innerHTML=(d.running?'RUNNING ':'STOPPED')+(d.pid?'(PID '+d.pid+')':'');
document.getElementById('l').innerHTML=d.login;document.getElementById('b').innerHTML='$'+d.balance;
document.getElementById('e').innerHTML='$'+d.equity;document.getElementById('p').innerHTML=d.positions;
document.getElementById('t').innerHTML=d.trades;document.getElementById('d').innerHTML=d.pnl;
document.getElementById('log').innerHTML=(d.log||[]).join('<br>')||'No logs';
});
</script></body></html>"""
        self.wfile.write(html.encode())

    def do_POST(self):
        global bot_pid
        if self.path == "/stop":
            if bot_pid:
                try: os.kill(bot_pid, signal.SIGTERM); time.sleep(1)
                except: pass
                try: os.kill(bot_pid, 0); os.kill(bot_pid, signal.SIGKILL)
                except: pass
                bot_pid = None
        elif self.path in ("/start", "/restart"):
            if bot_pid:
                try: os.kill(bot_pid, signal.SIGTERM); time.sleep(1)
                except: pass
                try: os.kill(bot_pid, 0); os.kill(bot_pid, signal.SIGKILL)
                except: pass
                bot_pid = None
            time.sleep(1)
            try:
                p = subprocess.Popen([sys.executable, BOT_SCRIPT],
                    stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT, cwd=BOT_DIR)
                bot_pid = p.pid
                time.sleep(2)
            except: pass
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, format, *args): pass

if __name__ == "__main__":
    print("=" * 40)
    print("  V22 Bot Dashboard")
    print("  Open: http://localhost:5000")
    print("  Close: Ctrl+C")
    print("=" * 40)
    HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()