# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

#import weakref

import roverlay.interface.generic


import roverlay.depres.channels
import roverlay.depres.depresolver
import roverlay.depres.deptype
import roverlay.depres.simpledeprule.pool
import roverlay.depres.simpledeprule.rules
import roverlay.depres.simpledeprule.rulemaker

DEFAULT_DEPTYPE = roverlay.depres.deptype.ALL

class RuleSyntaxException ( Exception ):
   pass

class DepresInterface ( roverlay.interface.generic.RoverlaySubInterface ):

   def __init__ ( self, parent_interface ):
      super ( DepresInterface, self ).__init__ (
         parent_interface=parent_interface
      )

      # set up the resolver
      self._resolver = roverlay.depres.depresolver.DependencyResolver (
         err_queue=self.err_queue
      )
      ## log everything
      self._resolver.set_logmask ( -1 )
      ## disable passing events to listeners
      self._resolver.set_listenermask ( 0 )

      # dependency rule pools (a set of rules) are organized in a FIFO
      # structure that allows to create and delete new pools at runtime
      self._poolstack = self._resolver.static_rule_pools
      self._pool_id   = -1

      self._parser = roverlay.depres.simpledeprule.rulemaker.SimpleRuleMaker()
   # --- end of __init__ (...) ---

   @property
   def resolver ( self ):
      return self._resolver

   @property
   def parser ( self ):
      return self._parser

   @property
   def poolstack ( self ):
      return self._poolstack

   @property
   def pool_id ( self ):
      return self._pool_id

   def _update_resolver ( self ):
      # sort() should be called on a per-pool basis
      self._resolver._reset_unresolvable()
   # --- end of _update_resolver (...) ---

   def close ( self ):
      super ( DepresInterface, self ).close()
      self._resolver.close()
   # --- end of close (...) ---

   def update ( self ):
      super ( DepresInterface, self ).update()
      if self._poolstack:
         self._poolstack[-1].sort()
      self._update_resolver()
   # --- end of update (...) ---

   def has_pool ( self ):
      return self._poolstack
   # --- end of has_pool (...) ---

   def has_nonempty_pool ( self ):
      return self._poolstack and not self._poolstack[-1].empty()
   # --- end of has_nonempty_pool (...) ---

   def get_pool ( self ):
      if self._poolstack:
         return self._poolstack[-1]
      else:
         return self.get_new_pool ( force=True )
   # --- end of get_pool (...) ---

   def get_new_pool ( self, force=False, with_deptype=DEFAULT_DEPTYPE ):
      if force or not self._poolstack or not self._poolstack[-1].empty():
         self._pool_id += 1
         try:
            pool = roverlay.depres.simpledeprule.pool.SimpleDependencyRulePool (
               "pool" + str ( self._pool_id ),
               deptype_mask=DEFAULT_DEPTYPE
            )
            self.poolstack.append ( pool )
         except:
            self._pool_id -= 1
            raise

         self._update_resolver()
      # -- end if force or ...
      return self._poolstack[-1]
   # --- end of get_new_pool (...) ---

   def discard_pool ( self ):
      try:
         self._poolstack.pop()
         self._pool_id -= 1
         assert self._pool_id >= -1
         return True
      except AssertionError:
         raise
      except:
         return False
   # --- end of discard_pool (...) ---

   def discard_pools ( self, count ):
      for i in range ( count ):
         if not self.discard_pool():
            return i
      else:
         return count
   # --- end of discard_pools (...) ---

   def discard_empty_pools ( self ):
      removed = 0
      while self._poolstack and self._poolstack[-1].empty():
         if self.discard_pool():
            removed += 1
         else:
            raise AssertionError (
               "discard_pool() should succeed if topmost pool exists."
            )
      return removed
   # --- end of discard_empty_pools (...) ---

   def load_rules_from_config ( self ):
      return self.load_rule_files (
         self.config.get_or_fail ( "DEPRES.simple_rules.files" )
      )
   # --- end of load_rules_from_config (...) ---

   def load_rule_files ( self, files_or_dirs ):
      return self._resolver.get_reader().read ( files_or_dirs )
   # --- end of load_rule_files (...) ---

   def add_rule ( self, rule_str ):
      if not self._parser.add ( rule_str ):
         raise RuleSyntaxException ( rule_str )
      return True
   # --- end of add_rule (...) ---

   def add_rules ( self, *rule_str_list ):
      for rule_str in rule_str_list:
         self.add_rule ( rule_str )
      return True
   # --- end of add_rules (...) ---

   def add_rule_list ( self, rule_str_list ):
      for rule_str in rule_str_list:
         self.add_rule ( rule_str )
      return True
   # --- end of add_rule_list (...) ---

   def compile_rules ( self, new_pool=False ):
      rules    = self._parser.done()
      destpool = self.get_new_pool() if new_pool else self.get_pool()

      try:
         # FIXME/COULDFIX: deptypes not supported here
         for deptype, rule in rules:
            destpool.rules.append ( rule )

         if destpool.empty():
            self.discard_empty_pools()
         else:
            destpool.sort()
         self._update_resolver()
         return True
      except:
         if new_pool:
            # this could discard (previosly) empty pools, too
            #  (side-effect of "optimizations" in get_new_pool())
            #
            self.discard_pool()
         raise
   # --- end of compile_rules (...) ---

   def add_immediate_rule ( self, rule_str ):
      return self.add_rule ( rule_str ) and self.compile_rules()
   # --- end of add_immediate_rule (...) ---

   def visualize_pool ( self ):
      if self._poolstack:
         return '\n'.join (
            '\n'.join ( rule.export_rule() )
               for rule in self._poolstack[-1].rules
         )
      else:
         return ""
   # --- end of visualize_pool (...) ---

   def get_channel ( self, channel_name="channel" ):
      channel = roverlay.depres.channels.EbuildJobChannel (
         err_queue=self.err_queue, name=channel_name
      )
      self._resolver.register_channel ( channel )
      return channel
   # --- end of get_channel (...) ---

   def do_resolve ( self, deps, with_deptype=DEFAULT_DEPTYPE ):
      channel = self.get_channel()
      # FIXME/COULDFIX: once again, hardcoded deptype
      try:
         channel.add_dependencies ( deps, with_deptype  )

         channel_result = channel.satisfy_request (
            close_if_unresolvable=False,
            preserve_order=True
         )
      finally:
         channel.close()

      return channel_result
   # --- end of do_resolve (...) ---

   def resolve ( self, *deps, **kw ):
      result = self.do_resolve ( deps, **kw )
      return None if result is None else result [0]
   # --- end of resolve (...) ---

   def can_resolve ( self, *deps, **kw ):
      return self.do_resolve ( deps, **kw ) is not None
   # --- end of can_resolve (...) ---

   def cannot_resolve ( self, *deps, **kw ):
      return self.do_resolve ( deps, **kw ) is None
   # --- end of cannot_resolve (...) ---

# --- end of DepresInterface ---
