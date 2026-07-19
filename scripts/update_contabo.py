"""Update and restart bot on Contabo."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

cmds = "cd /root/My-AI-trading-Bot\n"
cmds += "git fetch origin master\n"
cmds += "git reset --hard origin/master\n"
cmds += "echo GIT_OK\n"
cmds += "pkill -f main_v22_metaapi 2>/dev/null\n"
cmds += "sleep 2\n"
cmds += "cd trading_bot\n"
cmds += "nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &\n"
cmds += "sleep 15\n"
cmds += "ps aux | grep main_v22_metaapi | grep -v grep && echo RUNNING || echo DEAD\n"
cmds += "tail -15 /root/bot_output.log\n"

stdin, stdout, stderr = client.exec_command('bash -s', timeout=60)
stdin.write(cmds)
stdin.channel.shutdown_write()
out = stdout.read().decode()
print(out[-2000:])
client.close()