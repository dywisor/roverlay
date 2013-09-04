#!/bin/sh
# -*- coding: utf-8 -*-
# R overlay -- shell functions, list iterators
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
#
#
# --- functions provided by this file ---
#
# void generic_iterator (
#    item_separator, *words,
#    **F_ITER=echo, **ITER_SKIP_EMPTY=y, **ITER_UNPACK_ITEM=n,
#    **F_ITER_ON_ERROR=return
# )
# @iterator line_iterator ( *lines )
#
# --- variables provided by this file ---
#
# @private __HAVE_ITERTOOLS_FUNCTIONS__
#
# --- END HEADER ---

if [ -z "${__HAVE_ITERTOOLS_FUNCTIONS__-}" ]; then
readonly __HAVE_ITERTOOLS_FUNCTIONS__=y


# void generic_iterator (
#    item_separator, *words,
#    **F_ITER=echo, **ITER_SKIP_EMPTY=y, **ITER_UNPACK_ITEM=n,
#    **F_ITER_ON_ERROR=return
# )
# DEFINES @iterator <item_separator> <iterator_name>
#
#  Iterates over a list of items separated by item_separator.
#  All words are interpreted as "one big list".
#
#  Calls F_ITER ( item ) for each item and F_ITER_ON_ERROR() if F_ITER
#  returns a non-zero value.
#  The items will be unpacked if ITER_UNPACK_ITEM is set to 'y',
#  otherwise the item is interpreted as one word (default 'n').
#
#  Empty items will be ignored if ITER_SKIP_EMPTY is set to 'y', which
#  is the default behavior.
#
#  Examples: see the specific iterator function(s) below.
#
generic_iterator() {
   : ${IFS_DEFAULT?}
   local IFS="${1?}"
   shift
   set -- $*
   IFS="${IFS_DEFAULT}"
   local item
   for item; do
      if [ -z "${item}" ] && [ "${ITER_SKIP_EMPTY:-y}" = "y" ]; then
         true
      elif [ "${ITER_UNPACK_ITEM:-n}" = "y" ]; then
         ${F_ITER:-echo} ${item}   || ${F_ITER_ON_ERROR:-return}
      else
         ${F_ITER:-echo} "${item}" || ${F_ITER_ON_ERROR:-return}
      fi
   done
   return 0
}

# @iterator <newline> line_iterator
line_iterator() {
   generic_iterator "${IFS_NEWLINE?}" "$@"
}

fi # __HAVE_ITERTOOLS_FUNCTIONS__
