#!/bin/sh
# -*- coding: utf-8 -*-
# R overlay -- shell functions, git
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
#
#
# --- functions provided by this file ---
#
# int  git_has_changes ( [*files] ), raises die()
# void git_update_config ( config_key, [user_value], [fallback_value] ),
#  raises die()
#
#
# --- variables provided by this file ---
#
# GIT
# @private __GIT_DIFF_OPTS
#
# @private __HAVE_GIT_FUNCTIONS__
#
#
# --- END HEADER ---

if [ -z "${__HAVE_GIT_FUNCTIONS__-}" ]; then
readonly __HAVE_GIT_FUNCTIONS__=y

if [ -z "${GIT-}" ]; then
   GIT=$(which git 2>>${DEVNULL?})
   : ${GIT:=git}
fi

: ${__GIT_DIFF_OPTS=--no-ext-diff --quiet --ignore-submodules}


# int git_has_changes ( [*files] ), raises die()
#
# inspired by git-sh-setup.sh, require_clean_work_tree() from the git source
#
# Checks whether >the< git repo has unstaged changes. Also checks whether it
# has any uncommitted changes and dies if there are any (i.e., no clean commit
# possible).
#
# Returns 0 if there's anything to commit, else 1.
#
git_has_changes() {
   ${GIT} rev-parse --quiet --verify HEAD 1>>${DEVNULL} || \
      die "git rev-parse returned ${?}." ${?}
   #FIXME: return code if update-index?
   run_command_logged \
      ${GIT} update-index -q --ignore-submodules --refresh -- "$@"

   local has_changes
   if ! ${GIT} diff-files ${__GIT_DIFF_OPTS} "$@"; then
      ## return value of zero means no changes
      veinfo "git index: changes found"
      has_changes=0
   elif \
      [ -n "$( ${GIT} ls-files --exclude-standard -o -- $@ | head -n 1)" ]
   then
      # untracked files
      ## any better way to find them?
      veinfo "git index: changes found (untracked files)"
      has_changes=0
   else
      veinfo "git index: no changes found"
      has_changes=1
   fi

   if ${GIT} diff-index --cached ${__GIT_DIFF_OPTS} HEAD -- "$@"; then
      veinfo "git index: clean commit can be made."
   else
      die \
         "clean commit cannot be made - uncommitted changes staged for commit found."
   fi
   return ${has_changes}
}

# void git_update_config (
#    config_key, [user_value], [fallback_value]
# ), raises die()
#
# Sets config_key to user_value (if defined), else sets it to fallback_value
# if config_key's value is empty/does not exist.
#
#
git_update_config() {
   if [ -n "${2-}" ]; then
      autodie ${GIT} config "${1}" "${2}"
   elif [ -z "${3-}" ] || ${GIT} config --get "${1}" | grep -q .; then
      true
   else
      autodie ${GIT} config "${1}" "${3?}"
   fi
}

fi # __HAVE_GIT_FUNCTIONS__
