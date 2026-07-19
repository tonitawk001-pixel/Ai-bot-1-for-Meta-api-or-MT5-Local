"""Install deps and start bot on Contabo via paramiko."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$', timeout=30)

cmds = []
cmds.append("cd /root/My-AI-trading-Bot")
cmds.append("source venv/bin/activate 2>/dev/null || true")
cmds.append("which python3")
cmds.append("echo '=== Installing packages ==='")
cmds.append("pip install pandas numpy python-dotenv metaapi_cloud_sdk requests 2>&1 | tail -5")
cmds.append("echo '=== Kill old bot ==='")
cmds.append("pkill -f 'main_v22_metaapi' 2>/dev/null || true")
cmds.append("sleep 1")
cmds.append("echo '=== Start bot ==='")
cmds.append("cd trading_bot")
cmds.append("nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &")
cmds.append("echo 'PID: ' $!")
cmds.append("sleep 5")
cmds.append("ps aux | grep main_v22_metaapi | grep -v grep && echo 'BOT RUNNING!' || echo 'NOT RUNNING'")
cmds.append("tail -15 /root/bot_output.log 2>/dev/null || echo 'No log'")

command_str = "\n".join(cmdss)

stdin, stdout, stderr = client.exec_command('bash -s', timeout=180)
stdin.write(command_str)
stdin.channel.shutdown_write()

print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err[:500])
print('DONE')
client.close()