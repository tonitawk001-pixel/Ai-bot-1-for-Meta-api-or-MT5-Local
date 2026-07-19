"""Check Contabo bot status via paramiko."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

cmds = "hostname; echo BOT_PID; ps aux | grep main_v22_metaapi | grep -v grep; echo LAST_EVENTS; grep -E 'Balance:|Cycle|CLOSED|ALIVE|connected' /root/bot_output.log | tail -6; echo RECONNECTS; grep -c 'retrying subscription' /root/bot_output.log"

stdin, stdout, stderr = client.exec_command('bash -s', timeout=10)
stdin.write(cmds)
stdin.channel.shutdown_write()
print(stdout.read().decode()[-2000:])
client.close()