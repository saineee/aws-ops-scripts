# stop_unowned.py

Stops running EC2 instances that nobody owns. If an instance doesn't have an
owner, nobody's watching what it costs, so it's pretty much the first thing worth
shutting off.

"Unowned" means the `Owner` tag is missing, empty, or just spaces. Anything in an
Auto Scaling group gets skipped, since the group would just spin a new one right
back up.

## Running it

    ./stop_unowned.py                                                 # dry run
    ./stop_unowned.py --apply --expected-account 111111111111         # asks first
    ./stop_unowned.py --apply --expected-account 111111111111 --yes   # unattended

| Flag | What it does |
|---|---|
| `--region` | Which region to check, `us-east-1` by default |
| `--apply` | Actually stops them. Needs `--expected-account`. |
| `--expected-account` | Bails if your creds point at a different account |
| `--yes` | Skips the "you sure?" prompt, for cron or anything unattended |

It stops everything in one call and logs each state change straight from AWS,
like `running -> stopping`, so you can see exactly what happened.

## Permissions

`sts:GetCallerIdentity`, `ec2:DescribeInstances`, `ec2:StopInstances`
