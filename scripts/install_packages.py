"""Install Python packages and start bot on Contabo via SSH."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$', timeout=30)

# Use simple multi-line string, avoid escapes
cmds = []
cmds.append("cd /root/My-AI-trading-Bot")
cmds.append("source venv/bin/activate 2>/dev/null")
cmds.append("echo '=== Installing deps ==='")
cmds.append("pip install pandas numpy python-dotenv metaapi_cloud_sdk requests --break-system-packages 2>&1 | tail -5")
cmds.append("echo '=== Kill old ==='")
cmds.append("pkill -f main_v22_metaapi 2>/dev/null")
cmds.append("sleep 1")
cmds.append("echo '=== Starting bot ==='")
cmds.append("cd trading_bot")
cmds.append("nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &")
cmds.append("BOTPID=$!")
cmds.append("echo 'PID=' $BOTPID")
cmds.append("sleep 5")
cmds.append("ps aux | grep main_v22_metaapi | grep -v grep && echo 'RUNNING_OK' || echo 'NOT_RUNNING'")
cmds.append("echo '=== LAST LOG LINES ==='")
cmds.append("tail -20 /root/bot_output.log 2>/dev/null || echo 'no log'")

full_cmd = "\n".join(cmds)

stdin, stdout, stderr = client.exec_command('bash -s', timeout=180)
stdin.write(full_cmd)
stdin.channel.shutdown_write()

out = stdout.read().decode()
err = stderr.read().decode()

print("OUTPUT:")
print(out)
if err:
    lines = [l for l in err.split("\n") if "password" not in l.lower()]
    if lines:
        print("STDERR:", "\n".join(lines[:10]))

client.close()
print("\n=== DONE ===")