"""Fix the region in .env and start the bot on Contabo."""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

cmds = [
    "cd /root/My-AI-trading-Bot/trading_bot",
    "# Remove any existing REGION line",
    "sed -i '/METAAPI_REGION/d' .env",
    "# Add REGION=london",
    "echo 'METAAPI_REGION=london' >> .env",
    "echo '=== .env contents ==='",
    "cat .env",
    "echo '=== Killing old bot ==='",
    "pkill -f main_v22_metaapi 2>/dev/null",
    "sleep 2",
    "echo '=== Starting bot ==='",
    "cd /root/My-AI-trading-Bot/trading_bot",
    "nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &",
    "BOTPID=$!",
    "echo 'Started PID:' $BOTPID",
    "sleep 10",
    "echo '=== Checking if running ==='",
    "ps aux | grep main_v22_metaapi | grep -v grep && echo 'BOT_ALIVE' || echo 'BOT_DEAD'",
    "echo '=== Last log lines ==='",
    "tail -15 /root/bot_output.log",
]

full_cmd = "\n".join(cmds)
stdin, stdout, stderr = client.exec_command('bash -s', timeout=30)
stdin.write(full_cmd)
stdin.channel.shutdown_write()

out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:500])

client.close()