# R overlay -- package rule generators, addition control
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# converting addition-control lists (cmdline, from file...) to rule objects,
# hacky solution:
#
# ** step 1 -- collect category/package tokens, determine bitmask **
#
#  create a dict (
#     category_token|True => package_token|True => bitmask<policy>
#     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^    ^~~~~~~~~~~~~~^
#               "acceptor chain"                    "add-policy"
#  )
#
#   "True" means "accept all".
#
#   make sure that the tokens get de-duped
#    (normalize values, use tuples/namespace)
#
#
# ** step 2 -- expand category-wide bitmask, set effective package bitmask **
#
#  for each category with at least one non-True package_token loop
#    for each package in category loop
#       category->package |= category->True  [bitwise-OR]
#    end loop
#    (do not modify category->True, as it applies to packages not matched
#     by any package_token, too)
#  end loop
#
#  for each category loop
#     for each entry in category loop
#        reduce policy bitmask (keep effective bits only)
#     end loop
#  end loop
#
#  (merge the two for-loops in code)
#
#
# ** step 3 -- create reversed map **
#
#  BITMASK_MAP: create a dict (
#     effective_bitmask => category_token|True => set(package_token|True>)
#     ^~~~~~~~~~~~~~~~^    ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
#     "add-policy atom"                 "acceptor chain"
#  )
#
#
#  **hacky**:
#   It would be better to split effective_bitmask into its components
#   (2**k for k in ...), but this requires path compaction.
#   Not implemented. (graph/spanning-tree or logic minimization)
#
#
# ** step 4 -- naive path compaction **
#   (Keep in mind that acceptor tokens cannot be merged with match-all)
#
#   reduce acceptor chains (drop-superseeded):
#   for each effective_bitmask b in BITMASK_MAP loop
#      if BITMASK_MAP->b->True exists then
#         drop all other entries from BITMASK_MAP->b
#      else
#         for each category in BITMASK_MAP->b loop
#            if category->True exists then
#               drop all other entries from category
#            end if
#         end loop
#      end if
#   end loop
#
#   (optional: drop overlapping acceptor chains, e.g. regex ".*" is equal
#    to True and therefore all other entries in the regex' branch can be
#    removed)
#
#
#   merge-bitmask: (OPTIONAL / NOT IMPLEMENTED)
#    (bitwise-OR effective_bitmasks with identical acceptor chains)
#
#    *could* create a large table
#      <add-policy atom X category/package> => bool
#       (where category, package can also be "accept-all")
#
#
#    +-----------------+-------+-------+-----+-------+-------+-----+-------+
#    | add-policy atom | c0/p0 | c0/p1 | ... | c0/pM | c1/p0 | ... | cN/pJ |
#    +=================+=======+=======+=====+=======+=======+=====+=======+
#    | 2**0            | 0|1   | 0|1   | ... | 0|1   | 0|1   | ... | 0|1   |
#    +-----------------+-------+-------+-----+-------+-------+-----+-------+
#    | ...             | ...   | ...   | ... | ...   | ...   | ... | ...   |
#    +-----------------+-------+-------+-----+-------+-------+-----+-------+
#    | 2**k            | 0|1   | 0|1   | ... | 0|1   | 0|1   | ... | 0|1   |
#    +-----------------+-------+-------+-----+-------+-------+-----+-------+
#
#   ++ reduce table
#
#
# ** step 5 -- convert the acceptor chains to objects **
#
#   the final BITMASK_MAP can be easily translated to rule objects:
#
#   * the effective bitmask can be converted in one or more
#      PackageAdditionControl*Actions
#
#   * an OR<category OR<packages>> match statement
#      represents the acceptor chain
#      (reduce properly, e.g. "accept-all" entries)
#
#
# ** done **
#
