#!/bin/bash

# returns info regarding the current workspace https://docs.bazel.build/versions/main/user-manual.html#workspace_status
# these values can then be accessed inside of Bazel.
# WARNING! use the STABLE_ values only if you absolutely can't access the information
# from anywhere else as they might change rapidly, degrading cache performance for any actions
# that depend on them

# ANY STABLE KEY CHANGE HERE WILL INVALIDATE ALL GENRULES THAT READ FROM EITHER volatile-status.txt OR
# stable-status.txt
GIT_COMMIT=$(git rev-parse HEAD)
REMOTE_ORIGIN=$(git config --get remote.origin.url)

echo "GIT_COMMIT ${GIT_COMMIT}"
echo "REMOTE_ORIGIN ${REMOTE_ORIGIN}"

git diff-index --quiet HEAD --
if [[ $? == 0 ]]; then
  status="clean"
else
  status="modified"
fi

echo BUILD_SCM_BRANCH ${BUILDKITE_BRANCH}
echo BUILD_SCM_REVISION ${GIT_COMMIT}
echo BUILD_SCM_STATUS ${status}
echo BUILD_SCM_REMOTE ${REMOTE_ORIGIN}
