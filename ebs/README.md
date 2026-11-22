# old_snapshots.py

Finds EBS snapshots older than a certain number of days (30 by default) and can
delete them. Old snapshots are super easy to forget about, and they just keep
quietly costing money.

By default it's just a check. It lists each old snapshot with its volume, age, and
size, then a total at the end. It only looks at snapshots your account owns.

Tag a snapshot `Retain=true` and the script won't touch it. Casing and extra
spaces don't matter, so `True` or ` TRUE ` work too. If a snapshot's still being
used by an AMI, AWS won't let you delete it, so the script just logs a warning,
skips it, and moves on to the rest.

## Running it

    ./old_snapshots.py                                                # check, older than 30 days
    ./old_snapshots.py --days 90                                      # older than 90 days
    ./old_snapshots.py --apply --expected-account 111111111111        # asks first
    ./old_snapshots.py --apply --expected-account 111111111111 --yes  # unattended

| Flag | What it does |
|---|---|
| `--region` | Which region to check, `us-east-1` by default |
| `--days` | How old is "old", 30 days by default |
| `--apply` | Actually deletes them. Needs `--expected-account`. |
| `--expected-account` | Bails if your creds point at a different account |
| `--yes` | Skips the "you sure?" prompt, for cron or anything unattended |

## Exit codes

As a check, it exits `1` if it finds old snapshots and `0` if it doesn't. With
`--apply`, it's `0` if everything got deleted and `2` if anything got skipped or
failed, so a scheduler knows something still needs a look.

## Permissions

`sts:GetCallerIdentity`, `ec2:DescribeSnapshots`, `ec2:DeleteSnapshot`

## Testing

Tests fake AWS with `moto`, so no real account needed and nothing real gets
touched. Run them from the repo root:

    pip install -r requirements-dev.txt
    pytest

They make sure old snapshots get found, `Retain` actually protects (even with
weird casing) while untagged ones still get caught, newer snapshots get left
alone, and deleting one really gets rid of it.
