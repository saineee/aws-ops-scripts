#!/usr/bin/env python3


import logging
import argparse
import boto3
import sys
from botocore.exceptions import BotoCoreError, ClientError
from datetime import timezone, timedelta, datetime


def parse_args():
    parser = argparse.ArgumentParser(
        description="Script to find EBS Snapshots older than N days (default 30), in N region (default us-east-1).")

    parser.add_argument("--regions", nargs="+", default=["us-east-1"], help="aws region to search")
    parser.add_argument("--days", default=30, type=int, help="look for ebs snapshots older than this value")
    parser.add_argument("--apply", action="store_true", help="Non dry-run: delete snapshots")
    parser.add_argument("--expected-account", help="expected account that you intend to run this against")
    parser.add_argument("--yes", action="store_true",
                        help="intended for force apply during unattended runs e.g. cron jobs")

    args = parser.parse_args()

    if args.apply and args.expected_account is None:
        parser.error("when using --apply, you must use --expected-account")

    if args.days < 0:
        parser.error("--days must be a non-negative integer")

    return args


def check_account(sts, expected):
    sts_res = sts.get_caller_identity()
    acc = sts_res["Account"]
    arn = sts_res["Arn"]

    if expected and expected != acc:
        logging.error(f"expected account: {expected} does not match actual account: {acc}")
        sys.exit(2)

    logging.info(f"running script as {arn}")


def find_old_snapshots(ec2, cutoff):
    old_snapshots = []
    region = ec2.meta.region_name

    paginator = ec2.get_paginator("describe_snapshots")

    logging.info(f"searching {region}...")

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page["Snapshots"]:
            tags = {tag["Key"]: tag["Value"] for tag in snapshot.get("Tags", [])}

            if tags.get("Retain", "").lower().strip() == "true":
                continue

            creation = snapshot["StartTime"]

            if creation < cutoff:
                old_snapshots.append(snapshot)

    return old_snapshots


def confirm(yes):
    if yes:
        return
    try:
        confirmation = input("This action will remove the selected snapshots. 'yes' to confirm. ")

        if confirmation != "yes":
            logging.warning("aborting...")
            sys.exit(0)

    except EOFError:
        logging.error("\nuse --yes when running this script for unattended runs")
        sys.exit(2)


def delete_snapshots(ec2, snapshots):
    failed = 0
    deleted = 0

    for snap in snapshots:
        snap_id = snap["SnapshotId"]
        try:
            logging.info(f"requesting deletion for {snap_id}")
            ec2.delete_snapshot(SnapshotId=snap_id)
            logging.info(f"{snap_id} - deleted")
            deleted += 1

        except ClientError as e:
            failed += 1
            if e.response["Error"]["Code"] == "InvalidSnapshot.InUse":
                logging.warning(e.response["Error"]["Message"])
            else:
                logging.error(e.response["Error"]["Message"])

    return deleted, failed


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.getLogger("botocore").setLevel(logging.WARNING)

    args = parse_args()

    count = 0
    total_gb = 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)

    by_region = {}
    errors = []

    try:
        sts = boto3.client("sts")
        check_account(sts, args.expected_account)

        for region in args.regions:

            in_use = set()

            try:
                ec2 = boto3.client("ec2", region_name=region)
                old = find_old_snapshots(ec2, cutoff)

                if not old:
                    logging.warning(f"({ec2.meta.region_name}) - no snapshots found older than {args.days} days")
                    continue

                paginator = ec2.get_paginator("describe_images")
                for page in paginator.paginate(Owners=["self"]):
                    for image in page["Images"]:
                        for mapping in image["BlockDeviceMappings"]:
                            if mapping.get("Ebs", {}).get("SnapshotId"):
                                in_use.add(mapping["Ebs"]["SnapshotId"])

                to_delete = [snap for snap in old if snap["SnapshotId"] not in in_use]

                skipped = [snap for snap in old if snap["SnapshotId"] in in_use]

                for snap in skipped:
                    logging.warning(f"({ec2.meta.region_name}) - {snap['SnapshotId']} - in use")

                if not to_delete:
                    logging.warning(f"({ec2.meta_region_name}) - nothing eligible to delete")
                    continue

                for snap in to_delete:
                    creation = snap["StartTime"]
                    delta = (now - creation).days
                    print(
                        f"({ec2.meta.region_name}) - {snap['SnapshotId']} - {snap.get('VolumeId', 'N/A')} - {delta} days old - {snap['VolumeSize']} GB")
                    count += 1
                    total_gb += snap["VolumeSize"]

                by_region[region] = to_delete
            except (BotoCoreError, ClientError) as e:
                errors.append((region, e))
                continue

        if count:
            logging.info(f"{count} snapshots - {total_gb} total GBs")

        if errors:
            for region, error in errors:
                logging.error(f"{region} - {error}")
            sys.exit(2)

        if not count:
            logging.warning("no snapshots found.")
            sys.exit(0)

        if not args.apply:
            sys.exit(1)

        confirm(args.yes)

        total_deleted = 0
        total_failed = 0

        for region, snaps in by_region.items():

            if not snaps:
                continue

            ec2 = boto3.client("ec2", region_name=region)

            deleted, failed = delete_snapshots(ec2, snaps)
            total_deleted += deleted
            total_failed += failed

        logging.info(f"deleted {total_deleted} - failed {total_failed}")

        if total_failed:
            sys.exit(2)
        else:
            sys.exit(0)

    except (BotoCoreError, ClientError) as e:
        logging.error(e)
        sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())
