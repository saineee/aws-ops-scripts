#!/usr/bin/env python3

import argparse
import boto3
import sys
from botocore.exceptions import BotoCoreError, ClientError
from datetime import timezone, timedelta, datetime

parser = argparse.ArgumentParser(description="Script to find EBS Snapshots older than N days (default 30), in N region (default us-east-1).")

parser.add_argument("--region", default="us-east-1", help="aws region to search")
parser.add_argument("--days", default=30, type=int, help="look for ebs snapshots older than this value")

args = parser.parse_args()

if args.days < 0:
    print(f"--days must be a non-negative integer", file=sys.stderr)
    sys.exit(2)

now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=args.days)

found = False

try:
    ec2 = boto3.client("ec2", region_name=args.region)
    paginator = ec2.get_paginator("describe_snapshots")
    
    print(f"searching {args.region}...", file=sys.stderr)

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page["Snapshots"]:
            creation = snapshot["StartTime"]
            if creation < cutoff:
                delta = (now - creation).days
                found = True
                print(f"{snapshot['SnapshotId']} - {snapshot.get('VolumeId', 'N/A')} - {delta} days old - {snapshot['VolumeSize']} GB")
                
except (BotoCoreError, ClientError) as e:
    print(e, file=sys.stderr)
    sys.exit(2)

if found:
    sys.exit(1)
else:
    print("no snapshots found", file=sys.stderr)
    sys.exit(0)
