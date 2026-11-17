# aws-ops-scripts

## stop_unowned.py

This script looks for running EC2 instances that don't have an `Owner` tag and
stops them. The idea is that if nobody owns an instance, nobody's really keeping
an eye on what it costs, so it's a good candidate to shut off.

I mostly wanted to build something that's safe to point at a real account, so by
default it doesn't change anything. You have to explicitly tell it to stop
instances before it'll actually do it.

### Running it

    ./stop_unowned.py                 # dry run, shows what it would stop
    ./stop_unowned.py --apply         # stops them after you type "yes"
    ./stop_unowned.py --apply --yes --expected-account 111111111111   # for scheduled runs

| Flag | What it does |
|---|---|
| `--region` | The region to check, `us-east-1` by default |
| `--apply` | Actually stops the instances instead of doing a dry run |
| `--yes` | Skips the confirmation prompt, for things like cron where nobody's there to type |
| `--expected-account` | Makes the script refuse to run if you're in a different account than you meant to be |

### How it stays safe

If you run it with no flags, it just prints what it would stop, so forgetting a
flag can't hurt anything. Before it does anything, it prints the account and
identity it's running as, and if you pass `--expected-account` and it doesn't
match, it exits before making any EC2 calls. I added that one for the case where
you think you're in dev but your shell is still pointed at prod.

When you do use `--apply`, it shows you the list of instances first and waits for
you to type "yes". It then stops everything in a single `StopInstances` call and
only prints "Stopped" once that call has actually gone through. It also filters
for running instances on the AWS side and pages through the results, so it works
fine on accounts with a lot of instances.

### Permissions

It only needs `sts:GetCallerIdentity`, `ec2:DescribeInstances`, and
`ec2:StopInstances`.

### Exit codes

It exits `0` when everything went fine, which includes dry runs, having nothing
to stop, or saying no at the prompt. It exits `2` when it couldn't run, like a
wrong account, bad credentials, or an AWS error.

### Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

I tested it against my own account with a dry run, a wrong account, saying no at
the prompt, and a real `--apply --yes` run.
