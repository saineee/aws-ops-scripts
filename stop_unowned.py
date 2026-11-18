#!/usr/bin/env python3

import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError
import sys
import argparse

filters = [{"Name": "instance-state-name", "Values": ["running"]}]

def main():
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Script to stop EC2 instances")
    parser.add_argument("--region", default="us-east-1", help="aws region")
    parser.add_argument("--apply", action="store_true", help="stop instances, not dry run")
    parser.add_argument("--expected-account", help="Intended account to hit aws sdk on")
    parser.add_argument("--yes", action="store_true", help="force apply on unattended runs of this script")

    args = parser.parse_args()


    if args.apply and args.expected_account is None:
        parser.error("--apply requires --expected-account")

    try:
        sts = boto3.client("sts")
        sts_caller = sts.get_caller_identity()
        if args.expected_account and args.expected_account != sts_caller['Account']:
            logging.error(f"Unexpected account! Expected: {args.expected_account} does not match given: {sts_caller['Account']}")
            sys.exit(2)

        logging.info(f"Account: {sts_caller['Account']} Arn: {sts_caller['Arn']}")

        ec2 = boto3.client("ec2", region_name=args.region)
        paginator = ec2.get_paginator("describe_instances")

        to_stop = []
        
        for page in paginator.paginate(Filters=filters):
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                    if "Owner" in tags or "aws:autoscaling:groupName" in tags:
                        continue

                    to_stop.append((instance["InstanceId"], tags.get("Name", "-")))

        if not to_stop:
            logging.warning("Nothing to stop")
        elif args.apply:
            for instance_id, name in to_stop:
                logging.info(f"Will be stopped: {instance_id} {name}")

            if not args.yes:
                try:
                    confirmation = input("type yes to continue: ")
                except EOFError:
                    logging.error("use --yes for unattended runs")
                    sys.exit(2)

                if confirmation != "yes":
                    logging.warning("aborting")
                    sys.exit(0)
                else:
                    logging.info("starting stop process...")

            stop = [instance_id for instance_id, name in to_stop]
            ec2.stop_instances(InstanceIds=stop)
            for instance_id in stop:
                logging.info(f"Stopped {instance_id}")
        else:
            for instance_id, name in to_stop:
                print(f"DRY RUN: would stop {instance_id} {name}")

    except (BotoCoreError, ClientError) as e:
        logging.error(e)
        sys.exit(2)

if __name__ == "__main__":
    sys.exit(main())
