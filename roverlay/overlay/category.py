# R overlay -- overlay package, category
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay <-> filesystem interface (category)

This module provides the Category class that represents a portage category
and is part of the overlay <-> filesystem interface.
It offers access to its package directories (e.g. show()) and offers useful
abstractions (e.g. threaded writing using write()).
"""

__all__ = [ 'Category', ]

import threading
import os
import sys

try:
   import queue
except ImportError:
   import Queue as queue

from roverlay.overlay import pkgdir

class Category ( object ):

   WRITE_JOBCOUNT = 3

   def __init__ ( self,
      name, logger, directory, get_header, runtime_incremental
   ):
      """Initializes a overlay/portage category (such as 'app-text', 'sci-R').

      arguments:
      * name                -- name of the category
      * logger              -- parent logger
      * directory           -- filesystem location
      * get_header          -- function that returns an ebuild header
      * runtime_incremental -- enable/disable runtime incremental writing
                               for this category (and all created PackageDirs)
      """
      self.logger              = logger.getChild ( name )
      self.name                = name
      self._lock               = threading.RLock()
      self._subdirs            = dict()
      self.physical_location   = directory
      self.get_header          = get_header
      self.runtime_incremental = runtime_incremental
   # --- end of __init__ (...) ---

   def _get_package_dir ( self, pkg_name ):
      """Returns a PackageDir object for pkg_name.
      (so that <new object>.name == pkg_name and pkg_name in self._subdirs)

      arguments:
      * pkg_name --
      """
      if not pkg_name in self._subdirs:
         self._lock.acquire()
         try:
            if not pkg_name in self._subdirs:
               newpkg = pkgdir.get_class() (
                  name        = pkg_name,
                  logger      = self.logger,
                  directory   = self.physical_location + os.sep + pkg_name,
                  get_header  = self.get_header,
                  runtime_incremental = self.runtime_incremental,
                  parent      = self
               )
               self._subdirs [pkg_name] = newpkg
         finally:
            self._lock.release()

      return self._subdirs [pkg_name]
   # --- end of _get_package_dir (...) ---

   def add ( self, package_info, **pkg_add_kw ):
      """Adds a package to this category.

      arguments:
      * package_info --

      returns: success
      """
      return self._get_package_dir ( package_info ['name'] ).add (
         package_info, **pkg_add_kw
      )
   # --- end of add (...) ---

   def drop_package ( self, name ):
      p = self._subdirs [name]
      del self._subdirs [name]
      p.fs_destroy()
   # --- end of drop_package (...) ---

   def empty ( self ):
      """Returns True if this category contains 0 ebuilds."""
      return (
         len ( self._subdirs ) == 0 or
         all ( d.empty() for d in self._subdirs.values() )
      )
   # --- end of empty (...) ---

   def get_nonempty ( self, name ):
      subdir = self._subdirs.get ( name, None )
      return subdir if ( subdir and not subdir.empty() ) else None
   # --- end of has_nonempty (...) ---

   def has ( self, subdir ):
      return subdir in self._subdirs
   # --- end of has (...) ---

   def has_dir ( self, _dir ):
      return os.path.isdir ( self.physical_location + os.sep + _dir )
   # --- end of has_category (...) ---

   def list_package_names ( self ):
      for name, subdir in self._subdirs.items():
         if not subdir.empty():
            yield name
   # --- end of list_package_names (...) ---

   def list_packages ( self,
      for_deprules=False, is_default_category=False
   ):
      """Lists all packages in this category.
      Yields <category>/<package name> or a dict (see for_deprules below).

      arguments:
      * for_deprules        -- if set and True:
                                yield keyword args for dependency rules
      * is_default_category -- bool indicating whether this category is the
                               default one or not
      """
      if for_deprules:
         for name, subdir in self._subdirs.items():
            if not subdir.empty():
               yield dict (
                  dep_str           = name,
                  resolving_package = ( self.name + "/" + name ),
                  is_selfdep        = is_default_category,
                  # prefer packages from the default category (really?)
                  priority          = 80 if is_default_category else 90,
               )
      else:
         for name, subdir in self._subdirs.items():
            if not subdir.empty():
               yield self.name + os.sep + name
   # --- end of list_packages (...) ---

   def supports_threadsafe_manifest_writing ( self, unsafe=True ):
      """Returns True if manifest writing is thread safe for this
      category, else False. Also returns True for empty categories.

      arguments:
      * unsafe -- if False : verify that all packages of this category support
                             thread safe writing
                  else     : assume that all packages of this category are
                             instances of the same class and check only the
                             first one (=> faster).
                  Defaults to True.

      """
      if unsafe:
         try:
            return bool (
               next ( iter ( self._subdirs.values() ) ).MANIFEST_THREADSAFE
            )
         except StopIteration:
            return True
      else:
         for pkgdir in self._subdirs.values():
            #if not pkgdir.__class__.MANIFEST_THREADSAFE:
            if not pkgdir.MANIFEST_THREADSAFE:
               return False
         return True
   # --- end of supports_threadsafe_manifest_writing (...) ---

   def remove_empty ( self ):
      """This removes all empty PackageDirs."""
      with self._lock:
         for key in tuple ( self._subdirs.keys() ):
            if self._subdirs [key].check_empty():
               del self._subdirs [key]
   # --- end of remove_empty (...) ---

   def scan ( self, **kw ):
      """Scans this category for existing ebuilds."""
      for subdir in os.listdir ( self.physical_location ):
         if self.has_dir ( subdir ):
            pkgdir = self._get_package_dir ( subdir )
            try:
               pkgdir.scan ( **kw )
            finally:
               if pkgdir.empty():
                  del self._subdirs [subdir]
   # --- end of scan (...) ---

   def show ( self, **show_kw ):
      """Prints this category (its ebuild and metadata files).

      returns: None (implicit)
      """
      for package in self._subdirs.values():
         package.show ( **show_kw )
   # --- end of show (...) ---

   def write ( self,
      overwrite_ebuilds,
      keep_n_ebuilds,
      cautious,
      write_manifest,
      additions_dir
   ):
      """Writes this category to its filesystem location.

      returns: None (implicit)
      """
      def run_write_queue ( q, write_kw ):
         """Calls <package>.write for every <package> received from the queue.

         arguments:
         * q        -- queue
         * write_kw -- keywords for write(...)
         """
         while not q.empty() and not hasattr ( self, 'RERAISE' ):
            try:
               pkg = q.get_nowait()
               # remove manifest writing from threaded writing since it's
               # single-threaded
               pkg.write (
                  additions_dir = additions_dir.get_obj_subdir ( pkg ),
                  **write_kw
               )
            except queue.Empty:
               break
            except ( Exception, KeyboardInterrupt ) as err:
               self.logger.exception ( err )
               self.RERAISE = sys.exc_info()
      # --- end of run_write_queue (...) ---

      if len ( self._subdirs ) == 0: return

      # determine write keyword args
      write_kwargs = dict (
         overwrite_ebuilds = overwrite_ebuilds,
         keep_n_ebuilds    = keep_n_ebuilds,
         cautious          = cautious,
         write_manifest    = write_manifest,
      )

      # start writing:

      max_jobs = self.__class__.WRITE_JOBCOUNT

      # What's an reasonable number of min package dirs to
      # start threaded writing?
      # Ignoring it for now (and expecting enough pkg dirs)
      if max_jobs > 1:

         # writing <=max_jobs package dirs at once

         # don't create more workers than write jobs available
         max_jobs = min ( max_jobs, len ( self._subdirs ) )

         manifest_threadsafe = self.supports_threadsafe_manifest_writing (
            unsafe=True
         )

         write_queue = queue.Queue()
         for package in self._subdirs.values():
            write_queue.put_nowait ( package )

         write_kwargs ['write_manifest'] = (
            write_manifest and manifest_threadsafe
         )

         workers = frozenset (
            threading.Thread (
               target=run_write_queue,
               args=( write_queue, write_kwargs )
            ) for n in range ( max_jobs )
         )

         for w in workers: w.start()
         for w in workers: w.join()

         if hasattr ( self, 'RERAISE' ) and self.RERAISE:
            # ref: PEP 3109
            #  results in correct traceback when running python 3.x
            #  and inaccurate traceback with python 2.x,
            #  which can be tolerated since the exception has been logged
            try:
               reraise = self.RERAISE[0] ( self.RERAISE[1] )
            except TypeError:
               # "portage.exception.FileNotFound is not subscriptable"
               reraise = self.RERAISE[1]

            reraise.__traceback__ = self.RERAISE [2]
            raise reraise
         # --- end RERAISE;

         self.remove_empty()

         # write manifest files
         # fixme: debug print
         if write_manifest and ( not manifest_threadsafe ):
            print ( "Writing Manifest files ..." )
            for package in self._subdirs.values():
               package.write_manifest ( ignore_empty=True )

      else:
         for package in self._subdirs.values():
            package.write (
               additions_dir = additions_dir.get_obj_subdir ( package ),
               **write_kwargs
            )

         self.remove_empty()
   # --- end of write (...) ---

   def write_manifest ( self, **manifest_kw ):
      """Generates Manifest files for all packages in this category.
      Manifest files are automatically created when calling write().

      arguments:
      * **manifest_kw -- see PackageDir.write_manifest(...)

      returns: None (implicit)
      """
      for package in self._subdirs.values():
         package.write_manifest ( **manifest_kw )
   # --- end of write_manifest (...) ---
