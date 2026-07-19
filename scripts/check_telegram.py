"""Check if Contabo bot sends Telegram startup message."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('157.173.127.9', username='root', password='01877704Toni$')

# Use heredoc to bypass PowerShell issues
cmd = "grep -E 'Telegram|ERROR|init' /root/bot_output.log | tail -10"
stdin, stdout, stderr = client.exec_command("bash -c " + repr(cmd), timeout=10)
print(stdout.read().decode())
client.close()