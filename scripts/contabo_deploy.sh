"""Deploy script for Contabo - runs bot with all fixes."""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

cmds = [
    "cd /root/My-AI-trading-Bot",
    "echo '=== Python version ==='",
    "python3 --version",
    "echo '=== Check packages ==='",
    "python3 -c 'import pandas; print(\"pandas OK\")' 2>/dev/null && echo 'PANDAS_EXISTS' || echo 'PANDAS_MISSING'",
    "echo '=== Install packages system-wide ==='",
    "pip3 install pandas numpy python-dotenv metaapi_cloud_sdk requests 2>&1 | tail -3",
    "echo '=== Verify ==='",
    "python3 -c 'import pandas; print(\"pandas OK\")'",
    "echo '=== Kill old ==='",
    "pkill -f main_v22_metaapi 2>/dev/null",
    "sleep 2",
    "echo '=== Start bot ==='",
    "cd /root/My-AI-trading-Bot/trading_bot",
    "nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &",
    "sleep 15",
    "echo '=== Status ==='",
    "ps aux | grep main_v22_metaapi | grep -v grep && echo 'BOT_RUNNING' || echo 'BOT_NOT_RUNNING'",
    "echo '=== Last logs ==='",
    "tail -20 /root/bot_output.log",
]

full_cmd = "\n".join(cmds)
stdin, stdout, stderr = client.exec_command('bash -s', timeout=120)
stdin.write(full_cmd)
stdin.channel.shutdown_write()
out = stdout.read().decode()
print(out[-3000:])
client.close()