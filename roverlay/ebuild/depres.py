# R overlay -- ebuild creation, dependency resolution
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import print_function
# TODO: remove import ^

"""ebuild dependency resolution

This module handles ebuild-side dependency resolution (i.e. initialize
communication to the dependency resolver, queues dependencies, wait for
resolution and use results, whether successfully resolved or not).
"""

__all__ = [ 'EbuildDepRes', ]

from roverlay        import config
from roverlay.depres import deptype
from roverlay.ebuild import evars, depfilter

FIELDS_TO_EVAR = {
   'R_SUGGESTS' : ( 'Suggests', ),
   'DEPEND'     : ( 'Depends', 'Imports' ),
   'RDEPEND'    : ( 'LinkingTo', 'SystemRequirements' ),
   # ? : ( 'Enhances', )
}

# setting per-field dep types here, in accordance with
#  http://cran.r-project.org/doc/manuals/R-exts.html#The-DESCRIPTION-file
FIELDS = {

   # "The Depends field gives a comma-separated
   #  list of >>package names<< which this package depends on."
   'Depends'            : deptype.PKG,

   # "Other dependencies (>>external to the R system<<)
   #  should be listed in the SystemRequirements field"
   'SystemRequirements' : deptype.SYS,

   # "The Imports field lists >>packages<< whose namespaces
   #  are imported from (as specified in the NAMESPACE file)
   #  but which do not need to be attached."
   'Imports'            : deptype.PKG,

   # "The Suggests field uses the same syntax as Depends
   #  and lists >>packages<< that are >>not necessarily needed<<."
   'Suggests'           : deptype.internal,

   # "A package that wishes to make use of header files
   #  in other >>packages<< needs to declare them as
   #  a comma-separated list in the field LinkingTo in the DESCRIPTION file."
   'LinkingTo'          : deptype.PKG,
}

def create_use_expand_var ( *args, **kwargs ):
   return evars.R_SUGGESTS_USE_EXPAND (
      config.get_or_fail ( "EBUILD.USE_EXPAND.name" ),
      *args,
      use_expand_map=config.access().get_use_expand_map(),
      **kwargs
   )

EBUILDVARS = {
   'R_SUGGESTS' : create_use_expand_var,
   'DEPEND'     : evars.DEPEND,
   'RDEPEND'    : evars.RDEPEND,
}


class DepResultIterator ( object ):
   """A dependency result iterator meant for debugging only."""
   # meant for testing/debugging only,
   #  since (mandatory) deps should always be valid
   #  (and therefore direct access to the iterable is sufficient)
   #

   # a list of package names that should trigger "possibly broken" behavior
   # (see below)
   WATCHLIST = frozenset ({
   })

   def __init__ ( self, deps ):
      super ( DepResultIterator, self ).__init__()
      self.deps = deps
   # --- end of __init__ (...) ---

   def possibly_broken ( self, dep ):
      print ( "--- POSSIBLY BROKEN SELFDEP FOUND ---" )
      print (
         dep.dep,
         dep.version if dep.fuzzy else "<any version does it>",
         repr ( dep.version_compare ) if dep.fuzzy else "<no v-compare>",
         dep.candidates,
         [ c.get ( 'version' ) for c in dep.candidates ]
      )
      print ( "--- SNIP ---" )
   # --- end of possibly_broken (...) ---

   def __iter__ ( self ):
      for dep in self.deps:
         if dep.is_valid():
            # FIXME/REMOVE: debug code
            if dep.is_selfdep and dep.package in self.WATCHLIST:
               self.possibly_broken ( dep )
            yield dep
         else:
            raise Exception (
               "unsatisfied mandatory selfdep found: " + str ( dep )
            )
   # --- end of __iter__ (...) ---

# --- end of DepResultIterator ---


class OptionalSelfdepIterator ( object ):
   def __init__ ( self, deps ):
      super ( OptionalSelfdepIterator, self ).__init__()
      self.deps        = deps
      self.missingdeps = set()
   # --- end of __init__ (...) ---

   def __iter__ ( self ):
      dep_missing = self.missingdeps.add

      for dep in self.deps:
         if dep.is_valid():
            yield dep
         else:
            # !!! COULDFIX
            #  dep.dep is a depend atom, whereas the usual missingdeps
            #  entries are dependency strings
            #
            dep_missing ( dep.dep )
   # --- end of __iter__ (...) ---

# --- end of OptionalSelfdepIterator ---


class EbuildDepRes ( object ):
   """Handles dependency resolution for a single ebuild."""

   def __init__ (
      self, package_info, logger, depres_channel_spawner, err_queue,
      run_now=True,
   ):
      """Initializes an EbuildDepRes.

      arguments:
      * package_info           --
      * logger                 -- parent logger
      * depres_channel_spawner -- used to get channels to the dep resolver
      * create_iuse            -- create an IUSE evar (if True)
      * run_now                -- immediately start after initialization
      """
      self.logger       = logger.getChild ( 'depres' )
      self.package_info = package_info

      self.request_resolver = depres_channel_spawner

      # > 0 busy/working; 0 == done,success; < 0 done,fail
      self.status       = 1
      self.depmap       = None
      self.missingdeps  = None
      self.has_suggests = None
      self.err_queue    = err_queue
      self._channels    = None

      if run_now:
         self.resolve()

   # --- end of __init__ (...) ---

   #def done    ( self ) : return self.status  < 1
   #def busy    ( self ) : return self.status  > 0
   def success ( self ) : return self.status == 0
   #def fail    ( self ) : return self.status  < 0

   def resolve ( self ):
      """Try to make/get dependency resolution results. Returns None."""
      try:
         self.missingdeps = None
         self.depmap = None
         self._init_channels()

         if self._wait_resolve():
            self._make_result()
            self.status = 0
         else:
            # unresolvable
            self.logger.info ( "Cannot satisfy dependencies!" )

            self.missingdeps = None
            self.depmap = None
            self.status = -5

      finally:
         self._close_channels()
   # --- end of resolve (...) ---

   def _get_channel ( self, dependency_type ):
      """Creates and returns a communication channel to the dep resolver."""
      if dependency_type not in self._channels:
         self._channels [dependency_type] = self.request_resolver (
            name=dependency_type,
            logger=self.logger,
            err_queue=self.err_queue,
         )
      return self._channels [dependency_type]
   # --- end of get_channel (...) ---

   def _init_channels ( self ):
      """Initializes the resolver channels, one for each existing
      dependency type. Queues dependencies, too.
      """
      # collect dep strings and initialize resolver channels

      if self.request_resolver is None:
         self.logger.warning (
            "Cannot resolve dependencies, no resolver available!"
         )
         return True

      desc = self.package_info ['desc_data']
      self._channels = dict()

      dep_type = desc_field = None

      for dep_type in FIELDS_TO_EVAR:
         resolver = None

         for desc_field in FIELDS_TO_EVAR [dep_type]:
            if desc_field in desc:
               if not resolver:
                  resolver = self._get_channel ( dep_type )

               resolver.add_dependencies (
                  dep_list     = desc [desc_field],
                  deptype_mask = FIELDS [desc_field]
               )
      # -- for dep_type
   # --- end of _init_channels (...) ---

   def _close_channels ( self ):
      """Closes the resolver channels."""
      if self._channels is None: return

      for channel in self._channels.values(): channel.close()
      del self._channels

      self._channels = None
   # --- end of _close_channels (...) ---

   def _wait_resolve ( self ):
      """Wait for dep resolution."""
      # True if no channels
      for c in self._channels.values():
         if c.satisfy_request() is None:
            return False
      return True
   # --- end of _wait_resolve (...) ---

   def _make_result ( self ):
      """Make evars using the depres result."""

      # <ebuild varname> => <deps>
      depmap = dict()
      unresolvable_optional_deps = set()

      for dep_type, channel in self._channels.items():
         channel_result = channel.collect_dependencies()
         deps = set ( filter ( depfilter.dep_allowed, channel_result[0] ) )

         if deps:
            self.logger.debug ( "adding {deps} to {depvar}".format (
               deps=deps, depvar=dep_type
            ) )
            depmap [dep_type] = deps
         # else: (effectively) no dependencies for dep_type

         if channel_result[1]:
            unresolvable_optional_deps |= channel_result[1]

      self._close_channels()

      # remove redundant deps (DEPEND in RDEPEND, RDEPEND,DEPEND in R_SUGGESTS)
      if 'RDEPEND' in depmap and 'DEPEND' in depmap:
         depmap ['RDEPEND'] -= depmap ['DEPEND']
         if not depmap ['RDEPEND']:
            del depmap ['RDEPEND']

      self.has_suggests = False
      if 'R_SUGGESTS' in depmap:
         if 'RDEPEND' in depmap:
            depmap ['R_SUGGESTS'] -= depmap ['RDEPEND']
         if 'DEPEND' in depmap:
            depmap ['R_SUGGESTS'] -= depmap ['DEPEND']

         if depmap ['R_SUGGESTS']:
            self.has_suggests = True
         else:
            del depmap ['R_SUGGESTS']


      self.depmap = depmap
      if unresolvable_optional_deps:
         self.missingdeps = unresolvable_optional_deps
   # --- end of _make_result (...) ---

   def get_optional_selfdeps ( self, prepare=True ):
      if 'R_SUGGESTS' in self.depmap:
         if prepare:
            for r in self.depmap ['R_SUGGESTS']:
               if r.is_selfdep:
                  r.prepare_selfdep_reduction()
                  yield r
         else:
            for r in self.depmap ['R_SUGGESTS']:
               if r.is_selfdep:
                  yield r
   # --- end of get_optional_selfdeps (...) ---

   def get_mandatory_selfdeps ( self, prepare=True ):
      # branch depth = 6, ouch
      if prepare:
         for dep_name, deps in self.depmap.items():
            if dep_name != 'R_SUGGESTS':
               for dep_result in deps:
                  if dep_result.is_selfdep:
                     dep_result.prepare_selfdep_reduction()
                     yield dep_result
      else:
         for dep_name, deps in self.depmap.items():
            if dep_name != 'R_SUGGESTS':
               for dep_result in deps:
                  if dep_result.is_selfdep:
                     yield dep_result
   # --- end of get_mandatory_selfdeps (...) ---

   def get_evars ( self ):
      depmap       = self.depmap
      evar_list    = list()
      has_suggests = self.has_suggests

      if 'DEPEND' in depmap:
         evar_list.append (
            EBUILDVARS ['DEPEND'] (
               #DepResultIterator ( depmap ['DEPEND'] ),
               depmap ['DEPEND'],
               using_suggests=has_suggests, use_expand=True
            )
         )

      if 'RDEPEND' in depmap:
         evar_list.append (
            EBUILDVARS ['RDEPEND'] (
               #DepResultIterator ( depmap ['RDEPEND'] ),
               depmap ['RDEPEND'],
               using_suggests=has_suggests, use_expand=True
            )
         )
      elif has_suggests or 'DEPEND' in depmap:
         evar_list.append (
            EBUILDVARS ['RDEPEND'] (
               None, using_suggests=has_suggests, use_expand=True
            )
         )


      missing_deps = self.missingdeps
      if has_suggests:
         # TODO: add unsatisfiable^optional selfdeps to MISSINGDEPS below
         selfdep_iter = OptionalSelfdepIterator ( depmap [ 'R_SUGGESTS'] )

         evar_list.append (
            EBUILDVARS ['R_SUGGESTS'] (
               selfdep_iter, using_suggests=True, use_expand=True
            )
         )

         if selfdep_iter.missingdeps:
            if missing_deps:
               evar_list.append (
                  evars.MISSINGDEPS (
                     missing_deps | selfdep_iter.missingdeps, do_sort=True
                  )
               )
            else:
               evar_list.append (
                  evars.MISSINGDEPS ( selfdep_iter.missingdeps, do_sort=True )
               )
         elif missing_deps:
            evar_list.append (
               evars.MISSINGDEPS ( missing_deps, do_sort=True )
            )
      elif missing_deps:
         evar_list.append (
            evars.MISSINGDEPS ( missing_deps, do_sort=True )
         )

      return evar_list
   # --- end of get_evars (...) ---
