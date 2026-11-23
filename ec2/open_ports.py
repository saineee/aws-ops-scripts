#!/usr/bin/env python3

import argparse
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import sys

parser = argparse.ArgumentParser(description="Script to check open security groups. Default ports are 22, and 3389. Use --ports to customize")
parser.add_argument("--ports", nargs="+", type=int, default=[22, 3389], help="ports to search for")
parser.add_argument("--region", default="us-east-1", help="AWS Region")

args = parser.parse_args()

for port in args.ports:
    if not 0 <= port <= 65535:
        parser.error(f"Invalid port: {port} - must be 0 - 65535")
found = False

try:
    ec2 = boto3.client("ec2", region_name=args.region)

    paginator = ec2.get_paginator("describe_security_groups")

    for page in paginator.paginate():
        for sg in page["SecurityGroups"]:

            group_id = sg["GroupId"]
            group_name = sg["GroupName"]

            for perms in sg["IpPermissions"]:
                if perms["IpProtocol"] == "-1":
                    to_port = 65535
                    from_port = 0
                    note = " (all traffic)"
                # portless protocols like GRE (47) and ESP (50)
                elif "FromPort" not in perms:
                    continue
                else:
                    to_port = perms["ToPort"]
                    from_port = perms["FromPort"]
                    note = ""

                ipv4 = {ip.get("CidrIp", "") for ip in perms.get("IpRanges", [])}
                ipv6 = {ip.get("CidrIpv6", "") for ip in perms.get("Ipv6Ranges", [])}

                if "0.0.0.0/0" not in ipv4 and "::/0" not in ipv6:
                    continue

                for port in args.ports:
                    if from_port <= port <= to_port:
                        print(f"{group_id} {group_name} {port}{note}")
                        found = True

except (BotoCoreError, ClientError) as e:
    print(e, file=sys.stderr)
    sys.exit(2)


if found:
    sys.exit(1)
else:
    sys.exit(0)

