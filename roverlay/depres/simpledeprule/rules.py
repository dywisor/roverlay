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

class SlotRestrict ( object ):
   def accepts ( self, k ):
      """Returns True if k is allowed, else False.

      arguments:
      * k -- int
      """
      return True

   def __bool__ ( self ):
      return True

   def noexport ( self ):
      pass

   def __str__ ( self ):
      return ':'
# --- end of SlotRestrict ---

class SlotRangeRestrict ( SlotRestrict ):
   DEFAULT_LOW  = 0
   DEFAULT_HIGH = 1000

   def __init__ ( self, low, high ):
      super ( SlotRangeRestrict, self ).__init__()
      if low:
         self.low = int ( low )
      else:
         self.low = self.DEFAULT_LOW
         self._implicit_low = True

      if high:
         self.high = int ( high )
      else:
         self.high = self.DEFAULT_HIGH
         self._implicit_high = True
   # --- end of __init__ (...) ---

   def noexport ( self ):
      if hasattr ( self, '_implicit_low' ):
         del self._implicit_low
      if hasattr ( self, '_implicit_high' ):
         del self._implicit_high
   # --- end of noexport (...) ---

   def accepts ( self, k ):
      """Returns True if k is allowed, else False.

      arguments:
      * k -- int
      """
      return k >= self.low and k <= self.high

   def __str__ ( self ):
      return ":{low}..{high}".format (
         low  = ( '' if hasattr ( self, '_implicit_low'  ) else self.low  ),
         high = ( '' if hasattr ( self, '_implicit_high' ) else self.high ),
      )
   # --- end of __str__ (...) ---

# --- end of SlotRangeRestrict ---

class SlotSetRestrict ( SlotRestrict ):
   def __init__ ( self, iterable ):
      self._iset = frozenset ( int ( k ) for k in iterable )

   def accepts ( self, k ):
      """Returns True if k is allowed, else False.

      arguments:
      * k -- int
      """
      return k in self._iset

   def __str__ ( self ):
      return ':' + ','.join ( str ( k ) for k in sorted ( self._iset ) )
   # --- end of __str__ (...) ---

# --- end of SlotSetRestrict ---

class RuleConstructor ( object ):

   def __init__ ( self, eapi ):
      ##self.eapi = eapi

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
         ## syntax
         ## ~cat/pkg:<slot range>:<slot suffix>
         kwless = get_kwless()
         resolving, sepa, remainder = kwless.partition ( ':' )

         if sepa:
            # fuzzy slot rule
            kwargs = dict()
            slot_head, slot_sepa, slot_rem = remainder.partition ( ':' )

            if slot_sepa:
               # int range restriction
               istart, isepa, istop = slot_head.partition ( '..' )
               if isepa:
                  kwargs ['slot_restrict'] = SlotRangeRestrict (
                     low=istart, high=istop
                  )
               else:
                  # int list restriction

                  # "filter(None,...)" filters 0 but not '0'
                  istr_list = list (
                     filter ( None, slot_head.split ( ',' ) )
                     #filter ( lambda s : s or s == 0, slot_head.split ( ',' ) )
                  )

                  if istr_list:
                     kwargs ['slot_restrict'] = SlotSetRestrict ( istr_list )

               remainder = slot_rem
            else:
               #kwargs ['slot_restrict'] = SlotRestrict()
               remainder = slot_head
            # -- end if;

            if remainder[:2] == '+v':
               kwargs ['with_version'] = True
               remainder = remainder[2:]
            # -- end if;

            if not remainder:
               pass
            elif remainder[0] in { '/', '*', '=' }:
               # subslot, "any slot" operators
               # (subslots don't seem to make much sense here)

               ##if self.eapi < 5: raise ...
               kwargs ['slot_suffix'] = remainder
            else:
               raise Exception (
                  "unknown slot rule remainder {!r}".format ( remainder )
               )

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
      priority          = 71,
      resolving_package = None,
      slot_suffix       = None,
      slot_restrict     = None,
      with_version      = False,
      **kw
   ):
      super ( SimpleFuzzySlotDependencyRule, self ) . __init__ (
         priority=priority,
         resolving_package = resolving_package,
         logger_name       = 'FUZZY_SLOT.' + resolving_package,
         **kw
      )

      self.slot_suffix   = slot_suffix
      self.slot_restrict = slot_restrict

      if with_version:
         self._resolving_fmt = (
            '{vmod}' + self.resolving_package + '-{version}:{slot}'
            + ( slot_suffix or '' )
         )
         self.with_version = True
      else:
         self._resolving_fmt = (
            self.resolving_package + ':{slot}' + ( slot_suffix or '' )
         )
         self.with_version = False

      if self.is_selfdep:
         raise NotImplementedError ( "fuzzy slot rule must not be a selfdep." )
   # --- end of __init__ (...) ---

   def noexport ( self ):
      del self.slot_suffix
      del self.with_version
      if self.slot_restrict:
         self.slot_restrict.noexport()
   # --- end of noexport (...) ---

   def get_resolving_str ( self ):
      return "{prefix}{resolv}{restrict}:{flags}{slot}".format (
         prefix   = self.RULE_PREFIX,
         resolv   = self.resolving_package,
         restrict = ( self.slot_restrict or '' ),
         flags    = ( '+v' if self.with_version else '' ),
         slot     = ( self.slot_suffix or '' ),
      )
   # --- end of get_resolving_str (...) ---

   def handle_version_relative_match ( self, dep_env, fuzzy ):
      res  = False
      vmod = fuzzy ['vmod']

      if not ( vmod & dep_env.VMOD_NOT ):
         # can be resolved as slot(ted) dep

         ver_str = fuzzy ['version']
         v_major, sepa, v_remainder = ver_str.partition ( '.' )
         try:
            # TODO/FIXME: slot != int(v_major);
            #  example: sci-libs/fftw where slots are K.J (2.1, 3.0)
            slot = int ( v_major )

            # resolve '<' and '>' by decrementing/incrementing slot
            if vmod == dep_env.VMOD_LT:
               slot -= 1
            elif vmod == dep_env.VMOD_GT:
               slot += 1

            if not self.slot_restrict or self.slot_restrict.accepts ( slot ):
               res = self._resolving_fmt.format (
                  slot=slot,
                  version=ver_str,
                  vmod=fuzzy ['version_modifier'],
               )
         except ValueError:
            pass
      # -- end if vmod

      return res
   # --- end of handle_version_relative_match (...) ---
