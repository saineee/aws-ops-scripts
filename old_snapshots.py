#!/usr/bin/env python3

import argparse
import boto3
import sys
from botocore.exceptions import BotoCoreError, ClientError
from datetime import timezone, timedelta, datetime

parser = argparse.ArgumentParser(description="Script to find EBS Snapshots older than N days (default 30), in N region (default us-east-1).")

parser.add_argument("--region", default="us-east-1", help="aws region to search")
parser.add_argument("--days", default=30, type=int, help="look for ebs snapshots older than this value")
parser.add_argument("--apply", action="store_true", help="Non dry-run: delete snapshots")
parser.add_argument("--expected-account", help="expected account that you intend to run this against")
parser.add_argument("--yes", action="store_true", help="intended for force apply during unattended runs e.g. cron jobs")

args = parser.parse_args()

if args.apply and args.expected_account is None:
    parser.error("when using --apply, you must use --expected-account")

if args.days < 0:
    print(f"--days must be a non-negative integer", file=sys.stderr)
    sys.exit(2)

now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=args.days)

total_gb = 0
to_delete = []
count = 0

try:
    sts = boto3.client("sts")
    sts_res = sts.get_caller_identity()
    acc = sts_res["Account"]
    arn = sts_res["Arn"]

    if args.expected_account and args.expected_account != acc:
        print(f"expected account: {args.expected_account} does not match actual account: {acc}", file=sys.stderr)
        sys.exit(2)

    print(f"running script as {arn}", file=sys.stderr)

    ec2 = boto3.client("ec2", region_name=args.region)
    paginator = ec2.get_paginator("describe_snapshots")
    
    print(f"searching {args.region}...", file=sys.stderr)

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page["Snapshots"]:
            tags = {tag["Key"]: tag["Value"] for tag in snapshot.get("Tags", [])}

            if tags.get("Retain", "").lower().strip() == "true":
                continue
            creation = snapshot["StartTime"]

            if creation < cutoff:
                delta = (now - creation).days
                print(f"{snapshot['SnapshotId']} - {snapshot.get('VolumeId', 'N/A')} - {delta} days old - {snapshot['VolumeSize']} GB")
                count += 1
                total_gb += snapshot["VolumeSize"]
                to_delete.append(snapshot["SnapshotId"])

        if args.apply and count:
            try:
                if not args.yes:
                    confirmation = input("This action will remove the selected snapshots. 'yes' to confirm. ")
                    if confirmation != "yes":
                        print("aborting...", file=sys.stderr)
                        sys.exit(0)

                for snap in to_delete:
                    print(f"requesting deletion for {snap}", file=sys.stderr)
                    ec2.delete_snapshot(SnapshotId=snap)
                    print(f"{snap} - deleted", file=sys.stderr)

                sys.exit(0)

            except EOFError:
                print(f"\nuse --yes when running this script for unattended runs", file=sys.stderr)
                sys.exit(2)

except (BotoCoreError, ClientError) as e:
    print(e, file=sys.stderr)
    sys.exit(2)

if count:
    print(f"{count} snapshots older than {args.days} days, {total_gb} GB total", file=sys.stderr)
    sys.exit(1)
else:
    print(f"no snapshots found older than {args.days} days", file=sys.stderr)
    sys.exit(0)
