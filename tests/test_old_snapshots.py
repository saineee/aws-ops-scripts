from ebs.old_snapshots import find_old_snapshots, delete_snapshots
from moto import mock_aws
from datetime import datetime, timedelta, timezone
import boto3


@mock_aws
def test_find_old_snapshots_over_1_day():
    ec2 = boto3.client("ec2")
    vol = ec2.create_volume(AvailabilityZone=f"{ec2.meta.region_name}a", Size=1)
    snap = ec2.create_snapshot(VolumeId=vol["VolumeId"])

    snap_id = snap["SnapshotId"]
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=1)
    found = find_old_snapshots(ec2, cutoff)

    assert len(found) == 1
    assert found[0]["SnapshotId"] == snap_id


@mock_aws
def test_retain_protects_from_find_old_snapshots():
    ec2 = boto3.client("ec2")
    vol = ec2.create_volume(AvailabilityZone=f"{ec2.meta.region_name}a", Size=1)

    ec2.create_snapshot(VolumeId=vol["VolumeId"],
                        TagSpecifications=[
                            {"ResourceType": "snapshot", "Tags": [{"Key": "Retain", "Value": "true"}]}])

    ec2.create_snapshot(VolumeId=vol["VolumeId"]
                        , TagSpecifications=[
            {"ResourceType": "snapshot", "Tags": [{"Key": "Retain", "Value": " TRue  "}]}])

    snap = ec2.create_snapshot(VolumeId=vol["VolumeId"])
    snap_id = snap["SnapshotId"]

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=1)
    found = find_old_snapshots(ec2, cutoff)

    assert len(found) == 1
    assert found[0]["SnapshotId"] == snap_id
