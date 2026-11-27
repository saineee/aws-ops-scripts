#!/usr/bin/env python3

import socket
import ssl
import time
import os
import sys
import requests

def get_days_left(host):

    ctx = ssl.create_default_context()

    with socket.create_connection((host, 443), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:

            cert = tls.getpeercert()
            expire = cert["notAfter"]

            expires = ssl.cert_time_to_seconds(expire)
            days_left = (expires - time.time()) / 86400

            return int(days_left)

print(get_days_left("google.com"))
