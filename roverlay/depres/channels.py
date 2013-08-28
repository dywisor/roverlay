# R overlay -- dependency resolution, channels
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""
communcation channels for dependency resolution

Implements EbuildJobChannel, which is used in ebuild.depres.
"""

__all__ = [ 'EbuildJobChannel', ]

import logging

import roverlay.depres.depresult

from roverlay.depres               import deptype
from roverlay.depres.depenv        import DepEnv
from roverlay.depres.communication import DependencyResolverChannel

COMLINK = logging.getLogger ( "depres.com" )

class _EbuildJobChannelBase ( DependencyResolverChannel ):
   """The EbuildJobChannel is an interface to the dependency resolver used
   in EbuildJobs.
   It can be used to insert dependency strings, trigger dep resolution,
   poll until done and collect the dependencies afterwards.

   Note that this channel has a strict control flow:
     add deps, then satisfy_request(): collect/lookup
   """

   def __init__ ( self, err_queue, name=None, logger=None ):
      """EbuildJobChannel

      arguments:
      * name -- name of this channel, optional
      * logger --
      """
      super ( _EbuildJobChannelBase, self ) . __init__ ( main_resolver=None )

      # this is the number of resolved deps so far,
      # should only be modified in the join()-method
      self._depdone = 0

      self.err_queue = err_queue

      # set of portage packages (resolved deps)
      #  this is None unless all deps have been successfully resolved
      self._collected_deps    = None
      self._unresolvable_deps = None

      # used to communicate with the resolver
      self._depres_queue   = None

      # the count of dep strings ever assigned to this channel
      self._depcount = 0

      _logger = logger if logger is not None else COMLINK
      if name:
         self.name   = name
         self.logger = _logger.getChild ( 'channel.' + name )
      else:
         self.logger = _logger.getChild ( 'channel' )
   # --- end of __init__ (...) ---

   def close ( self ):
      """Closes this channel."""
      if self._depdone >= 0:
         # else already closed

         super ( _EbuildJobChannelBase, self ).close()
         self.err_queue.remove_queue ( self._depres_queue )
         del self._collected_deps, self._depres_queue
         del self.logger

         self._depdone = -1
         self._collected_deps = None
   # --- end of close (...) ---

   def set_resolver ( self, resolver, channel_queue, **extra ):
      """Assigns a resolver to this channel.

      arguments:
      * resolver      --
      * channel_queue -- the queue where the resolver puts processed DepEnvs in
      * **extra       -- ignored;
      """
      if self._depres_master is None:
         self._depres_master = resolver
         self._depres_queue  = channel_queue
         self.err_queue.attach_queue ( self._depres_queue, None )
      else:
         raise Exception ( "channel already bound to a resolver." )
   # --- end of set_resolver (...) ---

   def add_dependency ( self, dep_str, deptype_mask ):
      """Adds a dependency string that should be looked up.
      This channel will create a "dependency environment" for it and enqueues
      that in the dep resolver.

      arguments:
      * dep_str --

      raises: Exception if this channel is done

      returns: None (implicit)
      """
      if self._depdone:
         raise Exception (
            "This channel is 'done', it doesn't accept new dependencies."
         )
      else:
         for dep_env in DepEnv.from_str (
            dep_str=dep_str, deptype_mask=deptype_mask
         ):
            self._depcount += 1
            self._depres_master.enqueue ( dep_env, self.ident )

   # --- end of add_dependency (...) ---

   def add_dependencies ( self, dep_list, deptype_mask ):
      """Adds dependency strings to this channel. See add_dependency (...)
      for details.

      arguments:
      * dep_list --

      raises: passes Exception if this channel is done

      returns: None (implicit)
      """
      for dep_str in dep_list:
         self.add_dependency ( dep_str=dep_str, deptype_mask=deptype_mask )
   # --- end of add_dependencies (...) ---

   def add_dependencies_filtered (
      self, dep_list, deptype_mask, common_blacklist, specific_blacklist
   ):
      if common_blacklist:
         if specific_blacklist:
            for dep_str in dep_list:
               if (
                  dep_str not in common_blacklist and
                  dep_str not in specific_blacklist
               ):
                  self.add_dependency ( dep_str, deptype_mask )

         else:
            for dep_str in dep_list:
               if dep_str not in common_blacklist:
                  self.add_dependency ( dep_str, deptype_mask )

      elif specific_blacklist:
         for dep_str in dep_list:
            if dep_str not in specific_blacklist:
               self.add_dependency ( dep_str, deptype_mask )
      else:
         for dep_str in dep_list:
            self.add_dependency ( dep_str, deptype_mask )
   # --- end of add_dependencies_filtered (...) ---


   def collect_dependencies ( self ):
      """Returns a list that contains all resolved deps,
      including ignored deps that resolve to None.

      You have to call satisfy_request(...) before using this method.

      raises: Exception
      """
      if self._collected_deps is not None:
         self.logger.debug (
            "returning collected deps: {}.".format ( self._collected_deps )
         )
         return ( self._collected_deps, self._unresolvable_deps )
      raise Exception ( "cannot do that" )
   # --- end of collect_dependencies (...) ---

   def satisfy_request ( self, *args, **kw ):
      raise Exception ( "method stub" )


class EbuildJobChannel ( _EbuildJobChannelBase ):


   def satisfy_request ( self,
      close_if_unresolvable=True, preserve_order=False, want_tuple=True
   ):
      """Tells to the dependency resolver to run.
      Blocks until this channel is done, which means that either all
      deps are resolved or a mandatory one is unresolvable.

      arguments:
      * close_if_unresolvable -- close the channel if one dep is unresolvable
                                 this seems reasonable and defaults to True
      * preserve_order        -- if set and True:
                                 return resolved deps as list or tuple,
                                 not as frozenset
                                 Note that this doesn't filter out duplicates!
      * want_tuple            -- sets the return type for preserve_order

      Returns a 2-tuple ( <resolved dependencies>, <unresolvable dep strings> )
      if all mandatory dependencies could be resolved, else None.
      <Unresolvable dep strings> will be None unless optional dependencies
      could not be resolved.
      """
      dep_collected     = list()
      dep_unresolvable = list()
      resolved          = dep_collected.append
      unresolvable      = dep_unresolvable.append

      def handle_queue_item ( dep_env ):
         self._depdone += 1
         ret = False
         if dep_env is None:
            # queue unblocked -> on_error mode, return False
            #ret = False
            pass
         elif dep_env.is_resolved():
            # successfully resolved
            resolved ( dep_env.get_resolved() )
            ret = True
         elif deptype.mandatory & ~dep_env.deptype_mask:
            # not resolved, but deptype has no mandatory bit set
            #  => dep is not required, resolve it as "not resolved"
            #     and add it to the list of unresolvable deps
            resolved ( roverlay.depres.depresult.DEP_NOT_RESOLVED )
            unresolvable ( dep_env.dep_str )
            ret = True
         # else failed

         self._depres_queue.task_done()
         return ret
      # --- end of handle_queue_item (...) ---

      satisfiable = True

      # loop until
      #  (a) at least one required dependency could not be resolved or
      #  (b) all deps processed or
      #  (c) error queue not empty
      while self._depdone < self._depcount and \
         satisfiable and self.err_queue.empty \
      :
         # tell the resolver to start
         self._depres_master.start()

         # wait for one result at least
         satisfiable = handle_queue_item ( self._depres_queue.get() )

         # and process all available results
         while satisfiable and not self._depres_queue.empty():
            satisfiable = handle_queue_item ( self._depres_queue.get_nowait() )
      # --- end while

      if satisfiable and self.err_queue.empty:
         # using a set allows easy difference() operations between
         # DEPEND/RDEPEND/.. later, seewave requires sci-libs/fftw
         # in both DEPEND and RDEPEND for example
         self._collected_deps    = frozenset ( dep_collected )
         self._unresolvable_deps = frozenset ( dep_unresolvable ) \
            if len ( dep_unresolvable ) > 0 else None

         if preserve_order:
            if want_tuple:
               return (
                  tuple ( dep_collected ),
                  tuple ( dep_unresolvable ) if dep_unresolvable else None
               )
            else:
               return ( dep_collected, dep_unresolvable or None )
         else:
            return ( self._collected_deps, self._unresolvable_deps )
      else:
         if close_if_unresolvable: self.close()
         return None
   # --- end of satisfy_request (...) ---

# --- end of EbuildJobChannel ---

class NonGreedyDepresChannel ( _EbuildJobChannelBase ):

   def handle_request ( self,
      preserve_order, allow_close=True, want_tuple=True
   ):
      """Tells to the dependency resolver to run.
      Blocks until this channel is done, which means that all deps have been
      processed, whether successful or not.

      arguments:

      * preserve_order -- if True: return resolved deps as list or tuple,
                                   not as frozenset
                          Note that this doesn't filter out duplicates!
      * allow_close    -- whether to allow automatic close() on error
                          Defaults to True.
      * want_tuple     -- sets the return type for preserve_order

      Returns a 3-tuple
      ( <satisfiable>, <resolved dependencies>, <unresolvable dep strings> )

      Also stores resolved/unresolvable deps in self._collected_deps,
      self._unresolvable_deps.

      Automatically closes this channel if on-error mode and returns a
      3-tuple (None,None,None) unless allow_close is set to False.
      """
      dep_collected     = list()
      dep_unresolvable = list()
      resolved          = dep_collected.append
      unresolvable      = dep_unresolvable.append

      def handle_queue_item ( dep_env ):
         self._depdone += 1

         if dep_env is None:
            # queue unblocked -> on_error mode, return False
            #ret = False
            ret = None
         elif dep_env.is_resolved():
            # successfully resolved
            resolved ( dep_env.get_resolved() )
            ret = True
         else:
            # dep_env not resolved,
            #  resolve it as "not resolved" (placeholder if preserve_order)
            #  and add it to the list of unresolvable deps
            # return false if mandatory bit is set
            if preserve_order:
               resolved ( roverlay.depres.depresult.DEP_NOT_RESOLVED )
            unresolvable ( dep_env.dep_str )
            ret = bool ( deptype.mandatory & ~dep_env.deptype_mask )

         self._depres_queue.task_done()
         return ret
      # --- end of handle_queue_item (...) ---

      satisfiable = True
      process_dep_result = True

      # loop until
      #  (a) satisfiable is None (= on_error mode) or
      #  (b) all deps processed or
      #  (c) error queue not empty
      while (
         ( satisfiable is not None ) and
         self._depdone < self._depcount and self.err_queue.empty
      ):
         # tell the resolver to start
         self._depres_master.start()

         # wait for one result at least
         process_dep_result = handle_queue_item ( self._depres_queue.get() )
         if process_dep_result is None:
            satisfiable = None
         elif process_dep_result is False:
            satisfiable = False

         # and process all available results
         while ( satisfiable is not None ) and not self._depres_queue.empty():
            process_dep_result = handle_queue_item (
               self._depres_queue.get_nowait()
            )
            if process_dep_result is None:
               satisfiable = None
            elif process_dep_result is False:
               satisfiable = False
      # --- end while

      if allow_close and (
         not self.err_queue.empty or satisfiable is None
      ):
         self.close()
         return ( None, None, None )
      elif preserve_order:
         if want_tuple:
            # COULDFIX: tests/depres expects tuples for comparision
            self._collected_deps    = tuple ( dep_collected )
            self._unresolvable_deps = tuple ( dep_unresolvable )
         else:
            self._collected_deps    = dep_collected
            self._unresolvable_deps = dep_unresolvable
      else:
         self._collected_deps    = frozenset ( dep_collected )
         self._unresolvable_deps = frozenset ( dep_unresolvable )

      return ( satisfiable, self._collected_deps, self._unresolvable_deps )
   # --- end of handle_request (...) ---

   def satisfy_request ( self,
      close_if_unresolvable=True, preserve_order=False, want_tuple=True
   ):
      """Tells to the dependency resolver to run.
      Blocks until this channel is done, which means that all deps have been
      processed, whether successful or not.

      arguments:
      * close_if_unresolvable -- close the channel if one dep is unresolvable
                                 this seems reasonable and defaults to True
      * preserve_order        -- if set and True:
                                 return resolved deps as tuple,
                                 not as frozenset
                                 Note that this doesn't filter out duplicates!
      * want_tuple            -- sets the return type for preserve_order

      Returns a 2-tuple
         ( <resolved dependencies>, <unresolvable dep strings>|None )
      if all mandatory deps could be resolved, else None.

      Calls handle_request() for doing the actual work. This is a compat
      function that provides a common interface for ebuild creation jobs,
      consider using handle_request() directly.
      """
      satisfiable, dep_resolved, dep_unresolable = self.handle_request (
         preserve_order=preserve_order, allow_close=close_if_unresolvable,
         want_tuple=want_tuple
      )

      if satisfiable and self.err_queue.empty:
         return ( self._collected_deps, self._unresolvable_deps or None )
      elif satisfiable is None or not close_if_unresolvable:
         # already closed or don't close
         return None
      else:
         self.close()
         return None
   # --- end of satisfy_request (...) ---

# --- end of NonGreedyDepresChannel ---
