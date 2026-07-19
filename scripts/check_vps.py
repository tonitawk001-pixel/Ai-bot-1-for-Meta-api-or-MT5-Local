"""Check Contabo VPS bot status and logs."""
import paramiko
import traceback

HOST = "157.173.127.9"
USER = "root"
PASS = "01877704Toni$"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    
    # Check bot process
    stdin, stdout, stderr = client.exec_command('ps aux | grep main_v22_metaapi | grep -v grep')
    out = stdout.read().decode().strip()
    print("=== BOT STATUS ===")
    if out:
        print("BOT IS RUNNING")
        print(out)
    else:
        print("BOT IS NOT RUNNING")
    
    # Check bot output log
    stdin2, stdout2, stderr2 = client.exec_command('cat /root/bot_output.log 2>/dev/null | tail -300')
    log_out = stdout2.read().decode()
    log_err = stderr2.read().decode()
    print("\n=== LAST 300 LINES OF bot_output.log ===")
    if log_out:
        print(log_out)
    if log_err:
        print("STDERR:", log_err[:500])
    
    # Check heartbeat log
    stdin3, stdout3, stderr3 = client.exec_command('cat /root/My-AI-trading-Bot/logs/heartbeat.log 2>/dev/null | tail -100')
    hb_out = stdout3.read().decode()
    print("\n=== LAST 100 LINES OF heartbeat.log ===")
    if hb_out:
        print(hb_out)
    else:
        print("No heartbeat log found")
    
    # List all log files
    stdin4, stdout4, stderr4 = client.exec_command('find /root -name "*.log" -o -name "*.flag" -o -name "bot_state.json" 2>/dev/null')
    print("\n=== LOG FILES ===")
    print(stdout4.read().decode()[:1000])
    
    # Check .env file
    stdin5, stdout5, stderr5 = client.exec_command('cat /root/My-AI-trading-Bot/.env 2>/dev/null || cat /root/.env 2>/dev/null || echo "No .env found"')
    print("\n=== .ENV FILE ===")
    env_out = stdout5.read().decode()
    # Mask sensitive info
    for line in env_out.split('\n'):
        if any(k in line.upper() for k in ['TOKEN', 'PASS', 'SECRET', 'KEY']):
            key = line.split('=')[0] if '=' in line else line
            print(f"{key}=***MASKED***")
        else:
            print(line)
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
finally:
    client.close()