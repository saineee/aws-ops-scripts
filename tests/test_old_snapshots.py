from ebs.old_snapshots import find_old_snapshots, delete_snapshots, main
from moto import mock_aws
from datetime import datetime, timedelta, timezone
import boto3
import sys
import pytest


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


@mock_aws
def test_new_snapshot_not_found():
    ec2 = boto3.client("ec2")

    vol = ec2.create_volume(AvailabilityZone=f"{ec2.meta.region_name}a", Size=1)
    ec2.create_snapshot(VolumeId=vol["VolumeId"])

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    found = find_old_snapshots(ec2, cutoff)

    assert len(found) == 0


@mock_aws
def test_delete_snapshots_delete_old_snapshot():
    ec2 = boto3.client("ec2")

    vol = ec2.create_volume(AvailabilityZone=f"{ec2.meta.region_name}a", Size=1)
    snap = ec2.create_snapshot(VolumeId=vol["VolumeId"])

    deleted, failed = delete_snapshots(ec2, [snap])

    assert deleted == 1
    assert failed == 0

    desc = ec2.describe_snapshots(OwnerIds=["self"])
    assert len(desc["Snapshots"]) == 0


@mock_aws
def test_main_skips_ami_backed_snapshot(monkeypatch):
    ec2 = boto3.client("ec2")
    region = ec2.meta.region_name

    vol = ec2.create_volume(AvailabilityZone=f"{region}a", Size=1)

    base = ec2.create_snapshot(VolumeId=vol["VolumeId"])
    base_id = base["SnapshotId"]

    plain = ec2.create_snapshot(VolumeId=vol["VolumeId"])
    plain_id = plain["SnapshotId"]

    ami = ec2.register_image(
        Name="test-ami",
        RootDeviceName="/dev/xvda",
        BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"SnapshotId": base_id}}],
    )

    res = ec2.describe_images(ImageIds=[ami["ImageId"]])
    image = res["Images"][0]
    in_use_id = image["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]

    monkeypatch.setattr(sys, "argv", [
        "old_snapshots.py", "--regions", region, "--days", "0",
        "--apply", "--expected-account", "123456789012", "--yes",
    ])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0

    res = ec2.describe_snapshots(OwnerIds=["self"])
    remaining = {snap["SnapshotId"] for snap in res["Snapshots"]}

    assert in_use_id in remaining
    assert plain_id not in remaining


@mock_aws
def test_main_all_ami_backed_snapshots(monkeypatch):
    ec2 = boto3.client("ec2")
    region = ec2.meta.region_name

    vol = ec2.create_volume(AvailabilityZone=f"{region}a", Size=1)

    base = ec2.create_snapshot(VolumeId=vol["VolumeId"])
    base_id = base["SnapshotId"]

    ami = ec2.register_image(
        Name="test-ami",
        RootDeviceName="/dev/xvda",
        BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"SnapshotId": base_id}}],
    )

    ec2.delete_snapshot(SnapshotId=base_id)

    ami_check = ec2.describe_snapshots(OwnerIds=["self"])

    assert len(ami_check["Snapshots"]) == 1

    res = ec2.describe_images(ImageIds=[ami["ImageId"]])
    image = res["Images"][0]
    in_use_id = image["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]

    assert ami_check["Snapshots"][0]["SnapshotId"] == in_use_id

    monkeypatch.setattr(sys, "argv", [
        "old_snapshots.py", "--regions", region, "--days", "0",
        "--apply", "--expected-account", "123456789012", "--yes",
    ])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0

    after = ec2.describe_snapshots(OwnerIds=["self"])["Snapshots"]
    assert len(after) == 1
    assert after[0]["SnapshotId"] == in_use_id

@mock_aws
def test_wrong_account_attempt_delete(monkeypatch):
    ec2 = boto3.client("ec2")
    region = ec2.meta.region_name

    vol = ec2.create_volume(AvailabilityZone=f"{region}a", Size=1)

    snap = ec2.create_snapshot(VolumeId=vol["VolumeId"])
    snap_id = snap["SnapshotId"]

    monkeypatch.setattr(sys, "argv", [
        "old_snapshots.py", "--regions", region, "--days", "0",
        "--apply", "--expected-account", "111111111111", "--yes",
    ])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2

    after = ec2.describe_snapshots(OwnerIds=["self"])["Snapshots"]
    assert len(after) == 1
    assert after[0]["SnapshotId"] == snap_id
