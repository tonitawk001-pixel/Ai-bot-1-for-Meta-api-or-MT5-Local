"""Deploy and start bot on Contabo."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

cmds = "#!/bin/bash\n"
cmds += "cd /root/My-AI-trading-Bot\n"
cmds += "pip3 install pandas numpy python-dotenv metaapi_cloud_sdk requests --break-system-packages 2>&1 | tail -3\n"
cmds += 'echo "INSTALL_DONE"\n'
cmds += 'python3 -c "import pandas; print(\'pandas OK\')"\n'
cmds += "pkill -f main_v22_metaapi 2>/dev/null\n"
cmds += "sleep 2\n"
cmds += "cd trading_bot\n"
cmds += "nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &\n"
cmds += "sleep 15\n"
cmds += "ps aux | grep main_v22_metaapi | grep -v grep && echo 'RUNNING' || echo 'DEAD'\n"
cmds += "tail -15 /root/bot_output.log\n"

stdin, stdout, stderr = client.exec_command('bash -s', timeout=120)
stdin.write(cmds)
stdin.channel.shutdown_write()
out = stdout.read().decode()[-3000:]
err = stderr.read().decode()
print(out)
print("DONE")
client.close()