#!/bin/sh
# -*- coding: utf-8 -*-
# roverlay hook that maintains (creates) a git history of the overlay
#
# What this script does:
#
# * check whether the git repo exists, else create it
# * check whether a clean commit can be made, that is (a) there are changes
#   to commit and (b) the git index does not contain uncommitted changes
# * then, add/commit changes
#
set -u

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root

## load git helper functions
$lf git
#autodie qwhich ${GIT}

## "config" for this script
# FIXME/TODO: remove config here?
GIT_COMMIT_AUTHOR='undef undef@undef.org'
GIT_COMMIT_MESSAGE='roverlay updates'


## other vars
EX_ADD_ERR=2
EX_COMMIT_ERR=3


## functions

# void git_try_rollback()
#
#  Trap function that tries to reset the git tree/index.
#
git_try_rollback() {
   # release trap
   trap - INT TERM EXIT
   run_command_logged ${GIT} reset --mixed --quiet || true
}

# int git_create_snapshot()
#
#  Adds changes and creates a commit.
#
git_create_snapshot() {
   trap git_try_rollback INT TERM EXIT

   # add changes
   #  --all: add changed, new and deleted files
   if ! run_command_logged ${GIT} add --all; then
      git_try_rollback
      return ${EX_ADD_ERR}
   fi

   # commit
   # FIXME:
   #  --author=?
   #  --file=? or --message=?
   if run_command_logged \
      ${GIT} commit --quiet --no-edit \
      --message="${GIT_COMMIT_MESSAGE}" --author="${GIT_COMMIT_AUTHOR}"
   then
      trap - INT TERM EXIT
      return 0
   else
      git_try_rollback
      return ${EX_COMMIT_ERR}
   fi
}


## main

# $GIT_DIR, $S/.git, $HOME/.git, ...?
if [ -d "${S}/.git" ]; then
   true
if [ ! -e "${S}/.git" ]; then
   einfo "Creating git repo"
   # FIXME: --shared OK?
   autodie ${GIT} init --quiet --shared=group "${S}"
else
   die "'${S}/.git should be a directory."
fi


if git_has_changes; then

   autodie git_create_snapshot

   ##push changes to local repo?
   ##
   ##if ! yesno ${NOSYNC}; then
   ##   #push changes to remote?
   ##fi

else
   veinfo "${SCRIPT_NAME}: nothing to do."
   exit 0
fi
