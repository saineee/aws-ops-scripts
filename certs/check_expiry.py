#!/usr/bin/env python3

import socket
import ssl
import time
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

HOSTS_FILE = Path(__file__).resolve().parent / "hosts.txt"
WARN_DAYS = 30
load_dotenv(Path(__file__).resolve().parent / ".env")

def get_days_left(host):
    ctx = ssl.create_default_context()

    with socket.create_connection((host, 443), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            cert = tls.getpeercert()
            expire = cert["notAfter"]

            expires = ssl.cert_time_to_seconds(expire)
            days_left = (expires - time.time()) / 86400

            return int(days_left)


def check_host(host, warn_days):
    try:
        days = get_days_left(host)
        if days < warn_days:
            return {"host": host, "status": "warn", "details": f"expires in {days} days"}
        else:
            return {"host": host, "status": "ok", "details": f"{days} days"}
    except ssl.SSLCertVerificationError as e:
        return {"host": host, "status": "finding", "details": f"code {e.verify_code}: {e.verify_message}"}
    except socket.gaierror:
        return {"host": host, "status": "check_error", "details": "DNS lookup failed"}
    except TimeoutError:
        return {"host": host, "status": "check_error", "details": "timed out"}
    except OSError as e:
        return {"host": host, "status": "check_error", "details": str(e)}

def send_alert(message):
    url = os.environ["ALERT_WEBHOOK_URL"]

    resp = requests.post(url, json={"content": message}, timeout=10)
    if resp.status_code != 204:
        print(resp)

def main():
    hosts = []

    with open(HOSTS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hosts.append(line)

    for host in hosts:
        res = check_host(host, WARN_DAYS)
        print(f"Host: {res['host']} | Status: {res['status']} | Details: {res['details']}")

    message = "Hi"

    send_alert(message)

if __name__ == "__main__":
    sys.exit(main())
