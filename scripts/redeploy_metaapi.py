"""Force undeploy + redeploy MetaApi account to fix stale broker connection."""
import paramiko
import json

SERVER = "157.173.127.9"
USER = "root"
PASSWORD = "01877704Toni$"

METAAPI_TOKEN = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJhZjc4NTJlNDYwMTVlMDg5MjE2M2YxZDAzODNmNjk2MSIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJtZXRhYXBpLXJwYy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFzdGF0cy1hcGkiLCJtZXRob2RzIjpbIm1ldGFzdGF0cy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJyaXNrLW1hbmFnZW1lbnQtYXBpIiwibWV0aG9kcyI6WyJyaXNrLW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiYWY3ODUyZTQ2MDE1ZTA4OTIxNjNmMWQwMzgzZjY5NjEiLCJpYXQiOjE3ODM3NjIxODMsImV4cCI6MTc5MTUzODE4M30.ALjnk5ihx-SY3HcopWpPfy0P-YEgyChZtxHabVZBsLMlKJIE9thVUm2X6V5V6y54sDUgBjPsT11FgN0YZBhaCtKDmR7AlKJmL4jH33TQ7_RH8cXYPa18DhCJhndfTvPk_Wj7mMTAUmhUenZZptklWTccRKWfxyAZUdRKPghr98PhJgkr86asuiO05THEOdAQ-JWUFJ3OL0JtXQU726P8YRyyRh-P9LX5lnstZY1yfkH7EEVWWzeG0GeIXOhjDmDST6ABiYqRzeuNeY64socnJO6K9WBew2SH9hQJu9PS07tvhExUnvY9YOZJFcr61u_djKnskz8m52fd6nbRoc4zuRHIF0GwbiNIms1JDzjYg1oeesx-yaAYgxTaxXoo_uumqGduzXOuSpe00PkF1_Aa2dp67sAE-0HMpIIH6ogAU4aYYUwRYeGJB6ynzbbIoQvb_nEkCb8PkIFx1a8CRKruk-trmzxceNgDHRRWzOb3jfRu1pYbwxmStf50qyE-s3SJaCRTqcvKzqfp7VZo7m5WnIPnGcU8zJEyXIaNeb4d6oSx2ejV2hRk11y-tX8_AGZjoDWS-gSJD9jHcSMU_7NSzFXkKBzVEPCZ61n-tko8GHzjNQHls3P4QKBpnq7ApMgjv0keDZe2HIn94mwjE3qpdkF9zJb08LnGfSJQcbKQTjk"
METAAPI_ACCOUNT = "d80b2dae-5260-4e65-b4ab-a77e95cb3d89"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SERVER, username=USER, password=PASSWORD, timeout=30)

# Write a Python script to undeploy + redeploy the MetaApi account
redeploy_script = f'''#!/usr/bin/env python3
import os, asyncio, time
from metaapi_cloud_sdk import MetaApi

TOKEN = "{METAAPI_TOKEN}"
ACCOUNT_ID = "{METAAPI_ACCOUNT}"

async def main():
    api = MetaApi(TOKEN)
    acc = await api.metatrader_account_api.get_account(ACCOUNT_ID)
    print(f"Current state: {{acc.state}}")

    print("Undeploying account...")
    await acc.undeploy()
    print("Waiting for undeploy...")
    await asyncio.sleep(10)

    print("Redeploying account...")
    await acc.deploy()
    print("Waiting for deployment (up to 3 min)...")
    await acc.wait_deployed(timeout_in_seconds=180, interval_in_milliseconds=2000)
    print("Deployment complete!")

    print("READY")
    print("READY")

asyncio.run(main())
'''

stdin, stdout, stderr = client.exec_command('cat > /tmp/redeploy.py', timeout=10)
stdin.write(redeploy_script)
stdin.channel.shutdown_write()
stdout.channel.recv_exit_status()

# Kill bot, run redeploy, then restart
cmd = 'pkill -f main_v22_metaapi 2>/dev/null; sleep 2; echo '' > /root/bot_output.log; python3 /tmp/redeploy.py 2>&1; echo REDEPLOY_RESULT=$?; cd /root/My-AI-trading-Bot/trading_bot; nohup python3 main_v22_metaapi.py > /root/bot_output.log 2>&1 & echo RESTARTED; sleep 20; tail -10 /root/bot_output.log'
stdin2, stdout2, stderr2 = client.exec_command('bash -s', timeout=300)
stdin2.write(cmd)
stdin2.channel.shutdown_write()
out = stdout2.read().decode()
print(out[-3000:])
client.close()