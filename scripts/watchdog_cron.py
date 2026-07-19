"""Install a cron watchdog to auto-restart the bot if it dies."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

cmds = "#!/bin/bash\n"
cmds += "pkill -f main_v22_metaapi 2>/dev/null\n"
cmds += "sleep 2\n"
cmds += "rm -f /root/bot_output.log\n"
cmds += "cd /root/My-AI-trading-Bot/trading_bot\n"
cmds += "nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &\n"
cmds += "sleep 10\n"
cmds += "echo BOT_PID: $(pgrep -f main_v22_metaapi)\n"
cmds += "ps aux | grep main_v22_metaapi | grep -v grep && echo RUNNING_OK || echo BOT_DEAD\n"
cmds += "(crontab -l 2>/dev/null | grep -v main_v22_metaapi; echo '*/5 * * * * pgrep -f main_v22_metaapi.py > /dev/null || (cd /root/My-AI-trading-Bot/trading_bot && nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 &)') | crontab -\n"
cmds += "echo CRON_INSTALLED\n"
cmds += "crontab -l\n"
cmds += "echo LOG_START:\n"
cmds += "tail -15 /root/bot_output.log\n"

stdin, stdout, stderr = client.exec_command('bash -s', timeout=30)
stdin.write(cmds)
stdin.channel.shutdown_write()
out = stdout.read().decode()
print(out[-2500:])
if stderr.channel.recv_exit_status() != 0:
    print('STDERR:', stderr.read().decode()[:500])
client.close()