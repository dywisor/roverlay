#!/bin/sh
# -*- coding: utf-8 -*-
# roverlay hook that pushes the git history to a remote
#
#  It's expected that git-commit-overlay is run before this hook.
#
set -u

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root

# using line_iterator() from itertools
$lf git itertools

qwhich "${GIT}" || die_cannot_run "git is not available."


## functions

# void git_push_to_remote (
#    remote, *refspec, **__GIT_PUSH_SUCCESS!, **GIT_PUSH_ARGS
# )
#
#  Runs "git push" for the given remote and sets __GIT_PUSH_SUCCESS to 'n'
#  if errors occured.
#
git_push_to_remote() {
   if run_command_logged ${GIT} push ${GIT_PUSH_ARGS-} "$@"; then
      veinfo "successfully pushed changes to ${1}"
   else
      __GIT_PUSH_SUCCESS=n
      eerror "could not push changes to ${1}"
   fi
   return 0
}

# int git_push_to_remotes ( **GIT_REMOTES, **GIT_DEFAULT_REMOTE )
#
#  Calls git_push_to_remote() for each remote in GIT_REMOTES.
#  Returns EX_GIT_PUSH_ERR if pushing failed for at least one remote,
#  else 0.
#
git_push_to_remotes() {
   [ -n "${GIT_REMOTES-}" ] || \
      local GIT_REMOTES="${GIT_DEFAULT_REMOTE:-origin} master"
   # or "<remote> :"

   local __GIT_PUSH_SUCCESS=y

   F_ITER=git_push_to_remote \
   F_ITER_ON_ERROR=return \
   ITER_SKIP_EMTY=y \
   ITER_UNPACK_ITEM=y \
   line_iterator "${GIT_REMOTES}"

   if [ "${__GIT_PUSH_SUCCESS}" = "y" ]; then
      return 0
   else
      # don't return non-zero due to "git push" errors
      #  this would cause roverlay to abort
      #return ${EX_GIT_PUSH_ERR}
      return 0
   fi
}


## main

if sync_allowed "${this}"; then
   git_push_to_remotes
fi
