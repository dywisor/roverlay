# R overlay -- overlay package, overlay root
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay <-> filesystem interface (root)

This module provides the Overlay class that acts as an interface between
PackageInfo instances (in memory) and the R overlay (directory in filesystem).
Most requests are redirected to its subdirectories (Category), which, in turn,
pass them to their subdirectories (PackageDir).

Caution: Never deep-copy an overlay object. This leads to infinite recursion
due do double-linkage between PackageInfo and PackageDir.
"""

__all__ = [ 'Overlay', ]

import errno
import logging
import os
import shutil
import threading


import roverlay.config
import roverlay.util
import roverlay.overlay.additionsdir
import roverlay.overlay.base
import roverlay.overlay.category
import roverlay.overlay.header
import roverlay.overlay.pkgdir.base
import roverlay.overlay.pkgdir.distroot.static


class Overlay ( roverlay.overlay.base.OverlayObject ):
   DEFAULT_USE_DESC = (
      'byte-compile - enable byte compiling\n'
   )

   @classmethod
   def new_configured ( cls,
      logger, incremental, write_allowed, skip_manifest, rsuggests_flags, **kw
   ):
      """
      Returns a new Overlay instance that uses the roverlay configuration where
      possible.

      arguments:
      * logger              --
      * incremental         --
      * write_allowed       --
      * skip_manifest       --
      * runtime_incremental --
      """
      optional  = roverlay.config.get
      mandatory = roverlay.config.get_or_fail

      return cls (
         name                = mandatory ( 'OVERLAY.name' ),
         logger              = logger,
         directory           = mandatory ( 'OVERLAY.dir' ),
         default_category    = mandatory ( 'OVERLAY.category' ),
         eclass_files        = optional  ( 'OVERLAY.eclass_files' ),
         ebuild_header       = optional  ( 'EBUILD.default_header' ),
         eapi                = mandatory ( 'EBUILD.eapi' ),
         write_allowed       = write_allowed,
         incremental         = incremental,
         skip_manifest       = skip_manifest,
         additions_dir       = optional  ( 'OVERLAY.additions_dir' ),
         use_desc            = optional  ( 'OVERLAY.use_desc' ),
         rsuggests_flags     = rsuggests_flags,
         keep_n_ebuilds      = optional  ( 'OVERLAY.keep_nth_latest' ),
         masters             = mandatory ( 'OVERLAY.masters' ),
         **kw
      )
   # --- end of new_configured (...) ---

   def __init__ (
      self,
      name,
      logger,
      directory,
      default_category,
      eclass_files,
      ebuild_header,
      eapi,
      write_allowed,
      incremental,
      skip_manifest,
      additions_dir,
      rsuggests_flags,
      use_desc=None,
      runtime_incremental=False,
      keep_n_ebuilds=None,
      masters=None,
   ):
      """Initializes an overlay.

      arguments:
      * name                -- name of this overlay
      * logger              -- parent logger to use
      * directory           -- filesystem location of this overlay
      * default_category    -- category of packages being added without a
                                specific category
      * eclass_files        -- eclass files to import and
                                inherit in all ebuilds
      * ebuild_header       -- the header text included in all created ebuilds
      * write_allowed       -- whether writing is allowed
      * incremental         -- enable/disable incremental writing:
                               use already existing ebuilds (don't recreate
                               them)
      * skip_manifest       -- skip Manifest generation to save time
                               !!! The created overlay cannot be used with
                               emerge/portage
      * additions_dir       -- path to a directory that contains additional
                               files, e.g. hand-written ebuilds and ebuild
                               patches. The directory has to exist (it will
                               be checked here).
                               A value of None or "" disables additions.
      * use_desc            -- text for profiles/use.desc
      * runtime_incremental -- see package.py:PackageDir.__init__ (...),
                                Defaults to False (saves memory but costs time)
      * keep_n_ebuilds      -- number of ebuilds to keep (per package),
                               any "false" Value (None, 0, ...) disables this
      """
      super ( Overlay, self ).__init__ ( name, logger, directory, None )

      self.default_category     = default_category

      self._eclass_files        = eclass_files
      self._incremental         = incremental
      # disable runtime_incremental if writing not allowed
      self._runtime_incremental = write_allowed and runtime_incremental
      self._writeable           = write_allowed

      self._catlock             = threading.Lock()
      self._categories          = dict()

      self._masters             = masters
      self._rsuggests_flags     = rsuggests_flags

      self.skip_manifest        = skip_manifest

      self._header   = roverlay.overlay.header.EbuildHeader (
         ebuild_header, eapi
      )
      self._use_desc = (
         use_desc if use_desc is not None else self.DEFAULT_USE_DESC
      ).rstrip()

      if keep_n_ebuilds:
         self.keep_n_ebuilds = keep_n_ebuilds

      if additions_dir:
         if os.path.isdir ( additions_dir ):
            additions_dirpath = os.path.abspath ( additions_dir )
         else:
            raise ValueError (
               "additions dir {} does not exist!".format ( additions_dir )
            )
      else:
         additions_dirpath = None
      # -- end if

      self.additions_dir = (
         roverlay.overlay.additionsdir.AdditionsDir ( additions_dirpath )
      )

      # calculating eclass names twice,
      # once here and another time when calling _init_overlay
      self._header.set_eclasses ( frozenset (
         self._get_eclass_import_info ( only_eclass_names=True )
      ) )

      #if self._incremental:
      if incremental:
         # this is multiple-run incremental writing (in contrast to runtime
         # incremental writing, which writes ebuilds as soon as they're
         # ready)
         self.scan()

      if __debug__:
         # verify that these config keys exist:
         roverlay.config.get_or_fail ( "EBUILD.USE_EXPAND.name" ).rstrip()
         ##roverlay.config.get ( 'OVERLAY.backup_desc', True )
   # --- end of __init__ (...) ---

   def _get_category ( self, category ):
      """Returns a reference to the given category. Creates it if necessary.

      arguments:
      * category -- category identifier as string
      """
      if not category in self._categories:
         self._catlock.acquire()
         try:
            if not category in self._categories:
               newcat = roverlay.overlay.category.Category (
                  category,
                  self.logger,
                  self.physical_location + os.sep + category,
                  get_header=self._header.get,
                  runtime_incremental=self._runtime_incremental,
                  parent=self,
               )
               self._categories [category] = newcat
         finally:
            self._catlock.release()

      return self._categories [category]
   # --- end of _get_category (...) ---

   def _get_eclass_import_info ( self, only_eclass_names=False ):
      """Yields eclass import information (eclass names and files).

      arguments:
      * only_eclass_names -- if True: yield eclass dest names only,
                             else   : yield (eclass name, eclass src file)
                              Defaults to False.

      raises: AssertionError if a file does not end with '.eclass'.
      """
      if self._eclass_files:

         for eclass in self._eclass_files:
            dest = os.path.splitext ( os.path.basename ( eclass ) )

            if dest[1] == '.eclass' or ( not dest[1] and not '.' in dest[0] ):
               if only_eclass_names:
                  yield dest[0]
               else:
                  yield ( dest[0], eclass )
            else:
               raise AssertionError (
                  "{!r} does not end with '.eclass'!".format ( eclass )
               )
   # --- end of _get_eclass_import_info (...) ---

   def _import_eclass ( self, reimport_eclass ):
      """Imports eclass files to the overlay. Also sets ebuild_names.

      arguments:
      * reimport_eclass -- whether to import existing eclass files (again)

      raises:
      * AssertionError, passed from _get_eclass_import_info()
      * Exception if copying fails
      """

      if self._eclass_files:
         # import eclass files
         eclass_dir = self.physical_location + os.sep +  'eclass'
         try:
            eclass_names = list()
            roverlay.util.dodir ( eclass_dir )

            for destname, eclass in self._get_eclass_import_info ( False ):
               dest = eclass_dir + os.sep +  destname + '.eclass'
               if reimport_eclass or not os.path.isfile ( dest ):
                  shutil.copyfile ( eclass, dest )

               eclass_names.append ( destname )

            self._header.set_eclasses ( frozenset ( eclass_names ) )

         except Exception as e:
            self.logger.critical ( "Cannot import eclass files!" )
            raise
   # --- end of _import_eclass (...) ---

   def _generate_layout_conf ( self ):
      # create layout.conf file
      # * create lines

      kv_join    = lambda k, v: "{k} = {v}".format ( k=k, v=v )
      v_join     = lambda v: ' '.join ( v )

      yield kv_join ( "repo_name", self.name )

      if self._masters:
         yield kv_join ( "masters", v_join ( self._masters ) )
      else:
         yield "masters ="


      # strictly speaking,
      #  declaring cache-formats here is not correct since egencache
      #  is run as hook
      yield kv_join ( "cache-formats", "md5-dict" )

      ##yield kv_join ( "sign-commits", "false" )
      ##yield kv_join ( "sign-manifests", "false" )
      ##yield kv_join ( "thin-manifests", "false" )

      hashes = roverlay.overlay.pkgdir.base.get_class().HASH_TYPES
      if hashes:
         yield kv_join ( "manifest-hashes", v_join ( hashes ) )
   # --- end of _generate_layout_conf (...) ---

   def _init_overlay ( self, reimport_eclass, minimal=False ):
      """Initializes the overlay at its physical/filesystem location.

      arguments:
      * reimport_eclass -- whether to copy existing eclass files
                            again (True) or not
      * minimal         -- whether to do full overlay initialization (False)
                           or not (True). Defaults to False.

      raises:
      * IOError, OSError -- passed from file writing / dir creation
      """
      NEWLINE            = '\n'
      CONFIG_GET         = roverlay.config.get
      CONFIG_GET_OR_FAIL = roverlay.config.get_or_fail
      ROOT               = str ( self.physical_location )
      METADATA_DIR       = ROOT + os.sep + 'metadata'
      PROFILES_DIR       = ROOT + os.sep + 'profiles'


      def get_subdir_file_write ( root_dir ):
         """Returns a function for writing files in the given directory.

         arguments:
         * root_dir --
         """
         def write_subdir_file ( relpath, content, append_newline=True ):
            """Writes a file (<root_dir>/<relpath>).

            arguments:
            * relpath        -- file path relative to root_dir
            * content        -- data to write
            * append_newline -- whether to append a newline at EOF
            """
            content_str = str ( content )
            if content_str:
               with open ( root_dir + os.sep + relpath, 'wt' ) as FH:
                  FH.write ( content_str )
                  if append_newline:
                     FH.write ( NEWLINE )
            else:
               # touch file
               with open ( root_dir + os.sep + relpath, 'a' ) as FH:
                  pass
         # --- end of write_subdir_file (...) ---
         return write_subdir_file
      # --- end of get_subdir_file_write (...) ---


      write_profiles_file = get_subdir_file_write ( PROFILES_DIR )
      write_metadata_file = get_subdir_file_write ( METADATA_DIR )

      try:
         layout_conf_str = NEWLINE.join ( self._generate_layout_conf() )

         ## make overlay dirs, root, metadata/, profiles/
         roverlay.util.dodir ( ROOT, mkdir_p=True )
         roverlay.util.dodir ( PROFILES_DIR )
         roverlay.util.dodir ( METADATA_DIR )


         ## import eclass files
         self._import_eclass ( reimport_eclass )


         ## populate profiles/

         # profiles/repo_name
         write_profiles_file ( 'repo_name', self.name )

         # profiles/categories
         cats = NEWLINE.join (
            k for k, v in self._categories.items() if not v.empty()
         )
         if cats:
            write_profiles_file ( 'categories', cats )


         if not minimal:
            # profiles/desc/<r_suggests>.desc
            use_expand_name = (
               CONFIG_GET_OR_FAIL ( "EBUILD.USE_EXPAND.name" ).rstrip ( "_" )
            )

            self._write_rsuggests_use_desc (
               desc_file       = os.sep.join ([
                  PROFILES_DIR, 'desc', use_expand_name.lower(), '.desc'
               ]),
               use_expand_name = use_expand_name.upper(),
               backup_file     = CONFIG_GET ( 'OVERLAY.backup_desc', True ),
               flagdesc_file   = CONFIG_GET (
                  'EBUILD.USE_EXPAND.desc_file', None
               ),
            )


            # profiles/use.desc
            if self._use_desc:
               write_profiles_file ( 'use.desc', self._use_desc )

         # -- end if not minimal ~ profiles/

         ## metadata/

         # metadata/layout.conf
         write_metadata_file ( 'layout.conf', layout_conf_str )

      except ( OSError, IOError ) as e:
         self.logger.exception ( e )
         self.logger.critical ( "failed to init overlay" )
         raise
   # --- end of _init_overlay (...) ---

   def _write_rsuggests_use_desc (
      self, desc_file, use_expand_name, backup_file, flagdesc_file,
      rewrite=False
   ):
      """Creates a USE_EXPAND description file.

      Reads the old file (if it exists) and imports its header / flag desc.

      arguments:
      * desc_file       -- path to the file that should be written/read
      * use_expand_name -- name of the USE_EXPAND variable, e.g. R_SUGGESTS
      * backup_file     -- move desc_file to backup_file before overwriting it
                           This can also be an int i (=> desc_file + '.<i>')
                           or a bool (if True => desc_file + '.bak').
      * flagdesc_file   -- file with flag descriptions (will be read only)
      * rewrite         -- force recreation of the desc file
      """
      FLAG_SEPA  = ' - '
      DESC_UNDEF = 'unknown'

      def do_backup ( dest, makedir=False ):
         self.logger.debug ( "Moving old desc file to {!r}".format ( dest ) )
         if makedir:
            roverlay.util.dodir ( os.path.dirname ( dest ), mkdir_p=True )
         shutil.move ( desc_file, dest )
      # --- end of do_backup (...) ---

      def read_desc_file ( desc_file ):
         """Reads the old desc file (if it exists).
         Returns a 3-tuple ( list header, dict flags, bool file_existed ).

         arguments:
         * desc_file --

         Passes all exceptions (IOError, ...) but "file does not exist".
         """

         FH     = None
         header = list()
         # flags := dict { <flag name> => <desc>|None }
         flags  = dict()
         fexist = False
         try:
            FH = open ( desc_file, 'rt' )

            addto_header = True

            for line in FH.readlines():
               rsline = line.rstrip()
               if rsline and rsline [0] != '#':
                  flag, sepa, desc = rsline.partition ( FLAG_SEPA )
                  # <desc> == DESC_UNDEF -- ignore
                  flags [flag]     = desc if sepa else None
                  addto_header     = False
               elif addto_header is True:
                  header.append ( rsline )
               elif rsline:
                  self.logger.warning (
                     "dropping line from {f!r}: {l}".format (
                        f=desc_file, l=rsline
                     )
                  )
            # -- end for

            FH.close()
            fexist = True
         except IOError as ioerr:
            if ioerr.errno == errno.ENOENT:
               pass
            else:
               raise
         finally:
            if FH: FH.close()

         return ( header, flags, fexist )
      # --- end of read_desc_file ---

      def gen_desc ( header, flags ):
         """Creates new text lines for the desc file.

         arguments:
         * @implicit use_expand_name --
         * header -- header line(s) to use (a default header will be created
                     if this is empty)
         * flags  -- flag=>desc dict
         """
         NEWLINE = '\n'

         if header:
            for line in header:
               yield line
               yield NEWLINE
            #yield NEWLINE
         else:
            defheader = self._header.get_use_expand_header ( use_expand_name )
            if defheader:
               yield defheader
               yield NEWLINE

         for flag, desc in sorted ( flags.items(), key=lambda e: e[0] ):
            if desc:
               yield flag + FLAG_SEPA + desc
            else:
               yield flag + FLAG_SEPA + DESC_UNDEF
            yield NEWLINE
      # --- end of gen_desc (...) ---

      header, old_flags, can_backup = read_desc_file ( desc_file )

      if flagdesc_file:
         flagdesc_header, flagdesc, flagdesc_cb = read_desc_file (
            str ( flagdesc_file )
         )
         del flagdesc_header, flagdesc_cb
      else:
         flagdesc = dict()

      if self._incremental:
         # incremental: add new flags
         #  Create dict flag=>None that contains all new flags
         #  and copy old_flags "over" it.
         #
         flags = {
            flag: flagdesc.get ( flag, None )
            for flag in self._rsuggests_flags
         }
         flags.update ( old_flags )
      else:
         # not incremental: discard old flags
         #  Create a dict that contains the new flags only and use desc
         #  from old_flags if available.
         #
         flags = {
            flag: old_flags.get ( flag, None ) or flagdesc.get ( flag, None )
            for flag in self._rsuggests_flags
         }
      # -- end if

      # don't rewrite the desc file if nothing has changed
      if rewrite or (
         frozenset ( flags.keys() ) != frozenset ( old_flags.keys() )
      ):
         if can_backup:
            if backup_file is True:
               do_backup ( desc_file + '.bak' )
            elif isinstance ( backup_file, int ):
               do_backup ( desc_file + '.' + str ( backup_file ) )
            elif backup_file:
               do_backup ( str ( backup_file ), makedir=True )
         # -- end if

         self.logger.debug ( "writing desc file {!r}".format ( desc_file ) )

         roverlay.util.dodir ( os.path.dirname ( desc_file ) )
         with open ( desc_file, 'wt' ) as FH:
            for line in gen_desc ( header, flags ):
               FH.write ( line )
      else:
         self.logger.debug (
            "not writing desc file {!r} (nothing changed)".format ( desc_file )
         )
   # --- end of _write_rsuggests_use_desc (...) ---

   def access_distroot ( self ):
      return roverlay.overlay.pkgdir.distroot.static.access()
   # --- end of access_distroot (...) ---

   def add ( self, package_info, allow_postpone=False ):
      """Adds a package to this overlay (into its default category).

      arguments:
      * package_info   -- PackageInfo of the package to add
      * allow_postpone -- do not add the package if it already exists and
                          return None

      returns:
      * True if successfully added
      * a weak reference to the package dir object if postponed
      * else False
      """
      # NOTE:
      # * "category" keyword arg has been removed, use add_to(^2) instead
      # * self.default_category must not be None (else KeyError is raised)
      return self._get_category (
         package_info.get ( "category", self.default_category )
      ).add ( package_info, allow_postpone=allow_postpone )
   # --- end of add (...) ---

   def add_to ( self, package_info, category, allow_postpone=False ):
      """Adds a package to this overlay.

      arguments:
      * package_info   -- PackageInfo of the package to add
      * category       -- category where the pkg should be put in
      * allow_postpone -- do not add the package if it already exists and
                          return None

      returns:
      * True if successfully added
      * a weak reference to the package dir object if postponed
      * else False
      """
      return self._get_category ( category ).add (
         package_info, allow_postpone=allow_postpone
      )
   # --- end of add_to (...) ---

   def has_dir ( self, _dir ):
      return os.path.isdir ( self.physical_location + os.sep + _dir )
   # --- end of has_category (...) ---

   def find_duplicate_packages ( self, _default_category=None ):
      """Searches for packages that exist in the default category and
      another one and returns a set of package names.

      arguments:
      * _default_category -- category object
      """
      default_category = (
         _default_category if _default_category is None
         else self._categories.get ( self.default_category, None )
      )

      if default_category:
         duplicate_pkg = set()

         for category in self._categories.values():
            if category is not default_category:
               for name in category.list_package_names():
                  if default_category.get_nonempty ( name ):
                     duplicate_pkg.add ( name )
         # -- end for;

         return frozenset ( duplicate_pkg )
      else:
         return None
   # --- end of find_duplicate_packages (...) ---

   def remove_duplicate_ebuilds ( self, reverse ):
      """Searcges for packages that exist in the default category and
      another one and removes them from either one, depending on whether
      reverse if True (other will be removed) or False (default category).

      arguments:
      * reverse
      """
      default_category = self._categories.get ( self.default_category, None )
      if default_category:
         if reverse:
            d_pkg = self.find_duplicate_packages (
               _default_category=default_category
            )
            for pkg_name in d_pkg:
               default_category.drop_package ( pkg_name )

         else:
            d_pkg = set()
            for category in self._categories.values():
               if category is not default_category:
                  for name in category.list_package_names():
                     if default_category.get_nonempty ( name ):
                        d_pkg.add ( name )
                        category.drop_package ( pkg_name )
            # -- end for category;

         # -- end if;

         if d_pkg:
            self.remove_empty_categories()

            self.logger.info (
               '{} ebuilds have been removed from the default category, '
               'the overlay might be broken now!'.format ( len ( d_pkg ) )
            )
            return True
         else:
            return False
      else:
         return False

   # --- end of remove_duplicate_ebuilds (...) ---

   def remove_empty_categories ( self ):
      """Removes empty categories."""
      catlist = list ( self._categories.items() )
      for cat in catlist:
         cat[1].remove_empty()
         if cat[1].empty():
            del self._categories [cat[0]]

            try:
               os.rmdir ( cat [1].physical_location )
            except OSError as ose:
               self.logger.exception ( ose )

   # --- end of remove_empty_categories (...) ---

   def list_packages ( self, for_deprules=True ):
      for cat in self._categories.values():
         for package in cat.list_packages ( for_deprules=for_deprules ):
            yield package
   # --- end of list_packages (...) ---

   def readonly ( self ):
      return not self._writeable
   # --- end of readonly (...) ---

   def import_ebuilds ( self, overwrite, nosync=False, init_overlay=True ):
      """Imports ebuilds from the additions dir.

      arguments:
      * overwrite    -- whether to overwrite existing ebuilds
      * nosync       -- if True: don't fetch src files (defaults to False)
      * init_overlay -- if True: do minimal overlay initialization before
                                 importing ebuilds. This is recommended
                                 because portage expects metadata/layout.conf
                                 to exist, for example.
                                 Defaults to True.
      """
      if init_overlay:
         self._init_overlay ( False, minimal=True )

      for catview in (
         roverlay.overlay.additionsdir.CategoryRootView ( self.additions_dir )
      ):
         self._get_category ( catview.name ).import_ebuilds (
            catview, overwrite=overwrite, nosync=nosync
         )

      # assumption: distroot exists
      self.access_distroot().sync_distmap_if_required()
   # --- end of import_ebuilds (...) ---

   def iter_package_info ( self ):
      for cat in self._categories.values():
         for p_info in cat.iter_package_info():
            yield p_info
   # --- end of iter_package_info (...) ---

   def link_selfdeps ( self, selfdeps ):
      ##
      ## link:
      ## foreach selfdep in S loop
      ##    find <PackageInfo> candidates in overlay and link them to selfdep
      ## end loop
      ##
      for selfdep in selfdeps:
         cat = self._categories.get ( selfdep.category, None )
         if cat:
            pkgdir = cat.get_nonempty ( selfdep.package )
            if pkgdir:
               selfdep.linkall_if_version_matches (
                  pkgdir.iter_package_info()
               )
      # -- end for selfdep;
   # --- end of link_selfdeps (...) ---

   def remove_broken_packages ( self ):
      #
      # "balance"
      #
      ## find all <PackageInfo> p with p.is_valid() == False
      ##     drop p
      ##


      #PKG_REMOVED     = list()
      #PKG_REMOVED_ADD = PKG_REMOVED.append


      num_pkg_removed = 0
      for cat in self._categories.values():
         for pkgdir in cat._subdirs.values():
            for pvr, p_info in pkgdir._packages.items():
               if not p_info.is_valid():
                  #PKG_REMOVED_ADD ( "{}-{}".format ( pkgdir.name, pvr ) )
                  pkgdir.purge_package ( pvr )
                  num_pkg_removed += 1
      # -- end for cat;


#      if PKG_REMOVED:
#         with open ( "/tmp/roverlay_selfdep_redux.dbg", 'wt' ) as DEBUG_FH:
#            for line in PKG_REMOVED:
#               DEBUG_FH.write ( line )
#               DEBUG_FH.write ( '\n' )

      # FIXME: debug prints (use logging, ...)

      if num_pkg_removed > 0:
         # remove_empty_categories() could be done in the loop above
         self.remove_empty_categories()

         self.logger.info (
            'remove_broken_packages: {:d} ebuilds have been dropped.'.format (
               num_pkg_removed
            )
         )
      else:
         self.logger.info ( 'remove_broken_packages: no ebuilds removed.' )

      return num_pkg_removed
   # --- end of remove_broken_packages (...) ---

   def scan ( self, **kw ):
      def scan_categories():
         for x in os.listdir ( self.physical_location ):
            if '-' in x and self.has_dir ( x ):
               yield self._get_category ( x )
      # --- end of scan_categories (...) ---

      self.logger.info ( "Scanning the overlay for existing packages" )

      if os.path.isdir ( self.physical_location ):
         for cat in scan_categories():
            try:
               cat.scan ( **kw )
            except ( RuntimeError, SystemError, KeyboardInterrupt, ):
               raise
            except Exception as e:
               self.logger.exception ( e )
   # --- end of scan (...) ---

   def show ( self, **show_kw ):
      """Presents the ebuilds/metadata stored in this overlay.

      arguments:
      * **show_kw -- keywords for package.PackageDir.show(...)

      returns: None (implicit)
      """
      if not self._header.eclasses: self._header.set_eclasses (
         tuple ( self._get_eclass_import_info ( only_eclass_names=True ) )
      )
      for cat in self._categories.values():
         cat.show ( **show_kw )
   # --- end of show (...) ---

   def writeable ( self ):
      return self._writeable
   # --- end of writeable (...) ---

   def write ( self ):
      """Writes the overlay to its physical location (filesystem), including
      metadata and Manifest files as well as cleanup actions.

      arguments:
      * **write_kw -- keywords for package.PackageDir.write(...)

      returns: None (implicit)

      raises: IOError

      Note: This is not thread-safe, it's expected to be called when
      ebuild creation is done.
      """

      if self._writeable:
         self._init_overlay ( reimport_eclass=True )

         for cat in self._categories.values():
            cat.write (
               overwrite_ebuilds = False,
               keep_n_ebuilds    = getattr ( self, 'keep_n_ebuilds', None ),
               cautious          = True,
               write_manifest    = not self.skip_manifest,
               additions_dir     = self.additions_dir.get_obj_subdir ( cat ),
            )

         # assumption: distroot exists
         self.access_distroot().finalize()
      else:
         # FIXME debug print
         print (
            "Dropped write request for readonly overlay {}!".format (
               self.name
         ) )
   # --- end of write (...) ---

   def write_manifest ( self, **manifest_kw ):
      """Generates Manifest files for all ebuilds in this overlay that exist
      physically/in filesystem.
      Manifest files are automatically created when calling write().

      arguments:
      * **manifest_kw -- see PackageDir.generate_manifest(...)

      returns: None (implicit)
      """
      if self._writeable and not self.skip_manifest:
         # profiles/categories is required for successful Manifest
         # creation
         if os.path.isfile ( os.path.join (
            str ( self.physical_location ), 'profiles', 'categories'
         ) ):
            for cat in self._categories.values():
               cat.write_manifest ( **manifest_kw )
         else:
            raise Exception (
               'profiles/categories is missing - cannot write Manifest files!'
            )
      elif not self.skip_manifest:
         # FIXME debug print
         print (
            "Dropped write_manifest request for readonly overlay {}!".format (
               self.name
         ) )
   # --- end of write_manifest (...) ---
