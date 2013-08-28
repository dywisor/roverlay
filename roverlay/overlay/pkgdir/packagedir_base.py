# R overlay -- overlay package, package directory
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay <-> filesystem interface (package directory)

This module provides the PackageDir base class that offers direct
PackageInfo (in memory) <-> package directory (as directory in filesystem)
access, e.g. ebuild/metadata.xml/Manifest writing as well as scanning
the existing package directory.
Each PackageDir instance represents one package name (e.g. "seewave").
"""

__all__ = [ 'PackageDirBase', ]


import os
import shutil
import sys
import threading
import weakref

import roverlay.config
import roverlay.packageinfo
import roverlay.util

import roverlay.recipe.distmap

import roverlay.tools.ebuild
import roverlay.tools.ebuildenv
import roverlay.tools.patch

import roverlay.overlay.additionsdir

import roverlay.overlay.pkgdir.distroot.static
import roverlay.overlay.pkgdir.metadata

# TODO: proper reading of $SRC_URI when importing (or scanning) ebuilds
#        This would make manifest creation being more controlled

class PackageDirBase ( object ):
   """The PackageDir base class that implements most functionality except
   for Manifest file creation."""

   #DISTROOT =
   #DISTMAP  =
   #FETCH_ENV =
   #MANIFEST_ENV =

   EBUILD_SUFFIX = '.ebuild'

   # MANIFEST_THREADSAFE (tri-state)
   # * None  -- unknown (e.g. write_manifest() not implemented)
   # * False -- write_manifest() is not thread safe
   # * True  -- ^ is thread safe
   #
   MANIFEST_THREADSAFE = None

   # a set(!) of hash types which are used by the package dir
   # implementation (if any, else None)
   #  other subsystems might calculate them in advance if advertised here
   HASH_TYPES = None

   # DOEBUILD_IMPORTMANIFEST
   #  bool that controls whether a Manifest file should be created when
   #  importing ebuilds.
   #
   DOEBUILD_IMPORTMANIFEST = False

   @classmethod
   def init_base_cls ( cls ):
      # env for calling "ebuild <ebuild file> fetch"
      overlay_dir = roverlay.config.get_or_fail ( 'OVERLAY.dir' )

      fetch_env = roverlay.tools.ebuildenv.FetchEnv()
      fetch_env.add_overlay_dir ( overlay_dir )

      mf_env = roverlay.tools.ebuildenv.ManifestEnv()
      mf_env.add_overlay_dir ( overlay_dir )

      cls.DISTROOT = roverlay.overlay.pkgdir.distroot.static.get_configured()
      cls.DISTMAP      = roverlay.recipe.distmap.access()
      cls.FETCH_ENV    = fetch_env
      cls.MANIFEST_ENV = mf_env
   # --- end of init_cls (...) ---

   def __init__ ( self,
      name, logger, directory, get_header, runtime_incremental, parent
   ):
      """Initializes a PackageDir which contains ebuilds, metadata and
      a Manifest file.

      arguments:
      * name                -- name of the directory (${PN} in ebuilds)
      * logger              -- parent logger
      * directory           -- filesystem location of this PackageDir
      * get_header          -- function that returns an ebuild header
      * runtime_incremental -- enable/disable runtime incremental ebuild
                               writing. This trades speed (disabled) for
                               memory consumption (enabled) 'cause it will
                               write _all_ successfully created ebuilds
                               directly after they've been created.
                               Writing all ebuilds at once is generally faster
                               (+threading), but all PackageInfos must be
                               kept in memory for that.
      * parent                 (pointer to) the object that is creating this
                               instance
      """
      self.logger              = logger.getChild ( name )
      self.name                = name
      self._lock               = threading.RLock()
      # { <version> : <PackageInfo> }
      self._packages           = dict()
      self.physical_location   = directory
      self.get_header          = get_header
      self.runtime_incremental = runtime_incremental

      self._metadata = roverlay.overlay.pkgdir.metadata.MetadataJob (
         filepath = self.physical_location + os.sep + 'metadata.xml',
         logger   = self.logger
      )

      # <dir>/<PN>-<PVR>.ebuild
      self.ebuild_filepath_format = (
         self.physical_location + os.sep
         + self.name + "-{PVR}" + self.__class__.EBUILD_SUFFIX
      )

      # used to track changes for this package dir
      self.modified          = False
      self._need_manifest    = False
      self._need_metadata    = False
   # --- end of __init__ (...) ---

   def iter_package_info ( self, pkg_filter=None ):
      if pkg_filter is None:
         return self._packages.values()
      else:
         return ( p for p in self._packages.values() if pkg_filter ( p ) )
   # --- end of iter_package_info (...) --

   def iter_packages_with_efile ( self ):
      return (
         p for p in self._packages.values() if p.has ( 'ebuild_file' )
      )
   # --- end of iter_packages_with_efile (...) ---

   def _remove_ebuild_file ( self, pkg_info ):
      """Removes the ebuild file of a pkg_info object.
      Returns True on success, else False.
      """
      try:
         efile = pkg_info ['ebuild_file']
         if efile is not None:
            os.unlink ( efile )
            # Manifest file has to be updated
            self._need_manifest = True
         return True
      except Exception as e:
         self.logger.exception ( e )
         return False
   # --- end of remove_ebuild_file (...) ---

   def _scan_add_package ( self, efile, pvr ):
      """Called for each ebuild that is found during scan().
      Creates a PackageInfo for the ebuild and adds it to self._packages.

      PackageInfo objects added this way are not affected by package rules.

      arguments:
      * efile -- full path to the ebuild file
      * pvr   -- version ($PVR) of the ebuild
      """
      p = roverlay.packageinfo.PackageInfo (
         physical_only=True, pvr=pvr, ebuild_file=efile, name=self.name
      )
      # TODO/FIXME: parse SRC_URI, knowledge of distfile path would be good...
      self._packages [ p ['ebuild_verstr'] ] = p
      return p
   # --- end of _scan_add_package (...) ---

   def add ( self,
      package_info, add_if_physical=False, allow_postpone=False, _lock=True
   ):
      """Adds a package to this PackageDir.

      arguments:
      * package_info    --
      * add_if_physical -- add package even if it exists as ebuild file
                            (-> overwrite old ebuilds)

      returns: success as bool // weakref

      raises: Exception when ebuild already exists.
      """
      ### revbump the package for testing
      ##package_info.revbump().revbump().revbump().revbump()

      shortver = package_info ['ebuild_verstr']
      added = False
      try:
         if _lock: self._lock.acquire()

         if shortver in self._packages:
            # package exists, check if it existed before script invocation
            if self._packages [shortver] ['physical_only']:

               if add_if_physical:
                  # else ignore ebuilds that exist as file
                  self._packages [shortver] = package_info
                  added = True

               elif allow_postpone:
                  added = None

               elif self.DISTMAP.check_revbump_necessary ( package_info ):
                  # resolve by recursion
                  added = self.add (
                     package_info.revbump(), add_if_physical=False, _lock=False
                  )

               else:
                  # TODO: get a distmap "slot"
                  #  else collision can occur when using >1 category,
                  #  e.g. per-repo categories
                  #
                  #  solutions:
                  #  (a) automatic renaming (preferably before revbumping)
                  #  (b) ignore packages
                  #
                  self.logger.debug (
                     "'{PN}-{PVR}.ebuild' exists as file, skipping.".format (
                        PN=self.name, PVR=shortver
                     )
                  )
            else:
               # package has been added to this packagedir before,
               # this most likely happens if it is available from
               # more than one repo
               self.logger.debug (
                  "'{PN}-{PVR}.ebuild' already exists, cannot add it!".format (
                  PN=self.name, PVR=shortver
                  )
               )
         else:
            self._packages [shortver] = package_info
            added = True

      finally:
         if _lock: self._lock.release()

      if added:
         # add a link to this PackageDir into the package info,
         # !! package_info <-> self (double-linked)
         package_info.overlay_package_ref = weakref.ref ( self )
         return True
      elif added is None:
         return weakref.ref ( self )
      else:
         return added
   # --- end of add (...) ---

   def check_empty ( self ):
      """Similar to empty(),
      but also removes the directory of this PackageDir.
      """
      if len ( self._packages ) == 0:
         if os.path.isdir ( self.physical_location ):
            try:
               os.rmdir ( self.physical_location )
            except Exception as e:
               self.logger.exception ( e )
         return True
      else:
         return False
   # --- end of check_empty (...) ---

   def ebuild_uncreateable ( self, package_info ):
      """Called when ebuild creation (finally) failed for a PackageInfo
      object of this PackageDir.

      arguments:
      * package_info --
      """
      try:
         self._lock.acquire()
         pvr = package_info ['ebuild_verstr']
         self.logger.debug (
            "removing {PVR} from {PN}".format ( PVR=pvr, PN=self.name )
         )
         del self._packages [pvr]
         self.generate_metadata ( skip_if_existent=False )
      except KeyError:
         pass
      finally:
         self._lock.release()
   # --- end of ebuild_uncreateable (...) ---

   def empty ( self ):
      """Returns True if no ebuilds stored, else False.
      Note that "not empty" doesn't mean "has ebuilds to write" or "has
      ebuilds written", use the modified attribute for the former, and the
      has_ebuilds() function for the latter one.
      """
      return len ( self._packages ) == 0
   # --- end of empty (...) ---

   def fs_cleanup ( self ):
      """Cleans up the filesystem location of this package dir.
      To be called after keep_nth_latest, calls finalize_write_incremental().
      """
      def rmtree_error ( function, path, excinfo ):
         """rmtree onerror function that simply logs the exception"""
         self.logger.exception ( excinfo )
      # --- end of rmtree_error (...) ---

      with self._lock:
         if os.path.isdir ( self.physical_location ) \
            and not self.has_ebuilds() \
         :
            # destroy self.physical_location
            shutil.rmtree ( self.physical_location, onerror=rmtree_error )
   # --- end of fs_cleanup (...) ---

   def generate_metadata ( self, skip_if_existent, **ignored_kw ):
      """Creates metadata for this package.

      arguments:
      * skip_if_existent -- do not create if metadata already exist
      """
      with self._lock:
         if self._metadata.empty() or not skip_if_existent:
            self._metadata.update_using_iterable ( self._packages.values() )
   # --- end of generate_metadata (...) ---

   def has_ebuilds ( self ):
      """Returns True if this PackageDir has any ebuild files (filesystem)."""
      for p in self._packages.values():
         if p ['physical_only'] or p.has ( 'ebuild' ) or p ['imported']:
            return True
      return False
   # --- end of has_ebuilds (...) ---

   def keep_nth_latest ( self, n, cautious=True ):
      """Keeps the n-th latest ebuild files, removing all other packages,
      physically (filesystem) as well as from this PackageDir object.

      arguments:
      * n        -- # of packages/ebuilds to keep
      * cautious -- if True: be extra careful, verify that ebuilds exist
                             as file; note that this will ignore all
                             ebuilds that haven't been written to the file-
                             system yet (which implies an extra overhead,
                             you'll have to write all ebuilds first)
      """
      def is_ebuild_cautious ( p_tuple ):
         # package has to have an ebuild_file that exists
         efile = p_tuple [1] ['ebuild_file' ]
         if efile is not None:
            return os.path.isfile ( efile )
         else:
            return False
      # --- end of is_ebuild_cautious (...) ---

      def is_ebuild ( p_tuple ):
         # package has to have an ebuild_file or an ebuild entry
         return (
            p_tuple [1] ['ebuild_file'] or p_tuple [1] ['ebuild']
         ) is not None
      # --- end of is_ebuild (...) ---

      # create the list of packages to iterate over (cautious/non-cautious),
      # sort them by version in reverse order
      packages = reversed ( sorted (
         filter (
            is_ebuild if not cautious else is_ebuild_cautious,
            self._packages.items()
         ),
         key=lambda p : p [1] ['version']
      ) )

      if n < 1:
         raise Exception ( "Must keep more than zero ebuilds." )

      kept   = 0
      ecount = 0

      for pvr, pkg in packages:
         ecount += 1
         if kept < n:
            self.logger.debug ( "Keeping {pvr}.".format ( pvr=pvr ) )
            kept += 1
         else:
            self.logger.debug ( "Removing {pvr}.".format ( pvr=pvr ) )
            self.purge_package ( pvr )

      self.logger.debug (
         "Kept {kept}/{total} ebuilds.".format ( kept=kept, total=ecount )
      )

      if self._need_metadata:
         self.generate_metadata ( skip_if_existent=False )

      # Manifest is now invalid,
      #  need_manifest is set to True in purge_package()
      #
      # metadata will be re-written when calling write()
      #
      # dir could be "empty" (no ebuilds),
      #  which is solved when calling fs_cleanup(),
      #  implicitly called by write()
   # --- end of keep_nth_latest (...) ---

   def list_versions ( self ):
      return self._packages.keys()
   # --- end of list_versions (...) ---

   def new_ebuild ( self ):
      """Called when a new ebuild has been created for this PackageDir."""
      self._need_manifest = True
      self._need_metadata = True
      self.modified       = True
      if self.runtime_incremental:
         with self._lock:
            return self.write_ebuilds ( overwrite=False, additions_dir=None )
      else:
         return True
   # --- end of new_ebuild (...) ---

   def purge_package ( self, pvr ):
      """Removes the PackageInfo with key pvr entirely from this PackageDir,
      including its ebuild file.
      Returns: removed PackageInfo object or None.
      """
      try:
         p = self._packages [pvr]
         del self._packages [pvr]
         self._remove_ebuild_file ( p )
         self._need_metadata = True
         return p
      except Exception as e:
         self.logger.exception ( e )
         return None
   # --- end of purge_package (...) ---

   def fs_destroy ( self ):
      """Destroys the filesystem content of this package dir."""
      pvr_list = list ( self._packages.keys() )
      for pvr in pvr_list:
         self.purge_package ( pvr )

      assert self.empty()
      self.fs_cleanup()
   # --- end of fs_destroy (...) ---

   def scan ( self, stats, **kw ):
      """Scans the filesystem location of this package for existing
      ebuilds and adds them.
      """
      def scan_ebuilds():
         """Searches for ebuilds in self.physical_location."""
         elen = len ( self.__class__.EBUILD_SUFFIX )
         def ebuild_split_pvr ( _file ):
            if _file.endswith ( self.__class__.EBUILD_SUFFIX ):
               return _file [ : - elen ].split ( '-', 1 )
            else:
               return ( None, None )
         # --- end of is_ebuild (...) ---

         # assuming that self.physical_location exists
         #  (should be verified by category.py:Category)
         for f in os.listdir ( self.physical_location ):
            try:
               # filename without suffix ~= ${PF} := ${PN}-${PVR}
               pn, pvr = ebuild_split_pvr ( f )
               if pn is None:
                  # not an ebuild
                  pass
               elif pn == self.name:
                  yield ( pvr, self.physical_location + os.sep + f )
               else:
                  # $PN does not match directory name, warn about that
                  self.logger.warning (
                     "$PN {!r} does not match directory name, ignoring {!r}.".\
                     format ( pn, f )
                  )
            except:
               self.logger.warning (
                  "ebuild {!r} has an invalid file name!".format ( f )
               )
      # --- end of scan_ebuilds (...) ---

      ebuild_found = stats.ebuilds_scanned.inc

      # ignore directories without a Manifest file
      if os.path.isfile ( self.physical_location + os.sep + 'Manifest' ):
         for pvr, efile in scan_ebuilds():
            if pvr not in self._packages:
               try:
                  self._scan_add_package ( efile, pvr )
               except ValueError as ve:
                  self.logger.error (
                     "Failed to add ebuild {!r} due to {!r}.".format (
                        efile, ve
                     )
                  )
                  raise
               else:
                  ebuild_found()
   # --- end of scan (...) ---

   def show ( self, stream=sys.stderr ):
      """Prints this dir (the ebuilds and the metadata) into a stream.

      arguments:
      * stream -- stream to use, defaults to sys.stderr

      returns: True

      raises:
      * passes all exceptions (IOError, ..)
      """
      self.write_ebuilds (
         overwrite=True, additions_dir=None, shared_fh=stream
      )
      self.write_metadata ( shared_fh=stream )
      return True
   # --- end of show (...) ---

   def virtual_cleanup ( self ):
      """Removes all PackageInfos from this structure that don't have an
      'ebuild_file' entry.
      """
      with self._lock:
         # keyset may change during this method
         for pvr in tuple ( self._packages.keys() ):
            if self._packages [pvr] ['ebuild_file'] is None:
               del self._packages [pvr]
      # -- lock
   # --- end of virtual_cleanup (...) ---

   def write ( self,
      additions_dir,
      overwrite_ebuilds=False,
      write_ebuilds=True, write_manifest=True, write_metadata=True,
      cleanup=True, keep_n_ebuilds=None, cautious=True, stats=None,
   ):
      """Writes this directory to its (existent!) filesystem location.

      arguments:
      * additions_dir     -- AdditionsDir object for this package
      * write_ebuilds     -- if set and False: don't write ebuilds
      * write_manifest    -- if set and False: don't write the Manifest file
      * write_metadata    -- if set and False: don't write the metadata file
      * overwrite_ebuilds -- whether to overwrite ebuilds,
                              None means autodetect: enable overwriting
                              if not modified since last write
                              Defaults to False
      * cleanup           -- clean up after writing
                              Defaults to True
      * keep_n_ebuilds    -- # of ebuilds to keep (remove all others),
                              Defaults to None (disable) and implies cleanup
      * cautious          -- be cautious when keeping the nth latest ebuilds,
                             this has some overhead
                             Defaults to True
      * stats             --

      returns: success (True/False)

      raises:
      * passes IOError
      """
      # NOTE, replaces:
      # * old write: overwrite_ebuilds=True
      # * finalize_write_incremental : no extra args
      # * write_incremental : write_manifest=False, write_metadata=False,
      #                        cleanup=False (or use write_ebuilds)
      # BREAKS: show(), which has its own method/function now

      cleanup = cleanup or ( keep_n_ebuilds is not None )

      success = True
      with self._lock:
         if self.has_ebuilds():
            # not cautious: remove ebuilds before writing them
            if not cautious and keep_n_ebuilds is not None:
               self.keep_nth_latest ( n=keep_n_ebuilds, cautious=False )

            # write ebuilds
            if self.modified and write_ebuilds:
               # ( overwrite == None ) <= not modified, which is not
               # possible in this if-branch
               success = self.write_ebuilds (
                  additions_dir = additions_dir,
                  overwrite     = bool ( overwrite_ebuilds ),
                  stats         = stats,
               )
#                  overwrite = overwrite_ebuilds \
#                     if overwrite_ebuilds is not None \
#                     else not self.modified


            # cautious: remove ebuilds after writing them
            if cautious and keep_n_ebuilds is not None:
               self.keep_nth_latest ( n=keep_n_ebuilds, cautious=True )

            # write metadata
            if self._need_metadata and write_metadata:
               # don't mess around with short-circuit bool evaluation
               if not self.write_metadata():
                  success = False

            # write manifest (only if shared_fh is None)
            if self._need_manifest and write_manifest:
               if not self.write_manifest ( ignore_empty=True ):
                  success = False
         # -- has_ebuilds?

         if cleanup:
            self.virtual_cleanup()
            self.fs_cleanup()

      # -- lock
      return success
   # --- end of write (...) ---

   def get_distdir ( self ):
      return self.DISTROOT.get_distdir ( self.name )
   # --- end of get_distdir (...) ---

   def get_fetch_env ( self, distdir=None ):
      return self.FETCH_ENV.get_env (
         (
            self.DISTROOT.get_distdir ( self.name )
            if distdir is None else distdir
         ).get_root()
      )
   # --- end of get_fetch_env (...) ---

   def get_manifest_env ( self, distdir=None ):
      return self.MANIFEST_ENV.get_env (
         (
            self.DISTROOT.get_distdir ( self.name )
            if distdir is None else distdir
         ).get_root()
      )
   # --- end of get_manifest_env (...) ---

   def fetch_src_for_ebuild ( self, efile, create_manifest=False ):
      fetch_env = self.get_fetch_env()

      if create_manifest:
         return roverlay.tools.ebuild.doebuild_fetch_and_manifest (
            ebuild_file = efile,
            logger      = self.logger,
            env         = fetch_env,
         )
      else:
         return roverlay.tools.ebuild.doebuild_fetch (
            ebuild_file = efile,
            logger      = self.logger,
            env         = fetch_env,
         )
   # --- end of fetch_src_for_ebuild (...) ---

   def do_ebuildmanifest ( self, ebuild_file, distdir=None ):
      """Calls doebuild_manifest().
      Returns True on success, else False. Also handles result logging.

      arguments:
      * ebuild_file -- ebuild file that should be used for the doebuild call
      * distdir     -- distdir object (optional)
      """
      try:
         call = roverlay.tools.ebuild.doebuild_manifest (
            ebuild_file, self.logger, self.get_manifest_env ( distdir ),
            return_success=False
         )
      except Exception as err:
         self.logger.exception ( err )
         raise
      # -- end try

      if call.returncode == os.EX_OK:
         self.logger.debug ( "Manifest written." )
         return True
      else:
         self.logger.error (
            'Couldn\'t create Manifest for {ebuild}! '
            'Return code was {ret}.'.format (
               ebuild=ebuild_file, ret=call.returncode
            )
         )
         return False
   # --- end of do_ebuildmanifest (...) ---

   def import_ebuilds ( self, eview, overwrite, nosync=False, stats=None ):
      """Imports ebuilds from an additions dir into this package dir.

      arguments:
      * eview      -- additions dir ebuild view
      * overwrite  -- whether to overwrite existing ebuilds or not
      * nosync     -- if True: don't fetch src files (defaults to False)
      * stats      --
      """
      if not self.physical_location:
         raise Exception (
            "import_ebuilds() needs a non-virtual package dir!"
         )
      elif not eview.has_ebuilds():
         return None


      # setup
      stats_ebuild_imported = (
         stats.ebuilds_imported.inc if stats is not None
         else ( lambda: None )
      )
      imported_ebuild_files = list()
      efile_imported = imported_ebuild_files.append

      fetch_env = self.get_fetch_env()

      roverlay.util.dodir ( self.physical_location, mkdir_p=True )
      # -- end setup

      def import_ebuild_efile ( pvr, efile_src, fname ):
         """Imports an ebuild file into this package dir and registers it
         in self._packages.

         Returns the PackageInfo instance of the imported ebuild,

         arguments:
         * pvr       --
         * efile_src -- path to the (real, non-symlink) ebuild file
         * fname     -- name of the ebuild file
         """
         # this assertion is always true (see EbuildView)
         assert fname == self.name + '-' + pvr + '.ebuild'

         efile_dest = self.physical_location + os.sep + fname

         ##efile_dest = (
         ##   self.physical_location + os.sep
         ##   + self.name + '-' + pvr + '.ebuild'
         ##)

         try:
            # copy the ebuild file
            shutil.copyfile ( efile_src, efile_dest )

            # create PackageInfo and register it
            p = roverlay.packageinfo.PackageInfo (
               imported=True, pvr=pvr, ebuild_file=efile_dest
            )
            self._packages [ p ['ebuild_verstr'] ] = p

            # manifest needs to be rewritten
            self._need_manifest = True

            # fetch SRC_URI using ebuild(1)
            if not nosync and not self.fetch_src_for_ebuild ( efile_dest ):
               raise Exception ( "doebuild_fetch() failed." )

         except:
            # this package dir is "broken" now,
            # so a new manifest would be good...
            #
            # (the program stops when importing fails,
            #  so this is a theoretical case only)
            #
            self._need_manifest = True

            if pvr in self._packages:
               self.purge_package ( pvr )

            if os.access ( efile_dest, os.F_OK ):
               os.unlink ( efile_dest )

            raise
         else:
            # imported ebuilds cannot be used for generating metadata.xml
            ##self._need_metadata = True

            stats_ebuild_imported()
            efile_imported ( efile_dest )
            return p
      # --- end of import_ebuild_efile (...) ---

      if not self._packages:
         for pvr, efile, fname in eview.get_ebuilds():
            import_ebuild_efile ( pvr, efile, fname )

      elif overwrite:
         for pvr, efile, fname in eview.get_ebuilds():
            if pvr in self._packages:
               self.purge_package ( pvr )

            import_ebuild_efile ( pvr, efile, fname )
         # -- end for

      else:
         for pvr, efile, fname in eview.get_ebuilds():
            if pvr not in self._packages:
               import_ebuild_efile ( pvr, efile, fname )

      # -- end if


      # import metadata.xml from eview
      #  in conjunction with overwrite=False, metadata.xml won't get
      #  updated even if all ebuilds are imports (since only new imports
      #  get the "imported" flag)
      #
      if eview.has_metadata_xml():
         metadata_file = self._metadata.filepath
         if not os.path.isfile ( metadata_file ) or all (
            p.get ( 'imported', False ) for p in self._packages.values()
         ):
            shutil.copyfile ( eview.get_metadata_xml(), metadata_file )
            #self._need_metadata = False
      # -- end metadata.xml import

      if imported_ebuild_files and self.DOEBUILD_IMPORTMANIFEST:
         #self.do_ebuildmanifest ( next ( iter ( imported_ebuild_files ) ))
         self.do_ebuildmanifest ( imported_ebuild_files [0] )
   # --- end of import_ebuilds (...) ---

   def write_ebuilds ( self,
      overwrite, additions_dir, shared_fh=None, stats=None
   ):
      """Writes all ebuilds.

      arguments:
      * overwrite      -- write ebuilds that have been written before
      * additions_dir  --
      * shared_fh      -- if set and not None: don't use own file handles
                           (i.e. write files), write everything into shared_fh
      * stats          --
      """
      ebuild_header = self.get_header()

      def write_ebuild ( efile, ebuild ):
         """Writes an ebuild.

         arguments:
         * efile  -- file to write
         * ebuild -- ebuild object to write (has to have a __str__ method)
         * (shared_fh from write_ebuilds())
         """
         _success = False
         try:
            fh = open ( efile, 'w' ) if shared_fh is None else shared_fh
            if ebuild_header is not None:
               fh.write ( str ( ebuild_header ) )
               fh.write ( '\n\n' )
            fh.write ( str ( ebuild ) )
            fh.write ( '\n' )

            _success = True
         except IOError as e:
            self.logger.exception ( e )
         finally:
            if shared_fh is None and 'fh' in locals() and fh:
               fh.close()

         return _success
      # --- end of write_ebuild (...) ---

      def patch_ebuild ( efile, pvr, patches ):
         """Applies zero or more patches to an ebuild (file).

         Returns True on success (all patches applied cleanly,
         where all >= 0), else False.

         Removes the ebuild file if one or more patches failed.

         arguments:
         * efile   -- path to the file that should be patched
         * pvr     -- ${PVR} of the ebuild (used for removing the ebuild)
         * patches -- list of patch files to be applied, in order
         """
         if patches:
            self.logger.info ( "Patching " + str ( efile ) )
            self.logger.debug (
               "Patches for {} (in that order): {}".format ( efile, patches )
            )

            try:
               patch_success = True

               for patch in patches:
                  patch_ret = roverlay.tools.patch.dopatch (
                     filepath=efile, patch=patch, logger=self.logger
                  )

                  if patch_ret != os.EX_OK:
                     self.logger.error (
                        "failed to apply patch {!r}!".format ( patch )
                     )
                     patch_success = False
                     break

            except Exception as err:
               # ^ which exceptions exactly?
               self.logger.exception ( err )
               patch_success = False
            # -- end try;

            if patch_success:
               return True
            else:
               self.logger.error (
                  'Removing ebuild {!r} due to errors '
                  'while patching it.'.format ( efile )
               )
               # don't set need_manifest here (not required and
               # write_manifest() would fail if no ebuild written)
               #
               ##self._need_manifest = True
               self.purge_package ( pvr )
               return False
         else:
            return True
      # --- end of patch_ebuild (...) ---

      def ebuilds_to_write():
         """Yields all ebuilds that are ready to be written."""

         for ver, p_info in self._packages.items():
            if p_info.has ( 'ebuild' ) and not p_info ['physical_only']:
               efile = self.ebuild_filepath_format.format ( PVR=ver )

               if efile != p_info ['ebuild_file'] or overwrite:
                  yield ( ver, efile, p_info )
               # else efile exists
      # --- end of ebuilds_to_write (...) ---

      all_ebuilds_written = True

      ebuild_written = (
         stats.set_ebuild_written if stats is not None else ( lambda p: None )
      )

      # don't call dodir if shared_fh is set
      hasdir = bool ( shared_fh is not None )

      if additions_dir is None:
         haspatch = None
      else:
         patchview = roverlay.overlay.additionsdir.PatchView ( additions_dir )
         haspatch  = patchview.has_patches()

      for pvr, efile, p_info in list ( ebuilds_to_write() ):
         if not hasdir:
            roverlay.util.dodir ( self.physical_location, mkdir_p=True )
            hasdir = True

         if (
            write_ebuild ( efile, p_info ['ebuild'] )
         ) and (
            not haspatch
            or patch_ebuild ( efile, pvr, patchview.get_patches ( pvr ) )
         ):

            self._need_manifest = True

            # update metadata for each successfully written ebuild
            #  (self._metadata knows how to handle this request)
            self._metadata.update ( p_info )

            if shared_fh is None:
               # this marks the package as 'written to fs'
               p_info.update_now (
                  ebuild_file=efile,
                  remove_auto='ebuild_written'
               )
               ebuild_written ( p_info )

               self.logger.info ( "Wrote ebuild {}.".format ( efile ) )
         else:
            all_ebuilds_written = False
            self.logger.error (
               "Couldn't write ebuild {}.".format ( efile )
            )

      self.modified = not all_ebuilds_written
      return all_ebuilds_written
   # --- end of write_ebuilds (...) ---

   def _write_manifest ( self, pkgs_for_manifest ):
      """Generates and writes the Manifest file for the given PackageInfo
      objects.

      arguments:
      * pkgs_for_manifest --

      expects: called in write_manifest()

      returns: success (True/False)

      """
      raise NotImplementedError (
         "_write_manifest() needs to be implemented by derived classes."
      )
   # --- end of _write_manifest (...) ---

   def write_manifest ( self, ignore_empty=False ):
      """Creates the Manifest file for this package dir.

      expects: called after writing metadata/ebuilds

      arguments:
      * ignore_empty --

      raises:
      * Exception if no ebuild exists

      returns: success (True/False)
      """

      # collect all PackageInfo instances that have enough data (PACKAGE_FILE,
      # EBUILD_FILE) for manifest creation
      pkgs_for_manifest = [
         p for p in self._packages.values()
         if p.has ( 'package_file', 'ebuild_file' )
      ]

      if pkgs_for_manifest:
         for p in pkgs_for_manifest:
            p.make_distmap_hash()
         self.logger.debug ( "Writing Manifest" )
         if self._write_manifest ( pkgs_for_manifest ):
            self._need_manifest = False
            return True
         else:
            return False

      elif (
         hasattr ( self, '_write_import_manifest' )
         and self._write_import_manifest()
      ):
         self._need_manifest = False
         return True
      elif ignore_empty:
         return True
      else:
         raise Exception (
            'In {mydir}: No ebuild written so far! '
            'I really don\'t know what do to!'.format (
               mydir=self.physical_location
         ) )
   # --- end of write_manifest (...) ---

   def write_metadata ( self, shared_fh=None ):
      """Writes metadata for this package.

      returns: success (True/False)
      """
      success = False
      try:
         self.generate_metadata ( skip_if_existent=True )

         if shared_fh is None:
            roverlay.util.dodir ( self.physical_location, mkdir_p=True )
            if self._metadata.write():
               self._need_metadata = False
               self._need_manifest = True
               success = True
            else:
               self.logger.error (
                  "Failed to write metadata file {}.".format (
                     self._metadata.filepath
                  )
               )
         else:
            self._metadata.show ( shared_fh )
            success = True
      except Exception as e:
         self.logger.exception ( e )

      return success
   # --- end of write_metadata (...) ---
