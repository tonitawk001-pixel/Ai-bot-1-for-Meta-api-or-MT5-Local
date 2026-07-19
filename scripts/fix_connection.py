"""Fix MetaApi connection: restart bot with full connection reset."""
import paramiko

SERVER = "157.173.127.9"
USER = "root"
PASSWORD = "01877704Toni$"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SERVER, username=USER, password=PASSWORD)

# Kill bot, force clean state, restart
cmd = []
cmd.append("pkill -f main_v22_metaapi 2>/dev/null")
cmd.append("sleep 3")
cmd.append("rm -f /root/My-AI-trading-Bot/logs/bot_state.json")
cmd.append("rm -f /root/bot_output.log")
cmd.append("cd /root/My-AI-trading-Bot/trading_bot")
cmd.append("# Also remove METAAPI_REGION from .env if present")
cmd.append("sed -i '/METAAPI_REGION/d' /root/My-AI-trading-Bot/trading_bot/.env 2>/dev/null")
cmd.append("nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &")
cmd.append("echo WAITING...")
cmd.append("sleep 40")
cmd.append("echo BOT_PID")
cmd.append("pgrep -f main_v22_metaapi")
cmd.append("echo CONNECTION_TEST")
cmd.append("grep -E 'connected|Balance|ERROR|subscribe|timeout' /root/bot_output.log | tail -10")

stdin, stdout, stderr = client.exec_command("bash -s", timeout=60)
stdin.write("\n".join(cmd))
stdin.channel.shutdown_write()
out = stdout.read().decode()
print(out[-2500:])
client.close()