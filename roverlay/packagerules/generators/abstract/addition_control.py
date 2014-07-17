# R overlay -- abstract package rule generators, addition control
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.


import abc


import roverlay.packagerules.generators.abstract.base

import roverlay.packagerules.abstract.acceptors
import roverlay.packagerules.abstract.rules
import roverlay.packagerules.acceptors.trivial
import roverlay.packagerules.actions.addition_control


import roverlay.overlay.abccontrol
from roverlay.overlay.abccontrol import AdditionControlResult


# converting addition-control lists (cmdline, from file...) to rule objects,
# hacky solution:
#
# ** step 1 ** -- collect category/package tokens, determine bitmask
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
#    (normalize values, use tuples (or namespace))
#
#   Only the first and the last step need to know *what* category/package
#   tokens are. All intermediate steps should not need to care about this.
#

class AbstractAdditionControlPackageRuleGenerator (
   roverlay.packagerules.generators.abstract.base.AbstractPackageRuleGenerator
):
   """(Abstract) object that takes cmdline/files as input and creates
   add-policy package rules."""

   # Note that tokens are not totally abstract,
   #  the "match-all" (True) token is hardcoded

   #CategoryToken = collections.namedtuple ( 'CategoryToken', '<attr>*' )
   #PackageToken  = collections.namedtuple ( 'PackageToken',  '<attr>*' )

   @abc.abstractmethod
   def category_token_to_acceptor ( self, category_token, priority ):
      """Creates a package rule acceptor for the given category token.

      Returns: not-None acceptor (or nested acceptor)

      Must not return None.
      If a token is meaningless, then don't create it in the first place.

      arguments:
      * category_token -- a category token
      * priority       -- priority of the acceptor (int)
      """
      raise NotImplementedError()
   # --- end of category_token_to_acceptor (...) ---

   @abc.abstractmethod
   def package_token_to_acceptor ( self, package_token, priority ):
      """Creates a package rule acceptor for the given package token.

      Returns: not-None acceptor (or nested acceptor)

      arguments:
      * package_token -- a package token
      * priority      -- priority of the acceptor (int)
      """
      raise NotImplementedError()
   # --- end of package_token_to_acceptor (...) ---

   def create_package_rules ( self, reduced_bitmask_acceptor_chain_map ):
      """Creates a nested add-policy package rule object.
      The rule object's priority has to be set manually afterwards.

      Returns: (nested) package rule or None
      """
      # create_package_rules() is defined/implemented below (step 5)
      return create_package_rules (
         reduced_bitmask_acceptor_chain_map,
         convert_category_token_to_acceptor = self.category_token_to_acceptor,
         convert_package_token_to_acceptor  = self.package_token_to_acceptor
      )
   # --- end of create_package_rules (...) ---

   def create_new_bitmask_map ( self ):
      """Creates new, empty "acceptor chain" -> "bitmask" map.

      Returns: bitmask map

      arguments: none
      """
      return dict()
   # --- end of create_new_bitmask_map (...) ---

   def prepare_bitmask_map ( self, acceptor_chain_bitmask_map ):
      """Transforms the given "acceptor chain" -> "bitmask" map into the
      reduced "effective bitmask" -> "acceptor chain" map.

      Note: Involves in-place operations that modify
            acceptor_chain_bitmask_map.
            Pass a copy if the original map should remain unchanged.

      Returns: reduced/optimized "effective bitmask" -> "acceptor chain"

      arguments:
      * acceptor_chain_bitmask_map -- "acceptor chain" -> "bitmask" map
      """
      expand_acceptor_chain_bitmasks ( acceptor_chain_bitmask_map )

      bitmask_acceptor_chain_map = (
         create_bitmask_acceptor_chain_map ( acceptor_chain_bitmask_map )
      )

      reduce_bitmask_acceptor_chain_map ( bitmask_acceptor_chain_map )

      return bitmask_acceptor_chain_map
   # --- end of prepare_bitmask_map (...) ---

   def compile_bitmask_map ( self, acceptor_chain_bitmask_map ):
      """Transforms the given "acceptor chain" -> "bitmask" map into a
      (nested) package rule.

      This is equal to calling
         obj.create_package_rules (
            obj.prepare_bitmask_map ( acceptor_chain_bitmask_map )
         )

      Returns: (nested) rule object or None

      arguments:
      * acceptor_chain_bitmask_map -- "acceptor chain" -> "bitmask" map
      """
      return self.create_package_rules (
         prepare_bitmask_map ( acceptor_chain_bitmask_map )
      )
   # --- end of compile_bitmask_map (...) ---


# --- end of AbstractAdditionControlPackageRuleGenerator ---


#
# ** step 2 ** -- expand global and category-wide bitmasks,
#                 set effective package bitmask
#                 (FIXME: does it make sense to apply the global bitmask?)
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

def expand_acceptor_chain_bitmasks ( acceptor_chain_bitmask_map ):
   """Expands a "acceptor chain" -> "bitmask" map.
   (Sets the effective bitmask, propagates global bitmasks, ...)

   In-place operation that modifies the acceptor_chain_bitmask_map arg.

   Returns: None (implicit)

   arguments:
   * acceptor_chain_bitmask_map -- "acceptor chain" -> "bitmask" map
   """
   # naming convention: >e<ffective bit>mask< => emask

   get_emask = AdditionControlResult.get_effective_package_policy

   def normalize_entry ( mapping, key, additional_emask=0 ):
      """Determines and sets the effective bitmask of mapping->key.

      Returns: None (implicit)

      arguments:
      * mapping          -- dict-like object
      * key              -- dict key (has to exist)
      * additional_emask -- effective bitmask that should be propagated to
                            mapping->key (global/category-wide bitmask)
      """
      new_value     = get_emask ( mapping [key] | additional_emask )
      mapping [key] = new_value
      return new_value
   # --- end of normalize_entry (...) ---

   def normalize_entry_maybe_missing ( mapping, key, additional_emask=0 ):
      """Like normalize_entry(), but does not require the existence of
      mapping->key (the entry will be created if necessary).

      arguments:
      * mapping          --
      * key              --
      * additional_emask --
      """
      if key in mapping:
         return normalize_entry ( mapping, key, additional_emask )
      else:
         mapping [key] = additional_emask
         return additional_emask
   # --- end of normalize_entry_maybe_missing (...) ---

   # propagate global/category-wide emask to package_token entries

   # acceptor_chain_bitmask_map->True->True is the global emask
   if True in acceptor_chain_bitmask_map:
      global_emask = normalize_entry_maybe_missing (
         acceptor_chain_bitmask_map [True], True
      )
   else:
      global_emask = 0


   for category_token, package_token_map in acceptor_chain_bitmask_map.items():
      # --- cannot modify acceptor_chain_bitmask_map in this block

      category_emask = normalize_entry_maybe_missing (
         package_token_map, True, global_emask
      )

      for package_token in package_token_map:
         # --- cannot modify acceptor_chain_bitmask_map, package_token_map
         if package_token is not True:
            # else already processed (category_emask)
            normalize_entry (
               package_token_map, package_token, category_emask
            )
         # -- end if <package_token>
      # -- end for <package_token>

   # -- end for <category_token,package_token_map>

# --- end of expand_acceptor_chain_bitmasks (...) ---


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
#   Not implemented. (graph/spanning-tree and/or logic minimization)
#

def create_bitmask_acceptor_chain_map ( acceptor_chain_bitmask_map ):
   """Transforms a "acceptor chain" -> "[effective] bitmask" map
   into a "[effective] bitmask" -> "acceptor chain" mask without applying
   any optimization/reduction steps.

   Returns: "[effective] bitmask" -> "acceptor chain" map

   arguments:
   * acceptor_chain_bitmask_map -- "acceptor chain" -> "bitmask" map
                                   Should be in expanded form
                                   (expand_acceptor_chain_bitmasks())
   """
   bitmask_acceptor_chain_map = {}

   for category_token, package_token_map in acceptor_chain_bitmask_map.items():

      for package_token, emask in package_token_map.items():
         try:
            emask_entry = bitmask_acceptor_chain_map [emask]
         except KeyError:
            bitmask_acceptor_chain_map [emask] = {
               category_token: set ({ package_token, })
            }
         else:
            try:
               category_entry = emask_entry [category_token]
            except KeyError:
               emask_entry [category_token] = set ({ package_token, })
            else:
               category_entry.add ( package_token )
      # -- end for <package token map>

   # -- end for <category token map>

   return bitmask_acceptor_chain_map
# --- end of create_bitmask_acceptor_chain_map (...) ---


#
# ** step 4 -- naive path compaction **
#   (Keep in mind that acceptor tokens cannot be merged with match-all)
#
#   reduce acceptor chains (drop-superseeded):
#   for each effective_bitmask b in BITMASK_MAP loop
#      if BITMASK_MAP->b->True->True exists then
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

def reduce_bitmask_acceptor_chain_map ( bitmask_acceptor_chain_map ):
   """Reduces/Optimizes a "effective bitmask" -> "acceptor chain" map.

   In-place operation, the bitmask_acceptor_chain_map will be modified.

   Returns: None (implicit)

   arguments:
   * bitmask_acceptor_chain_map -- "effective bitmask" -> "acceptor chain" map

   Implementation detail:
   The reduced map uses empty sets/dicts for representing "match-all"
   acceptors.
   """

   # could be integrated in create_bitmask_acceptor_chain_map(),
   #  but kept separate for better readability
   #

   # emask==0 can be ignored
   bitmask_acceptor_chain_map.pop ( 0, True )

   for emask in bitmask_acceptor_chain_map:
      emask_matches_all = False

      for category_token, package_token_set in (
         bitmask_acceptor_chain_map [emask].items()
      ):
         if True not in package_token_set:
            # category~DONT_CARE, package!=True <=> keep entries
            pass
         elif category_token is True:
            # category==True, package==True <=> match all, *** BREAK LOOP ***
            emask_matches_all = True
            break
         else:
            # category!=True, package==True <=> match entire category
            package_token_set.clear()
      # -- end for <category->package token map>

      if emask_matches_all:
         bitmask_acceptor_chain_map [emask].clear()
   # -- end for <emask>
# --- end of reduce_bitmask_acceptor_chain_map (...) ---


#
# ** step 5 -- convert the acceptor chains to objects **
#
#   the final BITMASK_MAP can be easily translated into rule objects:
#
#   * convert the the effective bitmask into one or more
#      PackageAdditionControl*Actions
#
#   * an OR<category OR<packages>> match statement
#      represents the acceptor chain
#      (reduce properly, e.g. "accept-all" entries)
#
#
# ** done **
#

def create_packagerule_action_map():
   """Helper function that creates all add-policy package rule actions.

   Returns: dict ( "bitmask atom" (2**k) -> "package rule action" )

   arguments: none
   """
   return {
      action_cls.CONTROL_RESULT: action_cls (
         priority=action_cls.CONTROL_RESULT
      )
         for action_cls in (
            getattr (
               roverlay.packagerules.actions.addition_control,
               action_cls_name
            ) for action_cls_name in (
               roverlay.packagerules.actions.addition_control.ACTIONS
            )
         ) if action_cls.CONTROL_RESULT
   }
# --- end of create_packagerule_action_map (...) ---


def create_package_rules (
   reduced_bitmask_acceptor_chain_map,
   convert_category_token_to_acceptor,
   convert_package_token_to_acceptor,
   collapse_acceptor_combounds=True,
):
   """Converts the given "effective bitmask" -> "acceptor chain" map
   into a nested package rule.

   Returns: (nested) package rule or None

   arguments:
   * reduced_bitmask_acceptor_chain_map -- reduced/optimized
                                           "bitmask" -> "acceptor chain" map
   * convert_category_token_to_acceptor -- function(token,priority)
                                             -> category acceptor
   * convert_package_token_to_acceptor  -- function(token,priority)
                                             -> package acceptor
   * collapse_acceptor_combounds        -- bool that controls whether acceptor
                                           compounds should be merged or not
                                           Defaults to True.
   """
   packagerule_actions    = create_packagerule_action_map()
   # true acceptor with priority -1
   always_true_acceptor   = (
      roverlay.packagerules.acceptors.trivial.TrueAcceptor ( priority=-1 )
   )


   def get_acceptor_recursive ( category_token_map, priority ):
      """
      Creates a (possibly nested) acceptor for the given category_token_map.

      Returns: not-None acceptor

      arguments:
      * category_token_map -- "category token" -> "package token" map
                               ("acceptor chain")
      * priority           -- "recommended" priority of the acceptor
                               Ignored when returning an always-true acceptor.
      """

      # Note: it's illegal to set an acceptor's priority after its creation
      #       this would violate namespace->get_object()
      #        ==> use 0 as priority for objects where it doesn't matter much
      #             (at the cost of unstable-sorted output)
      #
      #        The acceptor gets wrapped with an Acceptor_AND object anyway(*),
      #        no need to set any priority.
      #        (*) "the top-level logic of a MATCH-block is AND by convention"
      #            the acceptor returned by get_*acceptor*() can be of *any*
      #            type, but its str representation (--print-package-rules)
      #            would always be the same.
      #
      #        ["proper" prio-setting is already implemented at
      #         package/category acceptor level, so the outmost AND acceptor
      #         has exactly one member and the member's priority matches
      #         the acceptor's]
      #

      def get_package_acceptor ( package_tokens, prio ):
         """Creates a (nested) acceptor for the given non-empty iterable
         of package tokens.

         Returns: not-None acceptor

         arguments:
         * package_tokens -- iterable of package tokens (not empty)
         * prio           -- advised priority of the top-most acceptor
                              (the object being returned)
         """
         if not package_tokens:
            raise ValueError ( "package token set must not be empty!" )

         elif len(package_tokens) == 1:
            # special case: bind prio to package_acceptor
            return convert_package_token_to_acceptor (
               next(iter(package_tokens)), prio
            )

         else:
            package_acceptors = [
               convert_package_token_to_acceptor ( package_token, 0 )
                  for package_token in package_tokens
            ]

            # package acceptors get ORed, no need to set a specific priority
            combined_acceptor = (
               roverlay.packagerules.abstract.acceptors.Acceptor_OR ( prio )
            )

            for package_acceptor in package_acceptors:
               combined_acceptor.add_acceptor ( package_acceptor )

            return combined_acceptor

      # --- end of get_package_acceptor (...) ---

      def get_category_acceptor ( category_token, package_tokens, prio ):
         """Creates a nested acceptor for the given category token and its
         package tokens.

         Returns: not-None acceptor

         arguments:
         * category_token -- category token (True or non-empty)
         * package_tokens -- iterable of package tokens (can be empty)
         """

         if category_token is True:
            return get_package_acceptor ( package_tokens, prio )

         elif package_tokens:
            acceptor = (
               roverlay.packagerules.abstract.acceptors.Acceptor_AND ( prio )
            )

            # match category first and then packages
            acceptor.add_acceptor (
               convert_category_token_to_acceptor ( category_token, 0 )
            )
            acceptor.add_acceptor (
               get_package_acceptor ( package_tokens, 1 )
            )

            return acceptor

         else:
            return convert_category_token_to_acceptor ( category_token, prio )
      # --- end of get_category_acceptor (...) ---

      if not category_token_map:
         # match-all
         return always_true_acceptor

      elif len(category_token_map) == 1:
         # special case: bind priority to entry
         category_acceptor = None
         for category_token, package_tokens in category_token_map.items():
            if category_acceptor is None:
               category_acceptor = get_category_acceptor (
                  category_token, package_tokens, priority
               )
            else:
               raise AssertionError ( "must not loop more than once." )
         # -- end for

         return category_acceptor

      else:
         acceptors = [
            get_category_acceptor ( category_token, package_tokens, k )
               for ( k, ( category_token, package_tokens ) ) in enumerate (
                  category_token_map.items()
               )
         ]

         combined_acceptor = (
            roverlay.packagerules.abstract.acceptors.Acceptor_OR ( priority )
         )

         for acceptor in acceptors:
            combined_acceptor.add_acceptor ( acceptor )

         return combined_acceptor

   # --- end of get_acceptor_recursive (...) ---

   def create_rule ( category_token_map, emask ):
      """Creates a package rule for the given acceptor chain
      ("category token" -> "package tokens" map)

      Returns: not-None not-nested package rule (with a nested match block)

      arguments:
      * category_token_map -- acceptor chain
      * emask              -- effective bitmask that gets translated into
                              its corresponding package rule actions
      """

      # wrap actual acceptor with Acceptor_AND, see above
      actual_acceptor = get_acceptor_recursive ( category_token_map, 0 )
      and_acceptor    = roverlay.packagerules.abstract.acceptors.Acceptor_AND (0)
      and_acceptor.add_acceptor ( actual_acceptor )

      if collapse_acceptor_combounds:
         and_acceptor.merge_sub_compounds()

      rule = roverlay.packagerules.abstract.rules.PackageRule (
         # top-priority action should be applied last
         priority = AdditionControlResult.get_reversed_sort_key ( emask )
      )

      rule.set_acceptor ( and_acceptor )

      have_any_action = False
      for k, action in packagerule_actions.items():
         have_any_action = True
         if ( k & emask ):
            rule.add_action ( action )

      if not have_any_action:
         raise AssertionError (
            "rule object has no actions - bad emask? {:#x}".format (
               emask=emask
            )
         )

      return rule
   # --- end of create_rule (...) ---

   rules = [
      create_rule ( category_token_map, emask )
         for emask, category_token_map in \
            reduced_bitmask_acceptor_chain_map.items()
   ]

   if not rules:
      return None

   elif len(rules) == 1:
      rules [0].priority = -1
      return rules [0]

   else:
      combined_rule = roverlay.packagerules.abstract.rules.NestedPackageRule (
         priority = -1
      )
      combined_rule.set_acceptor ( always_true_acceptor )

      for rule in rules:
         combined_rule.add_rule ( rule )

      return combined_rule
   # -- end if

# --- end of create_package_rules (...) ---
