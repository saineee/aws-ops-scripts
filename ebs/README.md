# old_snapshots.py

Finds EBS snapshots older than a certain number of days, 30 by default, and can
delete them. Old snapshots are easy to forget about and they quietly keep costing
money.

By default, it's just a check. It lists each old snapshot with its volume, age, and
size, plus a total at the end. It only looks at snapshots your account owns.

Tag a snapshot `Retain=true` and the script leaves it alone. The value isn't
picky about case or extra spaces, so `True` or ` TRUE ` work too. If a snapshot is
still being used by an AMI, AWS won't let it be deleted, so the script logs a
warning, skips it, and keeps going with the rest.

## Running it

    ./old_snapshots.py                                                # check, older than 30 days
    ./old_snapshots.py --days 90                                      # older than 90 days
    ./old_snapshots.py --apply --expected-account 111111111111        # asks before deleting
    ./old_snapshots.py --apply --expected-account 111111111111 --yes  # unattended runs

| Flag                 | What it does                                                     |
|----------------------|------------------------------------------------------------------|
| `--region`           | Region to check, `us-east-1` by default                          |
| `--days`             | Age cutoff in days, 30 by default                                |
| `--apply`            | Actually deletes them. Requires `--expected-account`.            |
| `--expected-account` | Refuses to run if your credentials point at a different account  |
| `--yes`              | Skips the confirmation prompt for cron and other unattended runs |

## Exit codes

As a check, it exits `1` when it finds old snapshots and `0` when it doesn't. With
`--apply`, it exits `0` if everything got deleted and `2` if anything was skipped
or failed, so a scheduler knows something still needs a look.

## Permissions

`sts:GetCallerIdentity`, `ec2:DescribeSnapshots`, `ec2:DeleteSnapshot`

## Testing

The tests run against a fake AWS using `moto`, so they don't need a real account
or credentials, and they can't touch anything real. Run them from the repo root:

    pip install -r requirements-dev.txt
    pytest

They check that old snapshots get found, that `Retain` protects a snapshot (even
with messy casing) while untagged ones still get picked up, that newer snapshots
are left alone, and that deleting actually removes the snapshot.
