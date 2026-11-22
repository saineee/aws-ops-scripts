# stop_unowned.py

Stops running EC2 instances that don't have an owner. If nobody owns an instance,
nobody's watching what it costs, so it's a good candidate to shut off.

An instance counts as unowned if its `Owner` tag is missing, empty, or just
whitespace. Anything in an Auto Scaling group gets skipped, since the group would
just replace it.

## Running it

    ./stop_unowned.py                                                 # dry run
    ./stop_unowned.py --apply --expected-account 111111111111         # asks before stopping
    ./stop_unowned.py --apply --expected-account 111111111111 --yes   # unattended runs

| Flag                 | What it does                                                     |
|----------------------|------------------------------------------------------------------|
| `--region`           | Region to check, `us-east-1` by default                          |
| `--apply`            | Actually stops them. Requires `--expected-account`.              |
| `--expected-account` | Refuses to run if your credentials point at a different account  |
| `--yes`              | Skips the confirmation prompt for cron and other unattended runs |

It sends one batched stop request and logs each instance's state change straight
from AWS, like `running -> stopping`.

## Permissions

`sts:GetCallerIdentity`, `ec2:DescribeInstances`, `ec2:StopInstances`
