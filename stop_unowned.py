#!/usr/bin/env python3

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import sys
import argparse

parser = argparse.ArgumentParser(description="Script to stop EC2 instances")
parser.add_argument("--region", default="us-east-1", help="aws region")
parser.add_argument("--apply", action="store_true", help="stop instances, not dry run")
parser.add_argument("--expected-account", help="Intended account to hit aws sdk on")
parser.add_argument("--yes", action="store_true", help="force confirmation in cases of lambda function or cron job")

args = parser.parse_args()

filters = [{"Name": "instance-state-name", "Values": ["running"]}]

try:
    sts = boto3.client("sts")
    sts_caller = sts.get_caller_identity()
    if args.expected_account and args.expected_account != sts_caller['Account']:
        print(f"Unexpected account! Expected: {args.expected_account} does not match given: {sts_caller['Account']}", file=sys.stderr)
        sys.exit(2)

    print(f"Account: {sts_caller['Account']} Arn: {sts_caller['Arn']}", file=sys.stderr)

    ec2 = boto3.client("ec2", region_name=args.region)
    paginator = ec2.get_paginator("describe_instances")

    to_stop = []
    
    for page in paginator.paginate(Filters=filters):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                if "Owner" in tags:
                    continue

                to_stop.append((instance["InstanceId"], tags.get("Name", "-")))

    if not to_stop:
        print("Nothing to stop", file=sys.stderr)
    elif args.apply:
        for instance_id, name in to_stop:
            print(f"Will be stopped: {instance_id} {name}", file=sys.stderr)

        if not args.yes:
            confirmation = input("type yes to continue:")
            if confirmation != "yes":
                print("aborting", file=sys.stderr)
                sys.exit(0)
            else:
                print("starting stop process...", file=sys.stderr)

        stop = [instance_id for instance_id, name in to_stop]
        ec2.stop_instances(InstanceIds=stop)
        for instance_id in stop:
            print(f"Stopped {instance_id}", file=sys.stderr)
    else:
        for instance_id, name in to_stop:
            print(f"DRY RUN: would stop {instance_id} {name}")

except (BotoCoreError, ClientError) as e:
    print(e, file=sys.stderr)
    sys.exit(2)
