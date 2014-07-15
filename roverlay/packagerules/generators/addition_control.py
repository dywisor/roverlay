# R overlay -- package rule generators, addition control
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import absolute_import
# temporary_demo_func():
from __future__ import print_function


import abc
# __metaclass__/metaclass= workaround
_AbstractObject = abc.ABCMeta ( str("AbstractObject"), ( object, ), {} )

import collections

#~ import roverlay.util.fileio
import roverlay.util.namespace
#~
import roverlay.packagerules.abstract.acceptors
import roverlay.packagerules.abstract.rules
#~ import roverlay.packagerules.acceptors.stringmatch
#~ import roverlay.packagerules.acceptors.util
import roverlay.packagerules.acceptors.trivial
import roverlay.packagerules.actions.addition_control
#~
#~ from roverlay.packagerules.abstract.rules import (
   #~ NestedPackageRule, PackageRule
#~ )
#~
#~ from roverlay.packagerules.acceptors.stringmatch (
   #~ NocaseStringAcceptor, StringAcceptor,
   #~ RegexAcceptor, ExactRegexAcceptor
#~ )
#~
#~ from roverlay.packagerules.acceptors.util import (
   #~ get_package, get_package_name, get_ebuild_name, get_category,
   #~ DEFAULT_CATEGORY_REPLACEMENT
#~ )

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



class AbstractAdditionControlPackageRuleGenerator ( _AbstractObject ):

   #CategoryToken = collections.namedtuple ( 'CategoryToken', '<attr>' )
   #PackageToken  = collections.namedtuple ( 'PackageToken',  '<attr>' )

   @abc.abstractmethod
   def category_token_to_acceptor ( self, category_token, priority ):
      raise NotImplementedError()

   @abc.abstractmethod
   def package_token_to_acceptor ( self, category_token, priority ):
      raise NotImplementedError()

   def create_package_rules ( self, reduced_bitmask_acceptor_chain_map ):
      # create_package_rules() is defined/implemented below (step 5)
      return create_package_rules (
         reduced_bitmask_acceptor_chain_map,
         convert_category_token_to_acceptor = self.category_token_to_acceptor,
         convert_package_token_to_acceptor  = self.package_token_to_acceptor
      )
   # --- end of create_package_rules (...) ---

# --- end of AbstractAdditionControlPackageRuleGenerator ---


def abstract_category_token_to_acceptor ( category_token, priority, namespace ):
   raise NotImplementedError()
# --- end of abstract_category_token_to_acceptor (...) ---

def abstract_package_token_to_acceptor ( package_token, priority, namespace ):
   raise NotImplementedError()
# --- end of abstract_package_token_to_acceptor (...) ---


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
   # naming convention: >e<ffective bit>mask< => emask
   # inplace operation (returns None and modifies the obj directly)

   get_emask = AdditionControlResult.get_effective_package_policy


   def normalize_entry ( mapping, key, additional_emask=0 ):
      new_value     = get_emask ( mapping [key] | additional_emask )
      mapping [key] = new_value
      return new_value
   # --- end of normalize_entry (...) ---

   def normalize_entry_maybe_missing ( mapping, key, additional_emask=0 ):
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
   # could be integrated in create_bitmask_acceptor_chain_map(),
   #  but kept separate for better readability
   #
   #  Note that the actual implementation uses empty sets/dicts in the
   #  reduced bitmask->acceptor chain mask to represent "match-all".
   #

   # ** inplace **

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
   # dict < int~2**k => packagerule action >
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
   convert_package_token_to_acceptor
):
   packagerule_actions    = create_packagerule_action_map()
   # true acceptor with priority -1
   always_true_acceptor   = (
      roverlay.packagerules.acceptors.trivial.TrueAcceptor ( priority=-1 )
   )


   def get_acceptor_recursive ( category_token_map, priority ):
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
      # wrap actual acceptor with Acceptor_AND, see above
      actual_acceptor = get_acceptor_recursive ( category_token_map, 0 )
      and_acceptor    = roverlay.packagerules.abstract.acceptors.Acceptor_AND (0)
      and_acceptor.add_acceptor ( actual_acceptor )

      rule = roverlay.packagerules.abstract.rules.PackageRule ( priority=emask )

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

class SillyAdditionControlPackageRuleGenerator (
   AbstractAdditionControlPackageRuleGenerator
):
   """
   An add-policy package rule generator that doesn't care about its tokens.

   Not useful for productive usage - will be removed as soon as a proper
   rule generator has been implemented.
   """

   def __init__ ( self ):
      super ( SillyAdditionControlPackageRuleGenerator, self ).__init__()
      self.namespace = roverlay.util.namespace.SimpleNamespace()

   def _get_true_accepor_from_namespace ( self, any_token, priority ):
      return self.namespace.get_object_v (
         roverlay.packagerules.acceptors.trivial.TrueAcceptor,
         ( priority, ),
         {}
      )

   category_token_to_acceptor = _get_true_accepor_from_namespace
   package_token_to_acceptor  = _get_true_accepor_from_namespace




def temporary_demo_func():
   rule_generator             = SillyAdditionControlPackageRuleGenerator()
   add_control_rule           = None
   bitmask_acceptor_chain_map = None
   acceptor_chain_bitmask_map = {
      True: {
         True: AdditionControlResult.PKG_REVBUMP_ON_COLLISION,
         'p0': 8|2,
      },
      'c': {
         True: 2,
      },
      'd': {
         True: AdditionControlResult.PKG_REPLACE_ONLY,
      },
      'f': {
         'p1': AdditionControlResult.PKG_REPLACE_ONLY,
      },
   }

   print ( "** initial acceptor_chain -> raw_bitmask map" )
   print ( acceptor_chain_bitmask_map )
   print()

   expand_acceptor_chain_bitmasks ( acceptor_chain_bitmask_map )
   print ( "** expanded acceptor_chain -> effective_bitmask map" )
   print ( acceptor_chain_bitmask_map )
   print()

   bitmask_acceptor_chain_map = (
      create_bitmask_acceptor_chain_map ( acceptor_chain_bitmask_map )
   )
   print ( "** initial effective_bitmask -> acceptor_chain map" )
   print(bitmask_acceptor_chain_map)
   print()

   reduce_bitmask_acceptor_chain_map ( bitmask_acceptor_chain_map )
   print ( "** reduced effective_bitmask -> acceptor_chain map" )
   print(bitmask_acceptor_chain_map)
   print()

   add_control_rule = (
      rule_generator.create_package_rules ( bitmask_acceptor_chain_map )
   )
   add_control_rule.priority = -1
   add_control_rule.prepare()

   print ( "** created package rule (sorted)" )
   print(add_control_rule)
   print()

   print ( "** content of the rule generator\'s namespace" )
   print ( rule_generator.namespace._objects )

# --- end of temporary_demo_func (...) ---


if __name__ == '__main__':
   import sys
   import os

   try:
      temporary_demo_func()
   except KeyboardInterrupt:
      excode = os.EX_OK ^ 130
   else:
      excode = os.EX_OK

   sys.exit ( excode )
