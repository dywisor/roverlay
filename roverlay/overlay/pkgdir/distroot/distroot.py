# R overlay -- overlay package, root of distdirs
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [
   'TemporaryDistroot', 'PersistentDistroot',
]

import atexit
import errno
import logging
import os
import shutil
import tempfile


import roverlay.db.distmap
import roverlay.overlay.pkgdir.distroot.distdir
import roverlay.util.hashpool
import roverlay.util.objects


class DistrootBase ( object ):
   """Base class for distroots."""

   HASHPOOL_JOB_COUNT = 2

   def __repr__ ( self ):
      return "{name}<root={root}>".format (
         name = self.__class__.__name__,
         root = self.get_root()
      )
   # --- end of __repr__ (...) ---

   def __str__ ( self ):
      return self.get_root()
   # --- end of __str__ (...) ---

   def __init__ ( self, root, flat, logger=None, distmap=None ):
      """DistrootBase constructor.

      arguments:
      * root    -- root directory
      * flat    -- whether to use a flat structure (all packages in a single
                    directory, True) or per-package sub directories (False)
      * logger  --
      * distmap --
      """
      super ( DistrootBase, self ).__init__()
      self.logger = logger or logging.getLogger ( self.__class__.__name__ )
      self._root  = root
      # or use hasattr ( self, '_default_distdir' )
      self._flat  = flat

      self.distmap = distmap

      if flat:
         self._default_distdir = (
            roverlay.overlay.pkgdir.distroot.distdir.Distdir ( self )
         )

      if not os.path.isdir ( self._root ):
         os.makedirs ( self._root, 0o755 )

      self._prepare()

      # python 2's atexit has no unregister()
      #  using a "guardian" function + a bool
      self.finalize_at_exit = True
      atexit.register ( self._atexit_run )
   # --- end of __init__ (...) ---

   def _atexit_run ( self ):
      if self.finalize_at_exit:
         self.finalize()
   # --- end of _atexit_run (...) ---

   def finalize ( self, backup_distmap=True ):
      # disable finalize_at_exit first so that exceptions cannot trigger
      # _atexit_run()->this function
      #
      self.logger.info ( "finalizing" )
      self.finalize_at_exit = False

      self._cleanup()
      if self.distmap is not None:
         if backup_distmap:
            self.distmap.backup_and_write ( force=False )
         else:
            self.distmap.write ( force=False )
   # --- end of finalize (...) ---

   @roverlay.util.objects.abstractmethod
   def _add ( self, src, dest ):
      """Adds src to the distroot.

      This method should be called by distdir objects.

      arguments:
      * src --
      * dest --
      """
      pass
   # --- end of _add (...) ---

   def _add_symlink ( self, src, dest, filter_exceptions=False ):
      """Adds src as symbolic link to the distroot.

      Returns True if the operation succeeded and False if an exception has
      been filtered out ("symlinks are not supported - try something else").
      Any other exception will be passed.

      arguments:
      * src --
      * dest --
      * filter_exceptions --
      """

      if os.path.lexists ( dest ):
         # safe removal
         os.unlink ( dest )
      elif os.path.exists ( dest ):
         # unsafe removal (happens when switching from e.g. hardlinks)
         # FIXME log this
         os.unlink ( dest )

      if filter_exceptions:
         try:
            os.symlink ( src, dest )
         except OSError as err:
            if err.errno == errno.EPERM:
               # fs does not support symlinks
               return False
            else:
               raise
      else:
         os.symlink ( src, dest )

      return True
   # --- end of _add_symlink (...) ---

   def _add_hardlink ( self, src, dest, filter_exceptions=False ):
      """Adds src as hard link to the distroot.

      Returns True if the operation succeeded and False if an exception has
      been filtered out ("hardlinks are not supported").
      Any other exception will be passed.

      arguments:
      * src --
      * dest --
      * filter_exceptions --
      """
      self._try_remove ( dest )

      if filter_exceptions:
         try:
            os.link ( src, dest )
         except OSError as err:
            if err.errno == errno.EXDEV or err.errno == errno.EPERM:
               # cross-device link or filesystem does not support hard links
               return False
            else:
               raise
      else:
         os.link ( src, dest )

      return True
   # --- end of _add_hardlink (...) ---

   def _add_file ( self, src, dest, filter_exceptions=False ):
      """Copies src to the distroot.

      Returns True if the operation succeeded and False if an exception has
      been filtered out ("copy is not supported").
      Any other exception will be passed.

      arguments:
      * src --
      * dest --
      * filter_exceptions --

      *** this function is DISABLED; it will always raise an Exception ***
      """
      raise NotImplementedError ( "copy is disabled" )
#      # TODO: check whether copying is necessary
#      self._try_remove ( dest )
#      shutil.copyfile ( src, dest )
#      return True
   # --- end of _add_file (...) ---

   def _cleanup ( self ):
      """Cleans up this distroot."""
      pass
   # --- end of _cleanup (...) ---

   def _prepare ( self ):
      """Prepares the distroot."""
      pass
   # --- end of _prepare (...) ---

   def iter_distfiles ( self, distfile_only ):
      def recursive_iter ( root_abspath, root_relpath ):
         for item in os.listdir ( root_abspath ):
            abspath = root_abspath + os.sep + item
            relpath = (
               item if root_relpath is None
               else root_relpath + os.sep + item
            )
            if os.path.isdir ( abspath ):
               for result in recursive_iter ( abspath, relpath ):
                  yield result
            else:
               yield ( abspath, relpath )
      # --- end of recursive_iter (...) ---

      if distfile_only:
         for pkgfile, distfile in recursive_iter ( self.get_root(), None ):
            yield distfile
      else:
         for pkgfile, distfile in recursive_iter ( self.get_root(), None ):
            yield ( pkgfile, distfile )
   # --- end of iter_distfiles (...) ---

   def _remove_broken_symlinks ( self ):
      """Recursively remove broken/dead symlinks."""

      def recursive_remove ( dirpath, rel_dirpath, rmdir ):
         for item in os.listdir ( dirpath ):
            fpath   = dirpath + os.sep + item
            relpath = (
               item if rel_dirpath is None else rel_dirpath + os.sep + item
            )

            if not os.path.exists ( fpath ):
               # drop broken symlink
               self.logger.debug (
                  "Removing broken symlink {!r}".format ( fpath )
               )
               os.unlink ( fpath )
               if self.distmap is not None:
                  self.distmap.try_remove ( relpath )
            elif os.path.isdir ( fpath ):
               recursive_remove ( fpath, relpath, True )
               if rmdir:
                  try:
                     os.rmdir ( fpath )
                  except OSError:
                     pass
         # -- end for
      # --- end of recursive_remove (...) ---

      return recursive_remove ( self.get_root(), None, False )
   # --- end of _remove_broken_symlinks (...) ---

   def _try_remove ( self, dest ):
      try:
         os.unlink ( dest )
         if self.distmap is not None:
            relpath = os.path.relpath ( dest, self.get_root() )

      except OSError as e:
         if e.errno == errno.ENOENT:
            pass
         else:
            raise
   # --- end of _try_remove (...) ---

   def get_distdir ( self, ebuild_name ):
      """Returns a distdir instance for given package.

      arguments:
      * package_name -- name of the ebuild (${PN}) for which a distdir will
                        be created. A "flat" distdir will be returned if this
                        is none.
      """
      if self._flat:
         assert self._default_distdir._distroot is self
         return self._default_distdir
      elif ebuild_name is None:
         return roverlay.overlay.pkgdir.distroot.distdir.Distdir ( self )
      else:
         return roverlay.overlay.pkgdir.distroot.distdir.PackageDistdir (
            self, ebuild_name
         )
   # --- end of get_distdir (...) ---

   def get_root ( self ):
      return str ( self._root )
   # --- end of get_root (...) ---

   def distmap_register ( self, p_info ):
      return self.distmap.add_entry_for ( p_info )
   # --- end of distmap_register (...) ---

   def check_integrity ( self ):
      if self.distmap is not None:
         root      = self.get_root()
         distfiles = set()
         distmap_hashtype = self.distmap.get_hash_type()
         checkfile = self.distmap.check_digest_integrity

         self.logger.info ( "calculating file hashes" )

         hash_pool = roverlay.util.hashpool.HashPool (
            ( distmap_hashtype, ), self.HASHPOOL_JOB_COUNT, use_threads=True
         )

         for abspath, relpath in self.iter_distfiles ( False ):
            hash_pool.add ( relpath, abspath, None )

         for relpath, hashdict in hash_pool.run_as_completed():
            status = checkfile ( relpath, hashdict[distmap_hashtype] )

            if status == 0:
               self.logger.debug (
                  "file has been verified: {!r}".format ( relpath )
               )
               distfiles.add ( relpath )
            elif status == 1:
               # file not in distmap
               self.logger.info (
                  "file not in distmap, creating dummy entry: {!r}".format ( relpath )
               )
               self.distmap.add_dummy_entry ( relpath, hashdict=hashdict )
               distfiles.add ( relpath )
            elif status == 2:
               # file in distmap, but not valid - remove it from distmap
               self.logger.warning (
                  "digest mismatch: {!r}".format ( relpath )
               )
               self.distmap.remove ( relpath )
         # -- end for

         distmap_keys = frozenset ( self.distmap.keys() )

         if distfiles:
            # reverse compare
            for distfile in distmap_keys:
               if distfile not in distfiles:
                  self.logger.warning (
                     "distmap file does not exist: {!r}".format ( distfile )
                  )
                  self.distmap.remove ( distfile )

         else:
            # no files from distroot in distmap -- invalidate distmap
            for distfile in distmap_keys:
               self.logger.warning (
                  "distmap file does not exist: {!r}".format ( distfile )
               )
               self.distmap.remove ( distfile )
      else:
         raise Exception ( "check_integrity() needs a distmap." )
   # --- end of check_integrity (...) ---

   @roverlay.util.objects.abstractmethod
   def set_distfile_owner ( self, backref, distfile ):
      pass
   # --- end of set_distfile_owner (...) ---

# --- end of DistrootBase ---


class TemporaryDistroot ( DistrootBase ):

   def __init__ ( self, logger=None ):
      # temporary distroots always use the non-flat distdir layout
      super ( TemporaryDistroot, self ).__init__ (
         root   = tempfile.mkdtemp ( prefix='tmp_roverlay_distroot_' ),
         flat   = False,
         logger = logger,
      )
   # --- end of __init__ (...) ---

   def _add ( self, src, dest ):
      return self._add_symlink ( src, dest, filter_exceptions=False )
   # --- end of _add (...) ---

   def _cleanup ( self ):
      """Cleans up the temporary distroot by simply wiping it."""
      super ( TemporaryDistroot, self )._cleanup()
      shutil.rmtree ( self._root )
   # --- end of _cleanup (...) ---

   def set_distfile_owner ( self, *args, **kwargs ):
      return True
   # --- end of set_distfile_owner (...) ---

# --- end of TemporaryDistroot ---


class PersistentDistroot ( DistrootBase ):

   USE_SYMLINK    = 1
   USE_HARDLINK   = 2
   USE_COPY       = 4

   USE_EVERYTHING = USE_SYMLINK | USE_HARDLINK | USE_COPY

   def __repr__ ( self ):
      return (
         '{name}<root={root}, strategy={s}, '
         'mode_mask={m_now}/{m_init}>'.format (
            name   = self.__class__.__name__,
            root   = self.get_root(),
            s      = self._strategy,
            m_now  = self._supported_modes,
            m_init = self._supported_modes_initial,
         )
      )
   # --- end of __repr__ (...) ---

   def __init__ ( self,
      root, flat, strategy, distmap, verify=False, logger=None
   ):
      """Initializes a non-temporary distroot.

      arguments:
      * root     -- root directory
      * flat     -- whether to per-package subdirs (False) or not (True)
      * strategy -- the distroot 'strategy' that determines what mode (sym-
                    link, hardlink, copy) will be tried in which order
                    This has to be an iterable with valid items.
      * distmap  --
      * verify   --
      * logger   --
      """
      super ( PersistentDistroot, self ).__init__ (
         root=root, flat=flat, logger=logger, distmap=distmap
      )

      self._strategy = self._get_int_strategy ( strategy )

      # determine supported modes
      self._supported_modes = 0
      for s in self._strategy:
         self._supported_modes |= s
      # finally, restrict supported modes to what is available
      self._supported_modes &= self.USE_EVERYTHING

      self._supported_modes_initial = self._supported_modes

      # dict ( mode => function (arg^2, kwarg^1) )
      self._add_functions = {
         self.USE_SYMLINK  : self._add_symlink,
         self.USE_HARDLINK : self._add_hardlink,
         self.USE_COPY     : self._add_file,
      }

      if self.distmap is not None:
         self.set_distfile_owner = self._set_distfile_owner_distmap
         if verify:
            # expensive task, print a message
            print (
               "Checking distroot file integrity, this may take some time ... "
            )
            self.check_integrity()
      else:
         self.set_distfile_owner = self._set_distfile_owner_nop
   # --- end of __init__ (...) ---

   def _set_distfile_owner_nop ( self, backref, distfile ):
      return True
   # --- end of _set_distfile_owner_nop (...) ---

   def _set_distfile_owner_distmap ( self, backref, distfile ):
      print ( "_set_distfile_owner_distmap(): method stub" )
   # --- end of _set_distfile_owner_distmap (...) ---

   def _add ( self, src, dest ):
      # race condition when accessing self._supported_modes
      #  * this can result in repeated log messages
      for mode in self._strategy:
         if self._supported_modes & mode:
            if self._add_functions [mode] (
               src, dest, filter_exceptions=True
            ):
               return True
            else:
               self.logger.warning (
                  "mode {} is not supported!".format ( mode )
               )
               # the _add function returned False, which means that the
               # operation is not supported
               # => remove mode from self._supported_modes
               self._supported_modes &= ~mode

               # any other exception is unexpected
               #  and will be passed to the caller

      else:
         raise Exception (
            "cannot add {src!r} to {root!r} as {destname!r}".format (
               src      = src,
               root     = self.get_root(),
               destname = os.path.basename ( dest )
            )
         )
   # --- end of _add (...) ---

   def _cleanup ( self ):
      super ( PersistentDistroot, self )._cleanup()
      if hasattr ( self, '_supported_modes_initial' ):
         if self._supported_modes_initial & self.USE_SYMLINK:
            self._remove_broken_symlinks()
   # --- end of _cleanup (...) ---

   def _get_int_strategy ( self, strategy ):
      """Converts the given strategy into its integer tuple representation.

      arguments:
      * strategy --
      """
      def get_int ( item ):
         if hasattr ( item, '__int__' ):
            return int ( item )
         elif item == 'symlink':
            return self.USE_SYMLINK
         elif item == 'hardlink':
            return self.USE_HARDLINK
         elif item == 'copy':
            return  self.USE_COPY
         else:
            raise Exception (
               "unknown mode in strategy {!r}: {!r}".format ( strategy, item )
            )
      # --- end of get_int (...) ---

      #return [ get_int ( s ) for s in strategy ]
      return tuple ( get_int ( s ) for s in strategy )
   # --- end of _get_int_strategy (...) ---

# --- end of PersistentDistroot ---
