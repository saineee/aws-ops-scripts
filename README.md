# aws-ops-scripts

Python and boto3 scripts for routine AWS cleanup work. I built these to be safe to
point at a real account, so they don't change anything unless you explicitly tell
them to.

| Tool | What it does |
|---|---|
| [ec2/stop_unowned.py](ec2/) | Stops running EC2 instances with no `Owner` tag |
| [ebs/old_snapshots.py](ebs/) | Finds old EBS snapshots and can clean them up |

## How they all work

- Dry run by default. Nothing changes without `--apply`.
- `--apply` requires `--expected-account`, so you can't change things in the wrong account by accident.
- They ask for confirmation before acting, and `--yes` skips that for unattended runs.
- They log the account they're running as, with timestamps on everything.
- Credentials come from the normal boto3 chain, a profile or a role. No keys in the code.
- List calls use paginators, so big accounts are fine.
- Exit codes: `0` ok, `1` a check found something, `2` couldn't run or something failed.

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Each folder has its own README with the details.
