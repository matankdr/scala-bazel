#!/usr/bin/env python3

from virtualmonorepo.processexec import run


def read_current_branch(directory=None, original_name=False):
    fail_message = "Failed to read the current git branch"
    if directory is None:
        branch = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                     fail_msg=fail_message)
    else:
        branch = run(
            ['git', '-C', directory, 'rev-parse', '--abbrev-ref', 'HEAD'],
            fail_msg=fail_message)

    result = branch.replace("/", "_")
    result = result.replace("\n", "")

    if original_name:
        return result
    else:
        return result.replace("/", "..")
