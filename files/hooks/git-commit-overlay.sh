#!/bin/sh
# -*- coding: utf-8 -*-
# roverlay hook that maintains (creates) a git history of the overlay
#
# What this script does:
#
# * check whether the git repo exists, else create it
# * check whether a clean commit can be made, that is (a) there are changes
#   to commit and (b) the git index does not contain uncommitted changes
# * then, add changes, create a commit message and finally commit
#
set -u

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root

## load git helper functions
$lf git
#autodie qwhich ${GIT}


## functions

# void git_try_rollback()
#
#  Trap function that tries to reset the git tree/index.
#
git_try_rollback() {
   # release trap
   trap - INT TERM EXIT
   run_command_logged ${GIT} reset --mixed --quiet || true
   if [ -n "${COMMIT_MSG_FILE-}" ]; then
      rm -f "${COMMIT_MSG_FILE}"
   fi
}

# int git_commit ( **GIT_COMMIT_MESSAGE, **GIT_COMMIT_MAX_LINE_WIDTH )
#
#  Adds changes and creates a commit.
#
git_commit() {
   local f="${T}/git_commit_message_$$"
   local COMMIT_MSG_FILE
   trap git_try_rollback INT TERM EXIT

   # add changes
   #  --all: add changed, new and deleted files
   if ! run_command_logged ${GIT} add --all; then
      git_try_rollback
      return ${EX_GIT_ADD_ERR}
   fi

   # create a commit message (file)
   {
      echo "${GIT_COMMIT_MESSAGE:-roverlay updates}" && \
      echo && \
      ${GIT} status \
         --porcelain --untracked-files=no --ignore-submodules | \
            sed -n -e 's,^[MADRC].[[:blank:]]\(.*\)\/..*[.]ebuild$,\1,p' | \
               sort -u | xargs echo | \
               fold -s -w ${GIT_COMMIT_MAX_LINE_WIDTH:-79}
   } > "${f}" || die
   COMMIT_MSG_FILE="${f}"

   # commit
   if run_command_logged \
      ${GIT} commit --quiet --no-edit \
         --file "${COMMIT_MSG_FILE}" ## --author="${GIT_COMMIT_AUTHOR}"
   then
      rm "${COMMIT_MSG_FILE-}" && COMMIT_MSG_FILE=
      trap - INT TERM EXIT
      return 0
   else
      git_try_rollback
      return ${EX_GIT_COMMIT_ERR}
   fi
}

# void git_reinit (
#    **GIT_REPO_USER_NAME, **GIT_REPO_USER_EMAIL, **GIT_DEFAULT_REMOTE
# ), raises die()
#
#  Configures the git repo.
#
git_reinit() {
   # update git config
   git_update_config "user.name" "${GIT_REPO_USER_NAME-}" "roverlay"
   git_update_config \
      "user.email" "${GIT_REPO_USER_EMAIL-}" "roverlay@undef.org"
   git_update_config "push.default" "" "matching"

   # add default remote
   if [ -n "${GIT_DEFAULT_REMOTE-}" ] && ! git remote | grep -q .; then
      autodie ${GIT} remote add origin "${GIT_DEFAULT_REMOTE}"
   fi
}


## main

# $GIT_DIR, $S/.git, $HOME/.git, ...?
if [ ! -e "${S}/.git" ]; then
   einfo "Creating git repo"
   # FIXME: --shared OK?
   autodie ${GIT} init --quiet --shared=group "${S}"

   # assume that there are changes,
   #  git_has_changes() does not work for new repos
elif ! git_has_changes; then
   veinfo "${SCRIPT_NAME}: nothing to do."
   return 0
fi

autodie git_reinit
autodie git_commit
