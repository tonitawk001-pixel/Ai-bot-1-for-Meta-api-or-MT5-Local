"""Check bot logs on Contabo."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

# Write a shell script to the server
cmds = []
cmds.append("cd /root")
cmds.append("echo '=== LOG FILE SIZE ==='")
cmds.append("wc -l bot_output.log")
cmds.append("echo '=== BOT PROCESS ==='")
cmds.append("ps aux | grep main_v22_metaapi | grep -v grep")
cmds.append("echo '=== KEY EVENTS ==='")
cmds.append("grep -E 'STARTUP|SIGNAL|Cycle|HEARTBEAT|ALIVE|CLOSED' bot_output.log | tail -30")
cmds.append("echo '=== RECENT ERRORS ==='")
cmds.append("grep -E 'ERROR|CRITICAL|Failed' bot_output.log | tail -15")
cmds.append("echo '=== DONE ==='")

cmd_str = "\n".join(cmds)
stdin, stdout, stderr = client.exec_command('bash -s', timeout=15)
stdin.write(cmd_str)
stdin.channel.shutdown_write()
print(stdout.read().decode()[-3000:])
client.close()