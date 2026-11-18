# aws-ops-scripts

## stop_unowned.py

This script looks for running EC2 instances that don't have an `Owner` tag and
stops them. The idea is that if nobody owns an instance, nobody's really keeping
an eye on what it costs, so it's a good candidate to shut off.

I mostly wanted to build something that's safe to point at a real account, so by
default it doesn't change anything. You have to explicitly tell it to stop
instances, and tell it which account you mean, before it'll actually do it.

### Running it

    ./stop_unowned.py                                                 # dry run, shows what it would stop
    ./stop_unowned.py --apply --expected-account 111111111111         # stops them after you type "yes"
    ./stop_unowned.py --apply --expected-account 111111111111 --yes   # for unattended runs like cron

| Flag | What it does |
|---|---|
| `--region` | The region to check, `us-east-1` by default |
| `--apply` | Actually stops the instances instead of doing a dry run. Requires `--expected-account`. |
| `--expected-account` | The account you mean to run against. The script refuses to run if your credentials point anywhere else. |
| `--yes` | Skips the confirmation prompt, for unattended runs where nobody's there to type |

### What counts as unowned

An instance gets stopped if it's running and either has no `Owner` tag or has an
`Owner` tag with an empty value. The tag key check is case-sensitive, so `owner`
in lowercase doesn't count, since that's how AWS treats tag keys too. It also
skips anything in an Auto Scaling group, because stopping those just makes the
group replace them.

### How it stays safe

If you run it with no flags, it just prints what it would stop, so forgetting a
flag can't hurt anything. Before it does anything, it logs the account and
identity it's running as. Any run with `--apply` has to name the account it's
meant for with `--expected-account`, and if that doesn't match, it exits before
making any EC2 calls. I added that one for the case where you think you're in
dev but your shell is still pointed at prod.

When you do use `--apply`, it lists the instances first and waits for you to
type "yes". If there's no terminal to type into, like under cron without
`--yes`, it exits with a clear error instead of crashing. It then sends a single
batched `StopInstances` call and logs each instance's state change straight from
AWS's response, like `running -> stopping`, so the log shows what actually
changed.

Everything it does is logged with a timestamp and a level, and the EC2 client
uses extra retries so it holds up if AWS starts throttling on a big account. It
also filters for running instances on the AWS side and pages through the
results.

### Permissions

It only needs `sts:GetCallerIdentity`, `ec2:DescribeInstances`, and
`ec2:StopInstances`.

### Exit codes

It exits `0` when everything went fine, which includes dry runs, having nothing
to stop, or saying no at the prompt. It exits `2` when it couldn't run, like a
wrong account, a missing `--expected-account`, no terminal for the prompt, bad
credentials, or an AWS error.

### Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

I tested it against my own account with a dry run, a wrong account, saying no at
the prompt, a cron-style run with no terminal, and a real `--apply --yes` run.
