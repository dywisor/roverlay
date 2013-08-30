# R overlay -- roverlay package, packageinfo
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""package info data structure

This module provides one class, PackageInfo, which is a data structure that
offers access to package and ebuild related data. It's also able to calculate
some data if required, like getting description data from an R package.
"""

__all__ = [ 'PackageInfo', ]

import re
import os.path
import logging


import roverlay.digest
import roverlay.versiontuple
import roverlay.db.distmap
import roverlay.util.objects
import roverlay.util.ebuildparser

from roverlay          import config, strutil
from roverlay.rpackage import descriptionreader

# PackageInfo info keys know to be used in roverlay's modules:
# *** some keys are not listed here (FIXME) ***
#
# * desc_data          -- dict containing DESCRIPTION data (created by
#                          rpackage.descriptionreader.DescriptionReader)
# * distdir            -- fs path to the directory containing the pkg (file)
# * ebuild             -- object representing the ebuild (printable via str())
# * ebuild_file        -- fs path to the ebuild file (str)
# * ebuild_verstr      -- version string as it's used in the ebuild
# * has_suggests       -- bool that indicates whether a package has optional
#                          dependencies
# * name               -- (ebuild) name of a package (no "special" chars etc.)
# * orig_name          -- original (ebuild) name (before "name" has been
#                          modified by package rules)
# * origin             -- a package's origin (repository object)
# * package_file       -- full fs path to the package file
# * package_filename   -- file name (including file extension)
# * package_filename_x -- file name without file extension
# * package_name       -- package name (file name without version, f-ext)
# * physical_only      -- bool that indicates whether a package exists as
#                          ebuild file only (True) or has additional
#                          runtime data (False)
# * src_uri            -- SRC_URI for a package
# * version            -- tuple containing a package's version
#
#
# Info (keys) that are created before applying package rules:
#
# * distdir
# * origin
# * package_{file{,name},name}
# * name (package_name)
# * src_uri (src_uri_base)
#
# "Foreign" info keys (never set or modified here):
#
# * category
# * src_uri_dest
#

LOGGER = logging.getLogger ( 'PackageInfo' )


class PackageInfoStatus ( roverlay.util.objects.ObjectView ):

   def __init__ ( self, package_info ):
      super ( PackageInfoStatus, self ).__init__ ( package_info )
      self.has_ebuild_file = False
   # --- end of __init__ (...) ---

   def get_name ( self ):
      return self.deref_safe().get ( 'name' )
   # --- end of get_name (...) ---

   def update ( self ):
      self.has_ebuild_file = bool (
         self.deref_safe().get ( 'ebuild_file', do_fallback=True )
      )
   # --- end of update (...) ---

# --- end of PackageInfoStatus ---


class PackageInfo ( roverlay.util.objects.Referenceable ):
   """PackageInfo offers easy, subscriptable access to package
   information, whether stored or calculated.

   class-wide variables:
   * EBUILDVER_REGEX -- a regex containing chars that will be replaced by
                        a dot '.'. (e.g. 2-3 becomes 2.3)
   * PKGSUFFIX_REGEX -- a regex that matches the suffix of an R package file
                        name. The regex str is retrieved from the config
                        module (which also means that the config has to be
                        loaded before import this module)
   * ALWAYS_FALLBACK -- a set of keys for which get() always returns a
                        fallback value (None)

   * _UPDATE_KEYS_SIMPLE         -- a set of keys that can be added
                                    without further checks
   * _UPDATE_KEYS_SIMPLE_INITIAL -- like _UPDATE_KEYS_SIMPLE, but only used
                                    on the first update() call (as long as
                                    no keys have been stored)
   * _UPDATE_KEYS_FILTER_NONE    -- like _UPDATE_KEYS_SIMPLE, but stores
                                    key's value only if it is not None
   * _REMOVE_KEYS_EBUILD         -- a set of keys that will be removed when
                                    _remove_auto ( 'ebuild_written' ) is
                                    called.
   """

   CACHE_REF = True

   EBUILDVER_REGEX = re.compile ( '[-]{1,}' )
   PKGSUFFIX_REGEX = re.compile (
      config.get_or_fail ( 'R_PACKAGE.suffix_regex' ) + '$'
   )
   EBUILDREV_REGEX = re.compile ( '[-]r[0-9]+$' )
   ALWAYS_FALLBACK = frozenset ( ( 'ebuild', 'ebuild_file' ) )

   _UPDATE_KEYS_SIMPLE         = frozenset ((
      'ebuild',
      'ebuild_file',
      'imported',
      'physical_only',
      'src_uri',
      'has_suggests',
   ))
   _UPDATE_KEYS_SIMPLE_INITIAL = frozenset ((
      'package_filename', 'name',
   ))
   _UPDATE_KEYS_FILTER_NONE    = frozenset ((
      'src_uri_base',
      'distdir',
   ))

   _REMOVE_KEYS_EBUILD         = frozenset ((
      'ebuild'
   ))

   # bind DIGEST_TYPE to this class
   DISTMAP_DIGEST_TYPE = roverlay.db.distmap.DistMapInfo.DIGEST_TYPE

   def __init__ ( self, **initial_info ):
      """Initializes a PackageInfo.

      arguments:
      * **initial_info -- passed to update ( **kw )
      """
      super ( PackageInfo, self ).__init__()

      self._info    = dict()
      self.readonly = False
      self.logger   = LOGGER
      # self.selfdeps is a list of _mandatory_ selfdeps
      self.selfdeps = None

      self.hashdict = dict()
      self.depconf  = None

      #self.selfdeps_valid      = UNDEF
      #self.overlay_package_ref = None
      #self._evars              = dict()
      #self._lazy_actions       = list()
      #(or set(), but list preserves order for actions with the same condition)

      self.update ( **initial_info )
   # --- end of __init__ (...) ---

   def init_selfdep_validate ( self, selfdeps ):
      """Tells this packageinfo to initialize selfdep validation.
      Returns True on success (=has selfdeps), else False.
      """
      if selfdeps:
         self.selfdeps_valid = True
         self.selfdeps = selfdeps
         return True
      else:
         self.selfdeps = None
         return False
   # --- end of init_selfdep_validate (...) ---

   def is_valid ( self ):
      return bool ( getattr ( self, 'selfdeps_valid', True ) )
   # --- end of is_valid (...) ---

   def end_selfdep_validate ( self ):
      v = self.has_valid_selfdeps()
      self.selfdeps = None
      return v
   # --- end of end_selfdep_validate (...) ---

   def has_selfdeps ( self ):
      return bool ( self.selfdeps )
   # --- end of has_selfdeps (...) ---

   def has_valid_selfdeps ( self ):
      """Returns True if all selfdeps of this package are valid."""
      if self.selfdeps is None:
         return True
      else:
         v = self.selfdeps_valid
         if v is True and not all (
            d.deps_satisfiable() for d in self.selfdeps
         ):
            self.selfdeps_valid = False
            return False

         return v
   # --- end of has_valid_selfdeps (...) ---

   def get_status_view ( self ):
      obj = PackageInfoStatus ( self )
      obj.update()
      return obj
   # --- end of get_status_view (...) ---

   def attach_lazy_action ( self, lazy_action ):
      """Attaches a lazy action.
      Unsafe operation (no locks will be acquired etc.).

      arguments:
      * lazy_action --
      """
      raise NotImplementedError ( "lazy actions are disabled." )
      if hasattr ( self, '_lazy_actions' ):
         self._lazy_actions.append ( lazy_action )
      else:
         self._lazy_actions = [ lazy_action ]
   # --- end of attach_lazy_action (...) ---

   def apply_lazy_actions ( self ):
      """Tries to apply all attached (lazy) actions.
      Removes actions that have been applied."""
      raise NotImplementedError ( "lazy actions are disabled." )
      if hasattr ( self, '_lazy_actions' ):
         retry_later = list()
         for action in self._lazy_actions:
            if not action.try_apply_action ( self ):
               retry_later.append ( action )

         if retry_later:
            self._lazy_actions = retry_later
         else:
            del self._lazy_actions
      # -- end if;
   # --- end of apply_lazy_actions (...) ---

   def set_readonly ( self, immediate=False, final=False ):
      """Makes the package info readonly.

      arguments:
      * immediate -- do not acquire lock, set readonly directly,
                      defaults to False
      * final     -- if set and True: make this decision final
     """
      self._set_mode ( True, immediate, final )
   # --- end of set_readonly (...) ---

   def set_writeable ( self, immediate=False ):
      """Makes the package info writeable.

      arguments:
      * immediate -- do not acquire lock, set writeable directly,
                      defaults to False
      """
      self._set_mode ( False, immediate )
   # --- end of set_writeable (...) ---

   def _set_mode ( self, readonly_val, immediate=False, final=False ):
      """Sets readonly to True/False.

      arguments:
      * readonly_val -- new value for readonly
      * immediate    -- do not acquire lock
      * final        -- only if readonly_val is True: make this decision final

      raises: Exception if self.readonly is a constant (_readonly_final is set)
      """
      if hasattr ( self, '_readonly_final' ):
         raise Exception ( "cannot modify readonly - it's a constant." )
      else:
         self.readonly = readonly_val
         if final and readonly_val:
            self._readonly_final = True
   # --- end of _set_mode (...) ---

   def _check_readonly ( self ):
      """Checks whether this object is writable.
      Returns True on success, else raises an exception.
      """
      if self.readonly or hasattr ( self, '_readonly_final' ):
         raise Exception ( "package info is readonly!" )
      else:
         return True
   # --- end of _check_readonly (...) ---

   def _has_log_keyerror_unexpected ( self, key, error ):
      self.logger.error (
         'FIXME: PackageInfo.get( {!r}, do_fallback=True ) '
         'raised KeyError'.format ( key )
      )
      self.logger.exception ( error )
   # --- end of _has_log_keyerror_unexpected (...) ---

   def has_key ( self, *keys ):
      """Returns False if at least one key out of keys is not accessible,
      i.e. its data cannot be retrieved using get()/__getitem__().

      arguments:
      * *keys -- keys to check
      """
      for k in keys:
         if k not in self._info:
            # try harder - use get() with fallback value to see if value
            # can be calculated
            try:
               if self.get ( k, do_fallback=True ) is None:
                  return False
            except KeyError as kerr:
               self._has_log_keyerror_unexpected ( k, kerr )
               return False
      return True
   # --- end of has_key (...) ---

   has = has_key

   def has_key_or ( self, *keys ):
      """Returns True if at least one key out of keys is accessible.

      arguments:
      * *keys -- keys to check
      """
      for k in keys:
         try:
            if k in self._info:
               return True
            elif self.get ( k, do_fallback=True ) is not None:
               return True
         except KeyError as kerr:
            self._has_log_keyerror_unexpected ( k, kerr )
      return False
   # --- end of has_key_or (...) ---

   has_or = has_key_or

   def compare_version ( self, other_package ):
      """Compares the version of two PackageInfo objects.
      Returns 1 if self's version is higher, -1 if lower and 0 if equal.

      arguments:
      * other_package --
      """
      if other_package is None: return 1

      my_ver    = self.get ( 'version', fallback_value=0 )
      other_ver = other_package.get ( 'version', fallback_value=0 )

      if my_ver > other_ver:
         return 1
      elif my_ver == other_ver:
         return 0
      else:
         return -1
   # --- end of compare_version (...) ---

   def get ( self, key, fallback_value=None, do_fallback=False ):
      """Returns the value specified by key.
      The value is either calculated or taken from dict self._info.

      arguments:
      * key --
      * fallback_value -- fallback value if key not found / unknown
      * do_fallback    -- if True: return fallback_value, else raise KeyError

      raises: KeyError
      """
      # normal dict access shouldn't be slowed down here
      if key in self._info:
         return self._info [key]

      key_low = key.lower()

      if key_low in self._info:
         return self._info [key_low]

      try:
         val = self._get_virtual ( key_low )
      except KeyError:
         self.logger.critical (
            "FIXME: _get_virtual({!r}) raised KeyError".format ( key_low )
         )
         raise

      if val is not None:
         return val
      elif fallback_value is not None or do_fallback:
         return fallback_value
      elif key_low in self.__class__.ALWAYS_FALLBACK:
         #return fallback_value
         return None
      else:
         raise KeyError ( key )
   # --- end of get (...) ---

   def _get_virtual ( self, key ):
      # 'virtual' keys - calculate result
      if key == 'package_file':
         distdir = self.get ( 'distdir', do_fallback=True )
         if distdir:
            fname = self._info.get ( 'package_filename', None )
            if fname:
               return distdir + os.path.sep + fname

      elif key == 'distdir':
         if 'origin' in self._info:
            # this doesn't work if the package is in a sub directory
            # of the repo's distdir
            return self._info ['origin'].distdir
         elif 'package_file' in self._info:
            return os.path.dirname ( self._info ['package_file'] )
         # else fallback/KeyError

      elif key == 'has_suggests':
         # 'has_suggests' not in self._info -> assume False
         return False

      elif key == 'physical_only':
         # 'physical_only' not in self._info -> assume False
         return False

      elif key == 'imported':
         # 'imported' not in self._info -> assume False
         return False

      elif key == 'src_uri':
         if 'src_uri_base' in self._info:
            return \
               self._info ['src_uri_base'] + '/' + \
               self._info ['package_filename']

         elif 'origin' in self._info:
            return self._info ['origin'].get_src_uri (
               self._info ['package_filename']
            )
         else:
            return "http://localhost/R-packages/" + \
               self._info ['package_filename']

      elif key == 'ebuild_dir':
         ebuild_file = self._info ['ebuild_file']
         if ebuild_file is not None:
            return os.path.dirname ( ebuild_file )

      elif key == 'ebuild_filename':
         ebuild_file = self._info ['ebuild_file']
         if ebuild_file is not None:
            return os.path.basename ( ebuild_file )

      elif key == 'package_src_destpath':
         # src file path relative to distroot (mirror root dir)
         destpath = self._info.get ('src_uri_dest', None )
         return ( destpath or self._info ['package_filename'] )

      # end if <key matches ...>

      # explicit return
      return None
   # --- end of _get_virtual (...) ---

   def get_create (
      self, key, newtype, convert=False, check_type=True, create_kw=None
   ):
      """Tries to get a value from the info dict. Creates it as newtype if
      necessary.

      Note: This operation is "unsafe". No locks will be acquired etc.

      arguments:
      * key         -- info key
      * newtype     -- "expected type", also used for creating new values
      * convert     -- if True: convert existing value (defaults to False)
      * check_type  -- if True: check whether the type of existing value is
                       a (sub-)type of newtype (defaults to True)
                       This arg can also be a type.
                       Has no effect if convert is set to True
      * create_kw   -- either None or a dict that will used as keyword args
                       when creating newtype
      """
      v = self.get ( key, do_fallback=True )
      if v is None:
         newv = newtype ( **create_kw ) if create_kw else newtype()
         self._info [key] = newv
         return newv
      elif convert:
         return newtype ( v )
      elif check_type:
         want_type = (
            check_type if ( type ( check_type ) is type ) else newtype
         )

         #if type ( v ) is want_type:
         if isinstance ( v, want_type ):
            return v
         else:
            raise TypeError (
               "key {k} should have type {t0}, but is a {t1}!".format (
                  k=key, t0=want_type, t1=type(v)
               )
            )
      else:
         return v
   # --- end of get_create (...) ---

   def get_desc_data ( self ):
      """Returns the DESCRIPTION data for this PackageInfo (by reading the
      R package file if necessary).
      """
      if 'desc_data' not in self._info:
         self._check_readonly()
         if 'desc_data' not in self._info:
            self._info ['desc_data'] = descriptionreader.read ( self )
      # -- end if;

      return self._info ['desc_data']
   # --- end of get_desc_data (...) ---

   def get_distmap_item ( self, allow_digest_create=False, no_digest=False ):
      """Returns a 2-tuple ( key, info ) for the distmap."""
      if no_digest:
         digest = None
      elif allow_digest_create:
         digest = self.make_distmap_hash()
      else:
         digest = self.hashdict [self.DISTMAP_DIGEST_TYPE]

      distfile = self.get ( "package_src_destpath" )
      repo     = self.get ( "origin" )

      return (
         distfile, (
            distfile,
            repo.name,
            os.path.relpath ( self.get ( "package_file" ), repo.distdir ),
            digest
         )
      )
   # --- end of get_distmap_item (...) ---

   def get_distmap_key ( self ):
      """Returns a key for the distmap."""
      return self.get ( "package_src_destpath" )
   # --- end of get_distmap_key (...) ---

   def get_distmap_value ( self, allow_digest_create=False, no_digest=False ):
      """Returns a data tuple for creating DistMapInfo instances.

      arguments:
      * allow_digest_create --
      * no_digest           -- use None as digest
      """
      return self.get_distmap_item ( allow_digest_create, no_digest ) [1]
   # --- end of get_distmap_value (...) ---

   def make_distmap_hash ( self ):
      """Creates (and returns) the distmap package file hash."""
      return self.make_hashes (
         { self.DISTMAP_DIGEST_TYPE, } ) [self.DISTMAP_DIGEST_TYPE]
   # --- end of make_distmap_hash (...) ---

   def make_hashes ( self, hashlist ):
      """Creates zero or more hashes and returns the hashdict.

      Note: the hashdict can also be accessed directly via <this>.hashdict.

      arguments:
      * hashlist -- list of hash names, e.g. "sha256", "md5"
      """
      pkgfile = self.get ( "package_file" )

      if self.hashdict:
         new_hashes = (
            frozenset ( hashlist ) - frozenset ( self.hashdict.keys() )
         )
      else:
         new_hashes = hashlist


      if new_hashes:
         self.hashdict.update (
            roverlay.digest.multihash_file ( pkgfile, new_hashes )
         )

      return self.hashdict
   # --- end of make_hashes (...) ---

   def revbump ( self, newrev=None ):
      """Do whatever necessary to revbump this pakages, that is set/update
      all data like src_uri_dest and ebuild_verstr.

      arguments:
      * newrev -- new revision, (current rev + 1) is used if this is None
      """
      rev     = self._info['rev'] + 1 if newrev is None else int ( newrev )
      rev_str = ( '-r' + str ( rev ) ) if rev > 0 else ''
      vstr    = (
         '.'.join ( str ( k ) for k in self._info['version'] ) + rev_str
      )

      # preserve destpath directory
      #  (this allows to handle paths like "a/b.tar/pkg.tgz" properly)
      #
      old_destpath = self ['package_src_destpath'].rpartition ( os.path.sep )

      # os.path.splitext does not "recognize" .tar.gz
      fhead, ftar, fext = old_destpath[2].rpartition ( '.tar' )
      if not ftar:
         fhead, fext = os.path.splitext ( fext )

      # FIXME: any way to get this reliably (+faster) done without a regex?
      #  ( a,b,c=fhead.rpartition ( '-r' ); try int(c) ...; ?)
      distfile = (
         old_destpath[0] + old_destpath[1]
         + self.EBUILDREV_REGEX.sub ( '', fhead ) + rev_str + ftar + fext
      )

      self._info ['rev']           = rev
      self._info ['ebuild_verstr'] = vstr
      self._info ['src_uri_dest']  = distfile

      return self
   # --- end of revbump (...) ---

   def __getitem__ ( self, key ):
      """Returns an item."""
      return self.get ( key, do_fallback=False )
   # --- end of __getitem__ (...) ---

   def __setitem__ ( self, key, value ):
      """Sets an item.

      arguments:
      * key --
      * value --

      raises: Exception when readonly
      """
      self._check_readonly()
      self._info [key] = value
   # --- end of __setitem__ (...) ---

   def set_direct_unsafe ( self, key, value ):
      """Sets an item. This operation is unsafe (write-accessibility won't
      be checked, data won't be validated).

      arguments:
      * key   --
      * value --
      """
      self._info [key] = value
   # --- end of set_direct_unsafe (...) ---

   def update_now ( self, **info ):
      """Updates the package info data with temporarily enabling write access.
      Data will be readonly after calling this method.

      arguments:
      * **info --
      """
      self.set_writeable()
      try:
         self.update ( **info )
      finally:
         self.set_readonly()
   # --- end of update_now (...) ---

   def update_unsafe ( self, **info ):
      """Updates the package info data without retrieving any locks or
      checking writability.
      Meant for usage with "package actions" (packagerules module).

      arguments:
      * **info --
      """
      # remove_auto has to be the last action (keyword order is not "stable")
      remove_auto = info.pop ( 'remove_auto', None )

      self._update ( info )
      if remove_auto:
         self._remove_auto ( remove_auto )
   # --- end of update_unsafe (...) ---

   def update ( self, **info ):
      """Uses **info to update the package info data.

      arguments:
      * **info --

      raises: Exception when readonly
      """
      # remove_auto has to be the last action (keyword order is not "stable")
      remove_auto = info.pop ( 'remove_auto', None )

      self._check_readonly()

      self._update ( info )
      if remove_auto:
         self._remove_auto ( remove_auto )
   # --- end of update (**kw) ---

   def add_evar ( self, evar ):
      """Adds an ebuild variable.

      arguments:
      * evar   --
      """
      #self._check_readonly()

      if not hasattr ( self, '_evars' ):
         self._evars = dict()
      # -- end if;
      self._evars [evar.get_pseudo_hash()] = evar
   # --- end of add_evar (...) ---

   def parse_ebuild_src_uri ( self, category_name ):
      return roverlay.util.ebuildparser.SrcUriParser.from_file (
         self._info ['ebuild_file'], self.create_vartable ( category_name )
      )
   # --- end of parse_ebuild_src_uri (...) ---

   def parse_ebuild_distfiles ( self, category_name ):
      parser = self.parse_ebuild_src_uri ( category_name )
      for distfile in parser.iter_local_files():
         yield distfile
   # --- end of parse_ebuild_distfiles (...) ---

   def get_evars ( self ):
      """Returns all ebuild variables."""
      if hasattr ( self, '_evars' ):
         return list ( self._evars.values() )
      else:
         return None
   # --- end of get_evars (...) ---

   def _update ( self, info ):
      """Updates self._info using the given info dict.

      arguments:
      * info --
      """
      initial = len ( self._info ) == 0

      for key, value in info.items():

         if key in self.__class__._UPDATE_KEYS_SIMPLE or (
            initial and key in self.__class__._UPDATE_KEYS_SIMPLE_INITIAL
         ):
            self._info [key] = value

         elif key in self.__class__._UPDATE_KEYS_FILTER_NONE:
            if value is not None:
               self._info [key] = value

         elif key == 'origin':
            self._info ['origin'] = value
            self._info ['repo_name'] = value.name

         elif key == 'filename':
            self._use_filename ( value )

         elif key == 'pvr':
            self._use_pvr ( value )

         elif key == 'suggests':
            # FIXME/TODO: remove
            self._info ['has_suggests'] = value

         elif key == 'filepath':
            self._use_filepath ( value )

         elif key == 'remove':
            for k in value:
               try:
                  if k in self._info: del self._info [k]
               except KeyError:
                  pass

         elif key == 'make_desc_data':
            if value:
               self.get_desc_data()

         else:
            self.logger.error (
               "in _update(): unknown info key {!r}!".format ( key )
            )
      # -- end for;

      # FIXME (if needed):
      #  the package rule parser doesn't create lazy actions, currently,
      #  so calling apply_lazy_actions() would do nothing
      ##self.apply_lazy_actions()
   # --- end of _update (...) ---

   def _use_filename ( self, _filename ):
      """auxiliary method for update(**kw)

      arguments:
      * _filename --
      """
      filename_with_ext = _filename

      # remove .tar.gz .tar.bz2 etc.
      filename = PackageInfo.PKGSUFFIX_REGEX.sub ( '', filename_with_ext )

      self.logger = logging.getLogger ( filename )

      package_name, sepa, package_version = filename.partition (
         config.get ( 'R_PACKAGE.name_ver_separator', '_' )
      )

      if not sepa:
         # file name unexpected, tarball extraction will (probably) fail
         self.logger.error ( "unexpected file name {!r}.".format ( filename ) )
         raise Exception   ( "cannot use file {!r}.".format ( filename ) )
         return

      version_str = PackageInfo.EBUILDVER_REGEX.sub ( '.', package_version )

      try:
         version = tuple ( int ( z ) for z in version_str.split ( '.' ) )
         self._info ['version'] = (
            roverlay.versiontuple.IntVersionTuple ( version )
         )
      except ValueError as ve:
         # version string is malformed, cannot use it
         self.logger.error (
            "Cannot parse version string {!r} for {!r}".format (
               _filename, version_str
            )
         )
         raise

      # using package name as name (unless modified later),
      #  using pkg_version for the ebuild version

      # removing illegal chars from the package_name
      ebuild_name = strutil.fix_ebuild_name ( package_name )

      # for DescriptionReader
      self._info ['package_name']       = package_name
      self._info ['rev']                = 0
      self._info ['name']               = ebuild_name
      self._info ['ebuild_verstr']      = version_str
      self._info ['package_filename']   = filename_with_ext
      self._info ['package_filename_x'] = filename
   # --- end of _use_filename (...) ---

   def _use_pvr ( self, pvr ):
      # 0.1_pre2-r17 -> ( ( 0, 1 ), ( 17 ) )
      pv_str, DONT_CARE, pr_str    = pvr.partition    ( '-r' )
      pv,     DONT_CARE, pv_suffix = pv_str.partition ( '_'  )

      # non-digit chars in pv are not supported
      pv_list = [ int(z) for z in pv.split ( '.' ) ]

      if pv_suffix:
         # not supported
         self._info ['version'] = (
            roverlay.versiontuple.SuffixedIntVersionTuple (
               pv_list, pv_suffix
            )
         )
      else:
         self._info ['version'] = (
            roverlay.versiontuple.IntVersionTuple ( pv_list )
         )

      self._info ['rev'] = int ( pr_str ) if pr_str else 0

      self._info ['ebuild_verstr'] = pvr
   # --- end of _use_pvr (...) ---

   def _remove_auto ( self, ebuild_status ):
      """Removes all keys from this PackageInfo instance that are useless
      after entering status 'ebuild_status' (like ebuild in overlay and
      written -> don't need the ebuild string etc.)
      """
      if ebuild_status == 'ebuild_written':

         # selectively delete entries that are no longer required

         for key in self.__class__._REMOVE_KEYS_EBUILD:
            try:
               del self._info [key]
            except KeyError:
               pass
      # -- if
   # --- end of _remove_auto (...) ---

   def _use_filepath ( self, _filepath ):
      """auxiliary method for update(**kw)

      arguments:
      * _filepath --
      """
      self.logger.warn (
         'Please note that _use_filepath is only meant for testing.'
      )
      filepath = os.path.abspath ( _filepath )
      self ['package_file'] = filepath
      self._use_filename ( os.path.basename ( filepath ) )
   # --- end of _use_filepath (...) ---

   def create_vartable ( self, category ):
      PN  = self._info ['name']
      PV  = str ( self._info ['version'] )
      PR  = str ( self._info ['rev'] )
      PVR = PV if PR == '0' else ( PV + '-' + PR )

      return {
         'P'        : PN + '-' + PV,
         'PN'       : PN,
         'PV'       : PV,
         'PR'       : PR,
         'PVR'      : PVR,
         'PF'       : PN + PVR,
         'CATEGORY' : category,
      }
   # --- end of create_vartable (...) ---

   def __str__ ( self ):
      return "<PackageInfo for {pkg}>".format (
         pkg=self.get (
            'package_file', fallback_value='[unknown file]', do_fallback=True
      ) )
   # --- end of __str__ (...) ---
