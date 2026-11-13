#!/usr/bin/env python3
"""Prepare the group Hub's local test-account hashes without storing passwords."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import tempfile

from shared_sandbox import load_group
from test_passwords import PASSWORD_HASH, hash_password


def update_accounts(approved, saved, rotate, prompt):
    if not rotate <= approved:
        raise ValueError("each --rotate account must be in the approved group roster")
    accounts = {member: saved[member] for member in approved - rotate if member in saved}
    if not all(isinstance(value, str) and PASSWORD_HASH.fullmatch(value) for value in accounts.values()):
        raise ValueError("existing hash file contains an invalid hash; rotate that account")
    for member in sorted(approved - accounts.keys()):
        password = prompt(f"Test password for {member}: ")
        if password != prompt(f"Repeat password for {member}: "):
            raise ValueError(f"passwords did not match for {member}")
        accounts[member] = hash_password(password)
    return accounts


def write_accounts(path, accounts):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".test-accounts-", delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(accounts, output, indent=2, sort_keys=True)
            output.write("\n")
            output.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rotate", action="append", default=[], metavar="ACCOUNT")
    args = parser.parse_args()
    settings = load_group(args.group_json)
    approved = {member for task in settings["tasks"].values() for member in task["members"]}
    saved = json.loads(args.output.read_text()) if args.output.exists() else {}
    if not isinstance(saved, dict):
        raise ValueError("existing test-account file must contain a JSON object")
    rotate = set(args.rotate)
    if (approved - saved.keys() or rotate) and not sys.stdin.isatty():
        raise ValueError("open an interactive terminal to enter test passwords without echo")
    accounts = update_accounts(approved, saved, rotate, getpass.getpass)
    write_accounts(args.output, accounts)
    print(f"Prepared password hashes for {len(accounts)} approved accounts")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
