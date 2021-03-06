# R overlay -- dependency resolution interface
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

#import weakref

import errno

import roverlay.interface.generic
import roverlay.interface.root


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
   """Interface to dependency resolution.

   This class provides:

   * rule creation (from text/text files)
   * manage dependency rule pools
      (stack-like discard_pool()/get_[new_]pool(), pop_pool()/push_pool())
   * resolve dependencies:
   -> do_resolve(<deps>) for "raw" depres results
   -> resolve(<deps>) for generic purpose results (list of resolved deps)
   -> can_resolve(<deps>)/cannot_resolve(<deps>) for checking whether a
      dependency string can(not) be resolved

   Note that this interface relies on a parent interface (RootInterface).
   """

   CONFIG_KEY_DEPRULES = 'DEPRES.simple_rules.files'

   GREEDY_DEPRES_CHANNEL    = roverlay.depres.channels.EbuildJobChannel
   NONGREEDY_DEPRES_CHANNEL = roverlay.depres.channels.NonGreedyDepresChannel
   ROOT_INTERFACE_CLS       = roverlay.interface.root.RootInterface


   def __init__ ( self, parent_interface, greedy=None, want_tuple=False ):
      """Initializes the dependency resolution interface.

      arguments:
      * parent_interface -- parent interface that provides shared functionality
                            like logging and config
      * greedy           -- whether to use greedy depres channels by default
                            or not. See get_channel() for details.
                            Defaults to None (=greedy if dep resolver uses
                            threads, else not greedy).
      * want_tuple       -- when do_resolve() with preserve_order=True:
                             return resolved deps as tuples not list
                            Defaults to False.
      """
      super ( DepresInterface, self ).__init__ (
         parent_interface=parent_interface
      )

      # set up the resolver
      self._resolver = roverlay.depres.depresolver.DependencyResolver (
         err_queue=self.err_queue
      )
      self.set_greedy ( greedy )
      self.want_tuple = bool ( want_tuple )

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
      """direct access to the resolver"""
      return self._resolver

   @property
   def parser ( self ):
      """direct access to the rule parser"""
      return self._parser

   @property
   def poolstack ( self ):
      """direct access to the dependency rule pool stack"""
      return self._poolstack

   @property
   def pool_id ( self ):
      """Index of the topmost rule pool (-1 if no rule pool active)"""
      return self._pool_id

   def set_greedy ( self, greedy ):
      if greedy is None:
         self.default_depres_channel = (
            self.GREEDY_DEPRES_CHANNEL if self._resolver.get_threadcount()
            else self.NONGREEDY_DEPRES_CHANNEL
         )
      elif greedy:
         self.default_depres_channel = self.GREEDY_DEPRES_CHANNEL
      else:
         self.default_depres_channel = self.NONGREEDY_DEPRES_CHANNEL
   # --- end of set_greedy (...) ---

   def _update_resolver ( self ):
      """Updates the resolver.

      Returns: None (implicit)
      """
      # sort() should be called on a per-pool basis
      self._resolver._reset_unresolvable()
   # --- end of _update_resolver (...) ---

   def close ( self ):
      """Closes the dependency resolver and all subinterfaces.

      Returns: self
      """
      super ( DepresInterface, self ).close()
      self._resolver.close()
      return self
   # --- end of close (...) ---

   def update ( self ):
      """Updates this interface, i.e. performs a "soft"-reload of the
      resolver and sorts the topmost rule pool.

      Returns: self
      """
      super ( DepresInterface, self ).update()
      if self._poolstack:
         self._poolstack[-1].sort()
      self._update_resolver()
      return self
   # --- end of update (...) ---

   def fixup_pool_id ( self ):
      """Resets the pool id.

      Does not need to be called manually.

      Returns: None (implicit)
      """
      self._pool_id = len ( self._poolstack ) - 1
   # --- end of fixup_pool_id (...) ---

   def has_pool ( self ):
      """
      Returns True if this interface has at least one rule pool, else False.
      """
      return self._poolstack
   # --- end of has_pool (...) ---

   def has_nonempty_pool ( self ):
      """
      Returns True if the topmost rule pool of this interface exists
      and is not empty.
      """
      return self._poolstack and not self._poolstack[-1].empty()
   # --- end of has_nonempty_pool (...) ---

   def get_pool ( self ):
      """Returns the topmost rule pool. Creates one if necessary."""
      if self._poolstack:
         return self._poolstack[-1]
      else:
         return self.get_new_pool ( force=True )
   # --- end of get_pool (...) ---

   def _add_pool ( self, pool ):
      """Pushes a rule pool back to the poolstack, making it the topmost one.

      Returns: None (implicit)

      arguments:
      * pool -- a dependency rule pool
      """
      self._pool_id += 1
      try:
         self._poolstack.append ( pool )
      except:
         self._pool_id -= 1
         raise

      self._update_resolver()
   # --- end of _add_pool (...) ---

   def push_pool ( self, pool ):
      """Pushes a rule pool back to the poolstack, making it the topmost one.

      Returns: topmost rule pool (should be the given pool)

      arguments:
      * pool -- a dependency rule pool
      """
      # COULDFIX: pool name possibly not unique when reinserting pools
      assert isinstance ( pool, roverlay.depres.simpledeprule.pool.SimpleDependencyRulePool )
      self._add_pool ( pool )
      return self._poolstack[-1]
   # --- end of push_pool (...) ---

   def get_new_pool ( self, force=False, with_deptype=DEFAULT_DEPTYPE ):
      """Creates a new pool, adds it to the pool stack and returns it.

      arguments:
      * force        -- if True: force creation of a new pool even if the
                                 current one is empty
      * with_deptype -- dependency type of the new pool (optional)
      """
      if force or not self._poolstack or not self._poolstack[-1].empty():
         self._add_pool (
            roverlay.depres.simpledeprule.pool.SimpleDependencyRulePool (
               "pool" + str ( self._pool_id ),
               deptype_mask=with_deptype
            )
         )
      # -- end if force or ...
      return self._poolstack[-1]
   # --- end of get_new_pool (...) ---

   def pop_pool ( self ):
      """Discards the topmost rule pool and returns it.

      Returns: dependency rule pool or None (=no pool removed).
      """
      try:
         pool = self._poolstack.pop()
      except IndexError:
         # poolstack is empty
         return None

      self._pool_id -= 1
      assert self._pool_id >= -1, self._pool_id
      return pool
   # --- end of pop_pool (...) ---

   def discard_pool ( self ):
      """Discards the topmost rule pool.

      Returns: True if a pool has been removed, else False.
      """
      return self.pop_pool() is not None
   # --- end of discard_pool (...) ---

   def discard_pools ( self, count ):
      """Discards up to <count> rule pools.

      arguments:
      * count -- number of rule pool to remove

      Returns: number of rule pool that have been removed (<= count)
      """
      for i in range ( count ):
         if not self.discard_pool():
            return i
      else:
         return count
   # --- end of discard_pools (...) ---

   def discard_all_pools ( self ):
      """Discards all rule pools.

      Returns: number of removed rule pools
      """
      i = 0
      while self.discard_pool():
         i += 1
      return i
   # --- end of discard_all_pools (...) ---

   def discard_empty_pools ( self ):
      """Discards rule pools until the topmost one is not empty.

      Returns: number of removed rule pools
      """
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

   def load_rules_from_config ( self, ignore_missing=False ):
      """Loads all configured rule files into a new pool (or new pools).

      arguments:
      * ignore_missing -- if True: do not raise an Exception if
                                   SIMPLE_RULE_FILE is not set in the config

      Returns: True if rule files have been loaded, else False.
      """
      if ignore_missing:
         rule_files = self.config.get ( self.CONFIG_KEY_DEPRULES, None )
         if rule_files:
            ##return self.load_rule_files ( rule_files, ignore_missing=True )
            return self.load_rule_files ( rule_files )
         else:
            return False
      else:
         return self.load_rule_files (
            self.config.get_or_fail ( self.CONFIG_KEY_DEPRULES )
         )
   # --- end of load_rules_from_config (...) ---

   load_configured = load_rules_from_config

   def load_rule_files ( self, files_or_dirs, ignore_missing=False ):
      """Loads the given files into a new rule pool (or new pools).

      arguments:
      * ignore_missing -- suppress exceptions caused by missing files and
                          return False

      Returns: True on success, else False
      """
      if ignore_missing:
         try:
            ret = self._resolver.get_reader().read ( files_or_dirs )
         except IOError as ioerr:
            if ioerr.errno == errno.ENOENT:
               ret = False
            else:
               raise
      else:
         ret = self._resolver.get_reader().read ( files_or_dirs )

      self.fixup_pool_id()
      return True if ret is None else ret
   # --- end of load_rule_files (...) ---

   def add_rule_objects ( self, rules ):
      """Adds SimpleDependencyRule objects to the topmost rule pool.

      update() has to be called manually.

      Returns: True

      arguments:
      * rule_objects -- iterable containing dependency rules
      """
      pool = self.get_pool()
      # pool validates the rules' type
      for deprule in rules:
         pool.add ( deprule )
      return True
   # --- end of add_rule_objects (...) ---

   def add_rule_object ( self, rule ):
      """Adds a single SimpleDependencyRule object to the topmost rule pool.

      update() has to be called manually.

      arguments:
      * rule -- dependency rule
      """
      # the rule pool validates the rule's type
      self.get_pool().add ( rule )
      return True
   # --- end of add_rule_object (...) ---

   def add_rule ( self, rule_str ):
      """Sends a text line to the rule parser.

      arguments:
      * rule_str -- text line

      Returns: True

      Raises: RuleSyntaxException if rule_str cannot be parsed

      Note: rules have to be compiled via compile_rules() after adding
            text lines
      """
      if not self._parser.add ( rule_str ):
         raise RuleSyntaxException ( rule_str )
      return True
   # --- end of add_rule (...) ---

   def add_rules ( self, *rule_str_list ):
      """Sends several text lines to the rule parser.
      See add_rule() for details.

      arguments:
      * *rule_str_list --

      Returns: True
      """
      for rule_str in rule_str_list:
         self.add_rule ( rule_str )
      return True
   # --- end of add_rules (...) ---

   def add_rule_list ( self, rule_str_list ):
      """Like add_rules(), but accepts a single list-like arg.
      See add_rule()/add_rules() for details.

      arguments:
      * rule_str_list --

      Returns: True
      """
      for rule_str in rule_str_list:
         self.add_rule ( rule_str )
      return True
   # --- end of add_rule_list (...) ---

   def try_compile_rules ( self, *args, **kwargs ):
      """Tells the rule parser to 'compile' rules. Does nothing if the
      rule parser has any active context (e.g. is inside a multi line rule).
      See compile_rules() for details.

      Returns: False if rule compiling has been suppressed du to active
               context, else True (=rules compiled)
      """
      if self._parser.has_context():
         return False
      else:
         return self.compile_rules()
   # --- end of try_compile_rules (...) ---

   def compile_rules ( self, new_pool=False ):
      """Tells the rule parser to 'compile' rules. This converts the text
      input into dependency rule objects, which are then added to a rule pool.

      arguments:
      * new_pool -- create a new pool for the compiled rules

      Returns: True
      """
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
            # this could discard (previously) empty pools, too
            #  (side-effect of "optimizations" in get_new_pool())
            #
            self.discard_pool()
         raise
   # --- end of compile_rules (...) ---

   def add_immediate_rule ( self, rule_str ):
      """Directly adds a single rule (given in rule file syntax form) to
      the topmost rule pool.

      arguments:
      * rule_str -- text line

      Note: this method calls compile_rules(), which creates rule objects
            for all text lines added so far.

      Returns: True
      """
      return self.add_rule ( rule_str ) and self.compile_rules()
   # --- end of add_immediate_rule (...) ---

   def visualize_pool ( self, pool_id=None ):
      """Visualizes the topmost rule pool (or the specified one).
      his returns a string that contains all rules of this pool
      in text form (in rule file syntax).

      arguments:
      * pool_id -- index of the pool that should be visualized
                   Defaults to 0 (-> use topmost pool).

      Returns:
          visualized pool (str) if requested pool existed, else empty string
      """
      try:
         pool = self._poolstack [ -1 if pool_id is None else pool_id ]
      except IndexError:
         return ""
      else:
         return '\n'.join ( pool.export_rules() )
   # --- end of visualize_pool (...) ---

   def visualize_pools ( self, id_range=None ):
      """Visualize multiple pools at once.

      arguments:
      * id_range -- an iterable of indexes or None (-> visualize all)
                    Defaults to None.

      Returns: visualized pools (str)
      """
      if id_range is None:
         return '\n'.join (
            '\n'.join ( pool.export_rules() ) for pool in self._poolstack
         )
      else:
         return '\n'.join (
            self.visualize_pool ( pool_id ) for pool_id in id_range
         )
   # --- end of visualize_pools (...) ---

   def get_channel ( self, channel_name="channel", greedy=None ):
      """Creates, registers and returns an EbuildJobChannel suitable for
      dependency resolution.

      Note: This doesn't need to be called manually in order to resolve
            dependencies.

      arguments:
      * channel_name -- name of the channel (defaults to "channel")
      * greedy       -- whether to return a greedy or non-greedy depres
                        channel. The greedy one stops if a mandatory dep
                        cannot be resolved, whereas the non-greedy one keeps
                        going until all deps have been processed.
                        Defaults to None (=use default channel).
      """
      if greedy is None:
         channel_cls = self.default_depres_channel
      elif greedy:
         channel_cls = self.GREEDY_DEPRES_CHANNEL
      else:
         channel_cls = self.NONGREEDY_DEPRES_CHANNEL

      channel = channel_cls ( err_queue=self.err_queue, name=channel_name )
      self._resolver.register_channel ( channel )
      return channel
   # --- end of get_channel (...) ---

   def do_resolve ( self, deps, with_deptype=DEFAULT_DEPTYPE, greedy=None ):
      """Performs dependency resolution for the given dependency list and
      returns the result, which is None (=not resolved) or a 2-tuple
      (<resolved deps>, <unresolvable, but optional deps>).

      Note: use resolve() for resolving dependencies unless the 2-tuple
            result form is desired.

      arguments:
      * deps         -- dependency string list
      * with_deptype -- dependency type (optional, defaults to DEFAULT_DEPTYPE)
      * greedy       -- whether to use a greedy depres channel or not
                         Defaults to None.
      """
      channel = self.get_channel()
      # FIXME/COULDFIX: once again, hardcoded deptype
      try:
         channel.add_dependencies ( deps, with_deptype  )

         channel_result = channel.satisfy_request (
            close_if_unresolvable=False,
            preserve_order=True,
            want_tuple=self.want_tuple,
         )
      finally:
         channel.close()

      return channel_result
   # --- end of do_resolve (...) ---

   def _do_resolve_weak_greedy ( self, deps, kw, greedy=True ):
      """Calls do_resolve ( deps, **kw ) with the given greedy mode unless
      greedy is in kw.

      Passes do_resolve()'s return value.

      arguments:
      * deps   --
      * kw     --
      * greedy -- defaults to True
      """
      if 'greedy' in kw:
         return self.do_resolve ( deps, **kw )
      else:
         return self.do_resolve ( deps, greedy=greedy, **kw )
   # --- end of _do_resolve_weak_greedy (...) ---

   def resolve ( self, *deps, **kw ):
      """Like do_resolve(), but accepts the dependency string list in var-args
      form and returns None (=not resolved) or a list of resolved dependencies.

      arguments:
      * *deps -- list of dependency strings
      * **kw  -- passed to do_resolve()
      """
      result = self.do_resolve ( deps, **kw )
      # result := ( list<resolved>, list<unresolvable> )
      return None if result is None else result [0]
   # --- end of resolve (...) ---

   def can_resolve ( self, *deps, **kw ):
      """Like resolve(), but simply returns True if all dependencies could
      be resolved.

      Technically, returns True IFF all mandatory dependencies could be
      resolved.

      arguments:
      * *deps --
      * **kw  --
      """
      return (
         self._do_resolve_weak_greedy ( deps, kw, greedy=True ) is not None
      )
   # --- end of can_resolve (...) ---

   def cannot_resolve ( self, *deps, **kw ):
      """Like can_resolve(), but returns True if at least one (mandatory)
      dependency could not be resolved.

      arguments:
      * *deps --
      * **kw  --
      """
      return self._do_resolve_weak_greedy ( deps, kw, greedy=True ) is None
   # --- end of cannot_resolve (...) ---

# --- end of DepresInterface ---
