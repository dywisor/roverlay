# R overlay -- simple dependency rules
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""simple dependency rules

This module provides 4 simple dependency rules classes
* SimpleDependencyRule
* SimpleIgnoreDependencyRule
* SimpleFuzzyDependencyRule
* SimpleFuzzyIgnoreDependencyRule

(TODO NOTE: could describe rule matching here)
"""

__all__ = (
   'SimpleIgnoreDependencyRule', 'SimpleDependencyRule',
   'SimpleFuzzyDependencyRule', 'SimpleFuzzyIgnoreDependencyRule'
)

from roverlay.depres.simpledeprule.abstractrules import \
   SimpleRule, FuzzySimpleRule

class RuleConstructor ( object ):

   def __init__ ( self, eapi ):
      self.eapi = eapi

      self.kw_ignore       = SimpleIgnoreDependencyRule.RULE_PREFIX
      self.kw_fuzzy        = SimpleFuzzyDependencyRule.RULE_PREFIX
      self.kw_fuzzy_ignore = SimpleFuzzyIgnoreDependencyRule.RULE_PREFIX
   # --- end of __init__ (...) ---

   def lookup ( self, keyworded_str ):
      get_kwless = lambda : keyworded_str[1:].lstrip() or None

      kw = keyworded_str[0]
      if kw == self.kw_ignore:
         return ( SimpleIgnoreDependencyRule, get_kwless(), {} )
      elif kw == self.kw_fuzzy_ignore:
         return ( SimpleFuzzyIgnoreDependencyRule, get_kwless(), {} )
      elif kw == self.kw_fuzzy:
         ##TODO
         ## > "default"
         ## > "slot only"
         ## > "combined"
   ## syntax
   ## ~cat/pkg:<slot suffix>
   ## ~cat/pkg:/<slot suffix>
   ## ~cat/pkg:{major}/{minor}<slot suffix>
   ##
         kwless = get_kwless()
         resolving, sepa, remainder = kwless.partition ( ':' )

         if sepa:
            # fuzzy slot rule
            kwargs = { 'resolving_package_name' : resolving, }
            slot_head, slot_sepa, slot_rem = remainder.partition ( ':' )

            if slot_sepa:
               # slot restriction
               istart, isepa, istop = slot_head.partition ( '..' )
               if isepa:
                  kwargs ['slot_restrict'] = frozenset (
                     range ( int ( istart or 0 ), int ( istop or 100 ) + 1 )
                  )
               else:
                  kwargs ['slot_restrict'] = frozenset (
                     int ( k ) for k in slot_head.split ( ',' )
                  )

               remainder = slot_rem
            else:
               remainder = slot_head
            # -- end if;


            if not remainder:
               # <cat>/<pkg>:
               kwargs ['slot_suffix'] = sepa + '{slot}'

            elif remainder[0] in { '/', '*', '=' }:
               # subslot, "any slot" operators
               assert self.eapi >= 5
               kwargs ['slot_suffix'] = sepa + '{slot}' + remainder
            else:
               kwargs ['slot_suffix'] = sepa + remainder


            # verify that slot_suffix can be formatted properly
##            if kwargs ['slot_suffix'] [0] != ':':
##               kwargs ['slot_suffix'] = ':' + kwargs ['slot_suffix']

            DONT_CARE = kwargs ['slot_suffix'].format ( slot='_', version='_' )
            return ( SimpleFuzzySlotDependencyRule, resolving, kwargs )
         else:
            return ( SimpleFuzzyDependencyRule, kwless, {} )
      else:
         return ( SimpleDependencyRule, keyworded_str, {} )
   # --- end of lookup (...) ---

# --- end of RuleConstructor ---

class SimpleIgnoreDependencyRule ( SimpleRule ):

   RULE_PREFIX = '!'

   def __init__ ( self, priority=50, resolving_package=None, **kw ):
      super ( SimpleIgnoreDependencyRule, self ) . __init__ (
         logger_name = 'IGNORE_DEPS',
         resolving_package=None,
         priority=50,
         **kw
      )

   def __str__ ( self ):
      if self.is_selfdep:
         return self.__class__.RULE_PREFIX + next ( iter ( self.dep_alias ) )
      else:
         return super ( self.__class__, self ) . __str__()

class SimpleDependencyRule ( SimpleRule ):

   def __init__ ( self, priority=70, resolving_package=None, **kw ):
      """Initializes a SimpleDependencyRule. This is
      a SimpleIgnoreDependencyRule extended by a portage package string.

      arguments:
      * resolving package --
      * dep_str --
      * priority --
      """
      super ( SimpleDependencyRule, self ) . __init__ (
         priority=priority,
         logger_name=resolving_package,
         resolving_package=resolving_package,
         **kw
      )

   # --- end of __init__ (...) ---

class SimpleFuzzyIgnoreDependencyRule ( FuzzySimpleRule ):

   RULE_PREFIX = '%'

   def __init__ ( self, priority=51, resolving_package=None, **kw ):
      super ( SimpleFuzzyIgnoreDependencyRule, self ) . __init__ (
         priority=priority,
         resolving_package=resolving_package,
         logger_name = 'FUZZY.IGNORE_DEPS',
         **kw
      )

   def __str__ ( self ):
      if self.is_selfdep:
         return self.__class__.RULE_PREFIX + next ( iter ( self.dep_alias ) )
      else:
         return super ( self.__class__, self ) . __str__()

   def handle_version_relative_match ( self, *args, **kwargs ):
      raise Exception ( "should-be unreachable code" )
   # --- end of handle_version_relative_match (...) ---

# --- end of SimpleFuzzyIgnoreDependencyRule ---


class SimpleFuzzyDependencyRule ( FuzzySimpleRule ):

   RULE_PREFIX = '~'

   def __init__ ( self, priority=72, resolving_package=None, **kw ):
      super ( SimpleFuzzyDependencyRule, self ) . __init__ (
         priority=priority,
         resolving_package=resolving_package,
         logger_name = 'FUZZY.' + resolving_package,
         **kw
      )
   # --- end of __init__ (...) ---

   def handle_version_relative_match ( self, dep_env, fuzzy ):
      ver_pkg  = self.resolving_package + '-' + fuzzy ['version']
      vmod_str = fuzzy ['version_modifier']
      vmod     = fuzzy ['vmod']

      #if vmod & dep_env.VMOD_NOT:
      if vmod == dep_env.VMOD_NE:
         # package matches, but specific version is forbidden
         # ( !<package>-<specific verion> <package> )
         return "( !={vres} {res} )".format (
            vres=ver_pkg, res=self.resolving_package
         )
      else:
         # std vmod: >=, <=, =, <, >
         return vmod_str + ver_pkg
   # --- end of handle_version_relative_match (...) ---

# --- end of SimpleFuzzyDependencyRule ---


class SimpleFuzzySlotDependencyRule ( FuzzySimpleRule ):
   # 2 slot variants
   # "slot only": resolve dep_str as <cat>/<pkg>:<slot>
   # "combined": resolve dep_str as <vmod><cat>/<pkg>-<ver>:<slot>

#   FMT_DICT = {
#      'slot' : '{slot}',
#   }

   #RULE_PREFIX = '~'
   RULE_PREFIX = SimpleFuzzyDependencyRule.RULE_PREFIX

   def __init__ ( self,
      priority               = 71,
      resolving_package      = None,
      resolving_package_name = None,
      slot_suffix            = None,
      slot_restrict          = None,
      **kw
   ):
      super ( SimpleFuzzySlotDependencyRule, self ) . __init__ (
         priority=priority,
         resolving_package = resolving_package,
         logger_name       = 'FUZZY_SLOT.' + (
            resolving_package_name if resolving_package_name is not None
            else resolving_package.partition ( ':' )[0]
         ),
         **kw
      )

      self.slot_suffix = slot_suffix

      if slot_restrict:
         self.slot_restrict = frozenset ( int ( k ) for k in slot_restrict )
      else:
         self.slot_restrict = None
   # --- end of __init__ (...) ---

   def __str__ ( self ):
      # FIXME/TODO
      return 'TODO! {low}..{high} {s}'.format (
         low  = ( min ( self.slot_restrict ) if self.slot_restrict else 'X' ),
         high = ( max ( self.slot_restrict ) if self.slot_restrict else 'X' ),
         s    = ( super ( SimpleFuzzySlotDependencyRule, self ).__str__() ),
      )
   # --- end of __str__ (...) ---

   def handle_version_relative_match ( self, dep_env, fuzzy ):
      res  = False
      vmod = fuzzy ['vmod']

      if not ( vmod & dep_env.VMOD_NOT ):
         # can be resolved as slot(ted) dep

         ver_str = fuzzy ['version']
         v_major, sepa, v_remainder = ver_str.partition ( '.' )
         try:
            slot = int ( v_major )

            # resolve '<' and '>' by decrementing/incrementing slot
            if vmod == dep_env.VMOD_LT:
               slot -= 1
            elif vmod == dep_env.VMOD_GT:
               slot += 1

            if not self.slot_restrict or slot in self.slot_restrict:
               res = self.resolving_package + self.slot_suffix.format (
                  slot=slot, version=ver_str,
                  #vmod=fuzzy ['version_modifier']
               )
         except ValueError:
            pass
      # -- end if vmod

      return res
   # --- end of handle_version_relative_match (...) ---
