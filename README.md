# aws-ops-scripts

Some Python + boto3 scripts I use to clean up AWS accounts. The whole idea is that
they're safe to point at a real account. They won't touch anything unless you
actually tell them to.

| Tool                         | What it does                                                             |
|------------------------------|--------------------------------------------------------------------------|
| [ec2/stop_unowned.py](ec2/)  | Stops running EC2 instances nobody's claimed with an `Owner` tag         |
| [ebs/old_snapshots.py](ebs/) | Finds old EBS snapshots across one or more regions and can clean them up |

## How they work

Both scripts play by the same rules:

- Dry run by default. Nothing happens until you add `--apply`.
- `--apply` won't go without `--expected-account`, so you can't wreck the wrong account by accident.
- They ask before changing anything. `--yes` skips that for stuff like cron.
- They log which account they're running as, with timestamps.
- Credentials come from your profile or role, never hardcoded.
- They page through everything, so big accounts are no big deal.
- Exit codes: `0` is good, `2` means it couldn't run or something broke. `old_snapshots.py` also exits `1` when it finds
  old snapshots, so a scheduler can pick that up.

## Testing

Tests fake AWS with `moto`, so they don't need a real account and can't mess
anything up. GitHub Actions runs them on every PR, and nothing lands in `main`
without a PR and green tests.

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Want to run the tests too?

    pip install -r requirements-dev.txt
    pytest

Each folder has its own README if you want the details.
