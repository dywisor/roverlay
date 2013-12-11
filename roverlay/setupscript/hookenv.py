# R overlay -- setup script, env for managing hooks
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import errno
import fnmatch
import os


import roverlay.fsutil
import roverlay.static.hookinfo
import roverlay.util.counter
import roverlay.util.dictwalk
import roverlay.util.objects
import roverlay.setupscript.baseenv


class HookOverwriteControl ( object ):
   """Object for deciding whether a file/link/... is allowed to be
   overwritten by a hook link."""

   OV_NONE      = 0
   OV_SYM_DEAD  = 2**0
   OV_SYM_EXIST = 2**1
   OV_SYM       = OV_SYM_DEAD|OV_SYM_EXIST
   OV_FILE      = 2**2
   OV_ALL       = ( 2**3 ) - 1

   OV_KEYWORDS = {
      'none'  : OV_NONE,
      'dead'  : OV_SYM_DEAD,
      'links' : OV_SYM,
      'all'   : OV_ALL,
   }

   @classmethod
   def from_str ( cls, vstr ):
      """Returns a new instance representing one of the control modes from
      OV_KEYWORDS.

      arguments:
      * vstr --
      """
      return cls ( cls.OV_KEYWORDS[vstr] )
   # --- end of from_str (...) ---

   def __init__ ( self, value ):
      """HookOverwriteControl constructor.

      arguments:
      * value -- the control mode (has to be an int, usually a comibination of
                 the OV_* masks provided by the HookOverwriteControl class)
      """
      super ( HookOverwriteControl, self ).__init__()
      assert isinstance ( value, int ) and value >= 0
      self.value = value
   # --- end of __init__ (...) ---

   def can_overwrite ( self, mask=None ):
      """Returns whether the control mode allows to overwrite files/links
      with the given mask.

      The return value should be interpreted in boolean context, but can
      be an int.

      arguments:
      * mask --
      """
      if mask is None:
         return self.value == self.OV_NONE
      else:
         return self.value & mask
   # --- end of can_overwrite (...) ---

   def overwrite_dead_symlinks ( self ):
      """Returns whether overwriting of dangling/broken symlinks is allowed."""
      return self.value & self.OV_SYM_DEAD

   def overwrite_symlinks ( self ):
      """Returns whether overwriting of arbitrary symlinks is allowed."""
      return self.value & self.OV_SYM

   def overwrite_all ( self ):
      """Returns True if the control mode does not restrict overwriting,
      else False."""
      return self.value == self.OV_ALL

   def get_str ( self ):
      """Returns a string representation of the control mode suitable for
      printing."""
      value = self.value
      def gen_words():
         if value == self.OV_NONE:
            yield "none"
         else:
            if value & self.OV_SYM_EXIST:
               if value & self.OV_SYM_DEAD:
                  yield "symlinks"
               else:
                  yield "symlinks to existing files"
            elif value & self.OV_SYM_DEAD:
               yield "broken symlinks"

            if value & self.OV_FILE:
               yield "files"
      # --- end of gen_words (...) ---

      return ', '.join ( gen_words() ) + " (0x{:x})".format ( value )
   # --- end of get_str (...) ---

   __str__ = get_str

# --- end of HookOverwriteControl ---


class HookScriptBase ( roverlay.util.objects.Referenceable ):
   """A hook script."""

   CACHE_REF = True

   def __init__ ( self,
      fspath, filename=None, priority=None, is_hidden=False
   ):
      """HookScriptBase constructor.

      arguments:
      * fspath    -- absolute path to the hook script
      * filename  -- name of the hook script
                      Defaults to os.path.basename(fspath).
      * priority  -- priority of the hook script.
                     Defaults to None (no priority).
                     Passing True as priority enables filename-based detection.
      * is_hidden -- whether the script is "hidden" or not. Defaults to False.
      """
      super ( HookScriptBase, self ).__init__()

      fname = (
         filename if filename is not None else os.path.basename ( fspath )
      )

      self.filename = fname

      if priority is True:
         prio_str, dash, remainder = fname.partition ( '-' )
         if prio_str and dash and remainder:
            try:
               prio = int ( prio_str, 10 )
            except ValueError:
               self.priority = None
            else:
               self.priority = prio
               fname         = remainder
         else:
            self.priority = None
      else:
         self.priority = priority

      self.name      = os.path.splitext ( fname )[0]
      self.fspath    = fspath
      self.is_hidden = is_hidden
   # --- end of __init__ (...) ---

   def __str__ ( self ):
      yesno = lambda k: 'y' if k else 'n'

      return "<{cls} {name!r}, hidden={h} prio={p}>".format (
         cls  = self.__class__.__name__,
         name = self.name,
         h    = yesno ( self.is_hidden ),
         p    = (
            "auto" if self.priority is None else
               ( "IGNORE" if self.priority < 0 else self.priority )
         ),
      )
   # --- end of __str__ (...) ---

   def has_priority ( self ):
      """Returns True if this hook script has a valid priority."""
      return self.priority is not None and self.priority >= 0
   # --- end of has_priority (...) ---

   def is_visible ( self ):
      """Returns True if this hook script can be used for linking/...,
      else False."""
      return not self.is_hidden and (
         self.priority is None or self.priority >= 0
      )
   # --- end of is_visible (...) ---

# --- end of HookScriptBase ---


class UserHookScript ( HookScriptBase ):
   """A hook script that resides in the user's hook script dir."""

   @classmethod
   def create_for_hook (
      cls, hook, destdir, event_name, priority_gen,
      file_ext='.sh', digit_len=2
   ):
      """Creates a UserHookScript instance that can be used for linking
      a HookScript in the given directory.

      arguments:
      * hook         -- HookScript object
      * destdir      -- directory where the link to the HookScript will be
                        created
      * event_name   -- name of the event (usually basename of destdir)
      * priority_gen -- priority generator (or an int) which will be used
                        if the HookScript object doesn't provide a priority
      * file_ext     -- file extension of the link name. Defautls to '.sh',
                        which shouldn't be changed, because the "mux.sh"
                        script recognizes file with this extension only.
      * digit_len    -- digit length of the priority part of the file name.
                        ("d^{>=digit_len}-{hook name}{file_ext}")
                        Defaults to 2.
      """
      if type ( priority_gen ) == int:
         prio = priority_gen
      elif hook.has_priority():
         prio = hook.priority
      else:
         prio = next ( priority_gen )

      filename = "{prio:0>{dlen}}-{name}{fext}".format (
         prio = prio,
         dlen = digit_len,
         name = hook.name,
         fext = file_ext,
      )

      instance = cls (
         ( destdir + os.sep + filename ), filename=filename,
         event=event_name, priority=prio,
      )
      instance.set_hookscript ( hook )
      return instance
   # --- end of create_for_hook (...) ---

   def __init__ ( self, fspath, filename=None, event=None, priority=True ):
      """UserHookScript constructor.

      arguments:
      * fspath    -- absolute path to the hook script
      * filename  -- name of the hook script
                      Defaults to os.path.basename(fspath).
      * event     -- name of the event to which this script belongs to,
                      e.g. "overlay_success" (or None). Defaults to None.
      * priority  -- priority of the hook script.
                      Defaults to True (auto-detect).
      """
      super ( UserHookScript, self ).__init__ (
         fspath, filename=filename, priority=priority
      )

      self.hook_script_fspath = os.path.realpath ( self.fspath )
      if (
         os.path.islink ( self.fspath ) or not os.path.lexists ( self.fspath )
      ):
         self.hook_script_ref = None
      else:
         # False means that this UserHookScript is not a link
         self.hook_script_ref = False

      self.event = event
   # --- end of __init__ (...) ---

   def set_hookscript ( self, script_obj, strict=True ):
      """Assigns a HookScript to this UserHookScript. Also establishes
      a back-reference in the hook script.

      arguments:
      * script_obj -- HookScript object
      * strict     -- whether to fail if this UserHookScript is not a link
                       (True) or not (False). Defaults to True.
      """
      if strict and script_obj and self.hook_script_ref is False:
         raise Exception (
            "user hook script {} is not a link!".format ( self.fspath )
         )
      elif script_obj is None or script_obj is False:
         self.hook_script_ref = False

      else:
         self.hook_script_ref = script_obj.get_ref()
         script_obj.add_user_script ( self )
   # --- end of set_hookscript (...) ---

   def has_hookscript ( self ):
      """Returns whether this object has a hook script of any kind (either
      a HookScript object or a file)."""
      return self.hook_script_ref is not None
   # --- end of has_hookscript (...) ---

   def get_hookscript ( self, unsafe=False ):
      """Returns the HookScript object to which this instance belongs to.
      Returns None if this UserHookScript is not a link.

      arguments:
      * unsafe -- do not raise ObjectDisappeared if not linked or hook script
                  disappeared and return None instead.

      Raises: roverlay.util.objects.ObjectDisappeared
      """
      ref = self.hook_script_ref
      if ref is False:
         return None
      elif unsafe:
         return None if ref is None else ref.deref_unsafe()
      elif ref is None:
         raise roverlay.util.objects.ObjectDisappeared()
      else:
         return ref.deref_safe()
   # --- end of get_hookscript (...) ---

   def get_hookscript_path ( self ):
      """Returns the link target (can be identical to the fspath attribute)."""
      return self.hook_script_fspath
   # --- end of get_hookscript_path (...) ---

   def get_dest_name ( self ):
      """Returns the link name."""
      return self.filename
   # --- end of get_dest_name (...) ---

# --- end of UserHookScript ---


class HookScript ( HookScriptBase ):
   """A hook script that resides in the 'static data' dir."""

   def __init__ ( self, fspath, filename=None ):
      """HookScript constructor.
      Also looks up static information (hook priority etc.).

      arguments:
      * fspath    -- absolute path to the hook script
      * filename  -- name of the hook script
                      Defaults to os.path.basename(fspath).
      """
      super ( HookScript, self ).__init__ ( fspath, filename=filename )

      static_entry = roverlay.static.hookinfo.get ( self.name, None )
      if static_entry is not None:
         self.default_events = static_entry[0]
         self.priority       = static_entry[1]
         self.is_hidden      = static_entry[2]
      else:
         self.default_events = False

      self.user_script_refs = set()
   # --- end of __init__ (...) ---

   def add_user_script ( self, user_script ):
      """Registers a UserHookScript linking to this object (as reference)."""
      self.user_script_refs.add ( user_script.get_ref() )
   # --- end of add_user_script (...) ---

   def iter_user_scripts ( self, ignore_missing=True, check_backref=True ):
      """Iterates over all UserHookScripts linked to this object.

      arguments:
      * ignore_missing -- do not fail if a referenced object disappeared.
                          Defaults to True.
      * check_backref  -- if True: ignore UserHookScripts that do no longer
                          link to this object. Defaults to True.
      """
      if ignore_missing:
         if check_backref:
            for ref in self.user_script_refs:
               obj = ref.deref_unsafe()
               if (
                  obj is not None and
                  obj.get_hookscript ( unsafe=True ) is self
               ):
                  yield obj
         else:
            for ref in self.user_script_refs:
               obj = ref.deref_unsafe()
               if obj is not None:
                  yield obj
      elif check_backref:
         for ref in self.user_script_refs:
            obj = ref.deref_safe()
            if obj.get_hookscript ( unsafe=False ) is self:
               yield obj
      else:
         for ref in self.user_script_refs:
            yield ref.deref_safe()
   # --- end of iter_user_scripts (...) ---

# --- end of HookScript ---


class HookScriptDirBase ( roverlay.util.objects.Referenceable ):
   """A directory containing hook scripts."""

   HOOK_SCRIPT_CLS  = None
   DIRNAMES_IGNORE  = frozenset({ '.*', })
   FILENAMES_IGNORE = frozenset({ '.*', })

   def dirname_filter ( self, dirname, _fnmatch=fnmatch.fnmatch ):
      """Returns True if dirname does not match any pattern in
      DIRNAMES_IGNORE, else False.

      arguments:
      * dirname  --
      * _fnmatch -- function for matching dirname against pattern.
                     Defaults to fnmatch.fnmatch.
      """
      return all (
         not _fnmatch ( dirname, pat ) for pat in self.DIRNAMES_IGNORE
      )
   # --- end of dirname_filter (...) ---

   def filename_filter ( self, filename, _fnmatch=fnmatch.fnmatch ):
      """Returns True if dirname does not match any pattern in
      FILENAMES_IGNORE, else False.

      arguments:
      * filename  --
      * _fnmatch  -- function for matching filename against pattern.
                      Defaults to fnmatch.fnmatch.
      """
      return all (
         not _fnmatch ( filename, pat ) for pat in self.FILENAMES_IGNORE
      )
   # --- end of filename_filter (...) ---

   def __init__ ( self, root ):
      """HookScriptDirBase constructor.

      arguments:
      * root -- absolute filesystem path to the hook script dir's root dir
      """
      super ( HookScriptDirBase, self ).__init__()

      self.root     = root
      self.scripts  = collections.OrderedDict()
      self.writable = None
   # --- end of __init__ (...) ---

   def __len__ ( self ):
      """Returns the number of scripts."""
      # also used in boolean context
      return len ( self.scripts )
   # --- end of __len__ (...) ---

   def get_fspath ( self, relpath=None ):
      """Returns the filesystem path of this dir or of a sub dir/file.

      arguments:
      * relpath -- sub dir/file path relative to the root. Defaults to None.
      """
      if relpath:
         return self.root + os.sep + str ( relpath )
      else:
         return self.root
   # --- end of get_fspath (...) ---

   def get_script ( self, name ):
      """Returns the script with the given name.
      Typically faster than find_by_name(), but less accurate when dealing
      with user scripts.

      arguments:
      * name -- script name
      """
      script = self.scripts [name]
      if script.is_visible():
         return script
      else:
         raise KeyError ( name )
   # --- end of get_scripts (...) ---

   def iter_scripts ( self ):
      """Generator that yields all visible scripts."""
      for script in self.scripts.values():
         if script.is_visible():
            yield script
   # --- end of iter_scripts (...) ---

   def find_all ( self, condition, c_args=(), c_kwargs={} ):
      """Generator that yields all visible scripts for which
      condition ( script, *c_args, **c_kwargs ) evaluates to True.

      arguments:
      * condition -- function/callable
      * c_args    -- packed args for condition. Defaults to ().
      * c_kwargs  -- packed keyword args for condition. Defaults to {}.
      """
      for script in self.iter_scripts():
         if condition ( script, *c_args, **c_kwargs ):
            yield script
   # --- end of find_all (...) ---

   def find ( self, condition, c_args=(), c_kwargs={}, **kw ):
      """Like find_all(), but returns the first match, if any, else None.

      arguments:
      * condition -- function/callable
      * c_args    -- packed args for condition. Defaults to ().
      * c_kwargs  -- packed keyword args for condition. Defaults to {}.
      * **kw      -- additional keyword args for find_all().
      """
      try:
         return next ( self.find_all ( condition, c_args, c_kwargs, **kw ) )
      except StopIteration:
         return None
   # --- end of find (...) ---

   def find_all_by_name ( self, name, **kw ):
      """Generator that yields all visible scripts whose names matches the
      given one.

      arguments:
      * name --
      * **kw -- additional keyword args for find_all()
      """
      return self.find_all (
         lambda s, n: s.name == n, c_args=( name, ), **kw
      )
   # --- end of find_all_by_name (...) ---

   def find_by_name ( self, name, **kw ):
      """Like find_all_by_name(), but returns the first match, if any,
      else None.

      arguments:
      * name --
      * **kw --
      """
      try:
         return next ( self.find_all_by_name ( name, **kw ) )
      except StopIteration:
         return None
   # --- end of find_by_name (...) ---

   def find_all_by_name_begin ( self, prefix, **kw ):
      """Generator that yields all visible scripts whose names begin with
      the given prefix.

      arguments:
      * prefix --
      * **kw   -- additional keyword args for find_all()
      """
      return self.find_all (
         lambda s, pre: s.name.startswith ( pre ), c_args=( prefix, ), **kw
      )
   # --- end of find_all_by_name_begin (...) ---

   def scan ( self ):
      """Scans the filesystem location of this hook script dir for hook
      scripts and adds them to the scripts attribute.
      """
      root = self.root
      try:
         filenames = sorted ( os.listdir ( root ) )
      except OSError as oserr:
         if oserr.errno != errno.ENOENT:
            raise
      else:
         HOOK_CLS = self.HOOK_SCRIPT_CLS
         for fname in filenames:
            if self.filename_filter ( fname ):
               fspath = root + os.sep + fname
               if os.path.isfile ( fspath ):
                  script_obj = HOOK_CLS ( fspath, filename=fname )
                  self.scripts [script_obj.name] = script_obj
   # --- end of scan (...) ---

# --- end of HookScriptDirBase ---


class NestedHookScriptDirBase ( HookScriptDirBase ):
   """A hook script dir with a nested structure (hook scripts in subdirs)."""

   SUBDIR_CLS = collections.OrderedDict

   def get_script ( self, name ):
      """Returns a list of all visible scripts with the given name.

      arguments:
      * name --
      """
      return list ( self.find_all_by_name ( name ) )
   # --- end of get_script (...) ---

   def scan ( self, prune_empty=True ):
      """Scans the hook script dir for hook scripts.
      Calls scan_scripts() when done.

      arguments:
      * prune_empty -- whether to keep empty dirs in the scripts dict
                       (False) or not (True). Defaults to True.
      """
      def get_script_name ( filename ):
         """Returns the script name of the given filename.

         arguments:
         * filename --
         """
         prio, sepa, name = filename.partition ( '-' )
         if name:
            try:
               prio_int = int ( prio, 10 )
            except ValueError:
               return filename
            else:
               return name
         else:
            return filename
      # --- end of get_script_name (...) ---

      def create_hookscript (
         fspath, filename, root, HOOK_SCRIPT_CLS=self.HOOK_SCRIPT_CLS
      ):
         """Creates a new hook script object.

         arguments:
         * fspath          -- absolute path to the script file
         * filename        -- name of the script file
         * root            -- directory of the script file
         * HOOK_SCRIPT_CLS -- hook script class.
                               Defaults to elf.HOOK_SCRIPT_CLS.
         """
         return HOOK_SCRIPT_CLS ( fspath, filename=filename )
      # --- end of create_hookscript (...) ---

      new_scripts = roverlay.fsutil.get_fs_dict (
         self.root,
         create_item     = create_hookscript,
         dict_cls        = self.SUBDIR_CLS,
         dirname_filter  = self.dirname_filter,
         filename_filter = self.filename_filter,
         include_root    = False,
         prune_empty     = prune_empty,
         file_key        = get_script_name,
      )
      self.scripts.update ( new_scripts )
      self.scan_scripts()
   # --- end of scan (...) ---

   def scan_scripts ( self ):
      """Performs additional actions after scanning scripts, e.g.
      setting correct event attributes.
      """
      for event, hook in self.iter_scripts():
         if hook.event is None:
            hook.event = event
   # --- end of scan (...) ---

   def iter_scripts ( self, event=None, ignore_missing=False ):
      """Generator that yields all visible script.

      Depending on the event parameter, the items are either
      2-tuples(event_name, script) (event is None) or scripts.

      arguments:
      * event          -- specific event to iterator over (or None for all)
                           Defaults to None.
      * ignore_missing -- do not fail if event subdir is missing.
                           only meaningful if event is not None
                           Defaults to False.
      """

      # roverlay uses per-event subdirs containing hook files
      SUBDIR_CLS = self.SUBDIR_CLS

      if event is None:
         for event_name, subdir in self.scripts.items():
            if isinstance ( subdir, SUBDIR_CLS ):
               for hook in subdir.values():
                  if isinstance ( hook, HookScriptBase ) and hook.is_visible():
                  #if not isinstance ( hook, SUBDIR_CLS ):
                     yield ( event_name, hook )
      else:
         try:
            subdir = self.scripts [event]
         except KeyError:
            pass
         else:
            assert isinstance ( subdir, SUBDIR_CLS )
            for script in subdir.values():
               yield script
      # -- end if
   # --- end of iter_scripts (...) ---

   def find_all ( self, condition, c_args=(), c_kwargs={}, event=None ):
      """Generator that yields all scripts matching the given condition.
      Can optionally be restricted to a single event subdir.
      See HookScriptDirBase.find_all() for details.

      arguments:
      * condition --
      * c_args    --
      * c_kwargs  --
      * event     --
      """
      if event is None:
         for event_name, script in self.iter_scripts():
            if condition ( script, *c_args, **c_kwargs ):
               yield script
      else:
         for script in self.iter_scripts ( event=event, ignore_missing=True ):
            if condition ( script, *c_args, **c_kwargs ):
               yield script
   # --- end of find_all_by_name (...) ---

   def get_subdir ( self, event_name ):
      """Returns the requested event subdir dict (by creating it if necessary)

      arguments:
      * event_name --
      """
      subdir = self.scripts.get ( event_name, None )
      if subdir is None:
         subdir = self.SUBDIR_CLS()
         self.scripts [event_name] = subdir
      # -- end if
      return subdir
   # --- end of get_subdir (...) ---


# --- end of NestedHookScriptDirBase ---


class UserHookScriptDir ( NestedHookScriptDirBase ):
   """A nested hook script dir that contains UserHookScripts."""

   HOOK_SCRIPT_CLS = UserHookScript

   def __init__ ( self, *args, **kwargs ):
      """See HookScriptDirBase.__init__().

      arguments:
      * *args    -- passed to super().__init__()
      * **kwargs -- passed to super().__init__()
      """
      super ( UserHookScriptDir, self ).__init__ ( *args, **kwargs )
      # per-event prio gen
##      self._prio_gen = collections.defaultdict (
##         self._create_new_prio_gen,
##      )
      self._prio_gen = self._create_new_prio_gen()
   # --- end of __init__ (...) ---

   def _create_new_prio_gen ( self ):
      """Creates and returns a new priority generator."""
      return roverlay.util.counter.SkippingPriorityGenerator (
         10, skip=roverlay.static.hookinfo.get_priorities()
      )
   # --- end of _create_new_prio_gen (...) ---

   def _get_prio_gen ( self, event_name ):
      """Returns a priority generator for the given event.

      arguments:
      * event_name --
      """
      return self._prio_gen
   # --- end of _get_prio_gen (...) ---

   def scan_scripts ( self ):
      """Performs additional actions after scanning the directory."""
      prios = collections.defaultdict ( list )
      for event, hook in self.iter_scripts():
         if hook.event is None:
            hook.event = event
         if hook.has_priority():
            prios [event].append ( hook.priority )
      # -- end for

      for event, priolist in prios.items():
         self._get_prio_gen ( event ).add_generated ( priolist )
   # --- end of scan (...) ---

   def create_hookdir_refs ( self,
      hook_dir, overwrite=False, compare_fspath=True
   ):
      """Establishes links (references) from user scripts to hook scripts
      in the given hook dir (which usually creates backreferences).

      arguments:
      * hook_dir       -- hook directory (HookScriptDir)
      * overwrite      -- overwrite existing references
      * compare_fspath -- if True: link only if filesystem paths
                                   (link target, script filepath) match
                          else: link if names match
                           Defaults to True.
      """
      for event, user_script in self.iter_scripts():
         if overwrite or not user_script.has_hookscript():
            try:
               hook = hook_dir.get_script ( user_script.name )
            except KeyError:
               pass
            else:
               if hook is not None and (
                  not compare_fspath or user_script.fspath == hook.fspath
               ):
                  user_script.set_hookscript ( hook )
   # --- end of create_hookdir_refs (...) ---

   def make_hookdir_refs ( self, hook_dir, overwrite=False ):
      """Calls create_hookdir_refs() twice, first with compare_fspath=True,
      and then with compare_fspath=False, so that exact matches are preferred.

      See create_hookdir_refs() for details.

      arguments:
      * hook_dir  --
      * overwrite --
      """
      # try exact fs path matches first, then use name-based ones
      self.create_hookdir_refs (
         hook_dir, overwrite=overwrite, compare_fspath=True
      )
      self.create_hookdir_refs (
         hook_dir, overwrite=overwrite, compare_fspath=False
      )
   # --- end of make_hookdir_refs (...) ---

   def add_entry_unsafe ( self, hook ):
      """Adds a hook object (UserHookScript) to this script directory.

      arguments:
      * hook -- hook object (the event attribute has to be set)
      """
      if hook.event:
         self.get_subdir ( hook.event ) [hook.name] = hook
      else:
         raise AssertionError ( "hook.event is not set." )
      return True
   # --- end of add_entry_unsafe (...) ---

   def get_entry_for_link ( self, hook, event_name ):
      """Returns a UserHookScript object that can be used to link against
      the given HookScript object.

      arguments:
      * hook       --
      * event_name --
      """
      existing_entry = self.find_by_name ( hook.name, event=event_name )
      if existing_entry:
         return existing_entry
      else:
         user_hook = UserHookScript.create_for_hook (
            hook         = hook,
            destdir      = ( self.root + os.sep + event_name ),
            event_name   = event_name,
            priority_gen = self._get_prio_gen ( event_name )
         )
         return user_hook
   # --- end of get_entry_for_link (...) ---

# --- end of UserHookScriptDir ---


class HookScriptDir ( HookScriptDirBase ):

   HOOK_SCRIPT_CLS = HookScript

   def iter_linked ( self ):
      """Generator that yields
      2-tuples ( HookScript, list( UserHookScript references ) ).

      The UserHookScript references list can be empty.
      """
      for script in self.iter_scripts():
         yield ( script, list ( script.iter_user_scripts() ) )
   # --- end of iter_linked (...) ---

   def iter_default_scripts ( self, unpack=False ):
      """Generator that yields all default scripts.

      Depending on the unpack parameter, the items are either HookScripts
      (False) or 2-tuples (event, HookScript) (True).

      arguments:
      * unpack -- defaults to False
      """
      if unpack:
         for script in self.iter_scripts():
            if script.default_events:
               for event in script.default_events:
                  yield ( event, script )
      else:
         for script in self.iter_scripts():
            if script.default_events:
               yield script
   # --- end of iter_default_scripts (...) ---

   def get_default_scripts ( self ):
      """
      Returns a dict containg per-event lists of the default HookScripts.
      """
      return roverlay.util.dictwalk.dictmerge (
         self.iter_default_scripts ( unpack=True ),
         get_value=lambda kv:kv[1]
      )
   # --- end of get_default_scripts (...) ---

# --- end of HookScriptDir ---



class SetupHookEnvironment (
   roverlay.setupscript.baseenv.SetupSubEnvironment
):
   """'Environment' for managing hooks."""

   NEEDS_CONFIG_TREE = True

   def format_hook_info_lines ( self,
      info, sort_info=True, append_newline=False
   ):
      """Generator that accepts a list of
      (scripts, list ( event to which script is linked, priority)) and yields
      formatted text lines "<script name> | <event>(<prio>)..." for each
      script.

      arguments:
      * info           --
      * sort_info      -- whether to sort info (by "has events",name)
                           Defaults to True.
      * append_newline -- whether to append a newline at the end
                           Defaults to False.
      """
      max_name_len = min ( 30, max ( len(x[0]) for x in info ) )

      event_names  = set()
      for name, ev_prio in info:
         event_names.update ( item[0] for item in ev_prio )

      # len(...) + 4 == len(...) + len("(__)")
      event_words = [
         ( ev, (4+len(ev)) * ' ' ) for ev in sorted ( event_names )
      ]

      if sort_info:
         my_info = sorted ( info, key=lambda k: ( not k[1], k[0] ) )
      else:
         my_info = info

      for name, event_prio_list in my_info:
         events   = dict ( event_prio_list )
         get_prio = lambda p: ( "UU" if p is None else p )

         yield "{name:>{nlen}} | {ev}".format (
            name=name, nlen=max_name_len,
            ev=' '.join (
               (
                  "{name}({prio:0>2})".format (
                     name=ev, prio=get_prio ( events[ev] )
                  ) if ev in events else replacement
                  for ev, replacement in event_words
               )
            )
         ).rstrip()
      # -- end for

      if append_newline:
         yield ""
   # --- end of format_hook_info_lines (...) ---

   def get_hook_root_info ( self, nonlinked_only=False ):
      """Returns a list with information about the hook root suitable
      for being formatted by format_hook_info_lines().

      arguments:
      * nonlinked_only -- whether to exclude scripts that are linked to
                          >= 1 event(s) (True) or not (False).
                          Defaults to False.
      """
      if nonlinked_only:
         return [
            ( script.name, [] )
            for script, user_scripts in self.hook_root.iter_linked()
               if not user_scripts
         ]
      else:
         return [
            (
               script.name,
               [ ( s.event or "undef", s.priority ) for s in user_scripts ]
            )
            for script, user_scripts in self.hook_root.iter_linked()
         ]
   # --- end of get_hook_root_info (...) ---

   def get_user_hook_info ( self ):
      """Returns a list with information about the user hook root suitable
      for being formatted by format_hook_info_lines().
      """
      return [
         ( s.name, [ ( s.event or "undef", s.priority ) ] )
         for event, s in self.user_hooks.iter_scripts()
      ]
   # --- end of get_user_hook_info (...) ---

   def gen_hook_info_lines ( self, append_newline=True ):
      """Generator that yields (formatted) text lines with information
      about hooks in the user hook root and the hook root."""
      info = (
         self.get_user_hook_info()
         + self.get_hook_root_info ( nonlinked_only=True )
      )
      for line in self.format_hook_info_lines (
         info, append_newline=append_newline
      ):
         yield line
   # --- end of gen_hook_info_lines (...) ---

   def setup ( self ):
      """Performs subclass-specific initialization."""
      self.hook_overwrite_control = self.setup_env.hook_overwrite

      additions_dir = self.config.get ( 'OVERLAY.additions_dir', None )

      self.hook_root = HookScriptDir (
         os.path.join ( self.setup_env.data_root, 'hooks' )
      )
      self.hook_root.scan()

      if additions_dir:
         self.user_hooks = UserHookScriptDir (
            os.path.join ( additions_dir, 'hooks' )
         )
         self.user_hooks.writable = (
            self.setup_env.fs_private.check_writable (
               self.user_hooks.get_fspath ( '.keep' )
            )
         )
         self.user_hooks.scan()
         if self.hook_root:
            self.user_hooks.make_hookdir_refs ( self.hook_root )
      else:
         self.user_hooks = None
   # --- end of setup (...) ---

   def check_link_allowed ( self, source, link, link_name ):
      """Returns whether symlinking link->source is allowed.
      This decision is made based on the fileystem "state" of the link
      and the HookOverwriteControl object (bound to this instance).

      arguments:
      * source    -- link destination (absolute filesystem path)
      * link      -- link file (absolute filesystem path)
      * link_name -- file name of the link
      """
      if os.path.lexists ( link ):
         allow_overwrite = False

         skip_message = (
            'Skipping activation of hook {!r} - '.format ( link_name )
         )
         ov_message = 'Overwriting hook {!r} - '.format ( link_name )


         if os.path.islink ( link ):
            linkdest = os.path.realpath ( link )

            if linkdest == source or linkdest == os.path.realpath ( source ):
               self.info ( skip_message + "already set up.\n" )
               allow_overwrite = None

            elif os.path.exists ( link ):
               if self.hook_overwrite_control.overwrite_symlinks():
                  self.info ( ov_message + "symlink.\n" )
                  allow_overwrite = True
               else:
                  self.error ( skip_message + "symlink.\n" )

            elif self.hook_overwrite_control.overwrite_dead_symlinks():
               self.info ( ov_message + "broken symlink.\n" )
               allow_overwrite = True

            else:
               self.error ( skip_message + "broken symlink.\n" )

         elif os.path.isfile ( link ):
            if self.hook_overwrite_control.overwrite_all():
               self.error ( ov_message + "file.\n" )
               allow_overwrite = True
            else:
               self.error ( skip_message + "file.\n" )

         else:
            self.error ( skip_message + "not a file!\n" )

         # -- end if

         return allow_overwrite
      else:
         return True
   # --- end of check_link_allowed (...) ---

   def link_hooks_v ( self, event_name, hooks ):
      """Links several hooks to the given event.

      Returns True on success, else False.

      arguments:
      * event_name --
      * hooks      --
      """
      success = False

      user_hooks = self.user_hooks

      if user_hooks is not None and user_hooks.writable:

         self.setup_env.fs_private.dodir (
            user_hooks.get_fspath ( event_name )
         )

         # note that there is a race condition when users manipulate their
         # hook dir while running roverlay-setup
         to_link = []
         for script in hooks:
            user_script = user_hooks.get_entry_for_link ( script, event_name )

            if self.check_link_allowed (
               script.fspath, user_script.fspath, user_script.get_dest_name()
            ):
               to_link.append ( ( script, user_script ) )
         # -- end for

         register_link  = user_hooks.add_entry_unsafe
         symlink        = self.setup_env.fs_private.symlink
         unlink         = self.setup_env.fs_private.unlink
         relative_links = self.setup_env.options ['hook_relpath']
         success        = True

         for script, user_script in to_link:
            link = user_script.fspath
            unlink ( link )
            if relative_links:
               have_link = symlink (
                  os.path.relpath (
                     script.fspath, os.path.dirname ( link )
                  ), link
               )
            else:
               have_link = symlink ( script.fspath, link )

            if have_link:
               register_link ( user_script )
            elif have_link is not None:
               success = False
      # -- end if

      return success
   # --- end of link_hooks_v (...) ---

   def link_hooks_to_events ( self, hooks, events ):
      """Links several hooks to several events.

      Returns True on success, else False.

      arguments:
      * hooks  --
      * events --
      """
      success = True
      for event_name in events:
         if not self.link_hooks_v ( event_name, hooks ):
            success = False
      return success
   # --- end of link_hooks_to_events (...) ---

   def unlink_hooks ( self, hooks, symlinks_only=True ):
      """Removes several hooks.

      Returns: None (implicit)

      arguments:
      * hooks         -- iterable of UserHookScripts
      * symlinks_only -- if True: remove symlinks only, else remove files
                                  else well. Defaults to True.
      """
      unlink = self.setup_env.fs_private.unlink

      if not symlinks_only:
         for hook in hooks:
            fspath = hook.fspath
            if os.path.isdir ( fspath ):
               self.error (
                  "skipping {!r} - is a directory.\n".format ( fspath )
               )
            else:
               unlink ( fspath )
      else:
         for hook in hooks:
            fspath = hook.fspath
            if os.path.islink ( fspath ):
               unlink ( fspath )
            else:
               self.error (
                  "skipping {!r} - not a symlink.\n".format ( fspath )
               )
   # --- end of unlink_hooks (...) ---

   def enable_defaults ( self ):
      """Enables all default hooks."""
      # not strict: missing hooks are ignored
      success = False
      if self.hook_root:
         success = True
         default_hooks = self.hook_root.get_default_scripts()
         for event, hooks in default_hooks.items():
            if not self.link_hooks_v ( event, hooks ):
               success = False
      # -- end if

      return success
   # --- end of enable_defaults (...) ---

   def run ( self ):
      """main() function that gets its information from the setup env.

      Supports show and add/del <hook> <event>...
      """
      setup_env   = self.setup_env
      options     = setup_env.options
      command     = options ['hook.action']
      hook_name   = options ['hook.name']
      hook_events = options ['hook.events']

      if command in { 'show', }:
         self.info ( '\n'.join ( self.gen_hook_info_lines() ) )
         # -- end <show>

      elif command in { 'add', }:
         hooks = list ( self.hook_root.find_all_by_name_begin ( hook_name ) )
         if not hooks:
            self.error (
               "no hooks found matching {!r}\n".format ( hook_name )
            )
            # FIXME: exit code?

         elif "all" in hooks:
            self.error (
               "cannot add hooks to the (virtual) \'all\' event!\n"
            )

         elif len ( hooks ) == 1:
            # exactly one hook matches
            self.link_hooks_to_events ( hooks, hook_events )

         else:
            # > 1 matches, find exact matches
            exact_matches = [ k for k in hooks if k.name == hook_name ]

            if not exact_matches or len ( exact_matches ) != 1:
               self.error (
                  "ambiguous hook name: {!r} could match {}\n".format (
                     hook_name, ', '.join ( hook.name for hook in hooks )
                  )
               )
            else:
               self.link_hooks_to_events ( exact_matches, hook_events )

         # -- end <add>

      elif command in { 'del', }:
         hooks_to_unlink = []

         if hook_events and not "all" in hook_events:
            for event in hook_events:
               hooks = list (
                  self.user_hooks.find_all_by_name_begin (
                     hook_name, event=event
                  )
               )
               if not hooks:
                  self.error (
                     "no hooks found for event {!r} matching {!r}\n".format (
                        event, hook_name
                     )
                  )

               elif len ( hooks ) == 1:
                  hooks_to_unlink.append ( hooks[0] )

               else:
                  exact_matches = [ k for k in hooks if k.name == hook_name ]

                  if not exact_matches or len ( exact_matches ) != 1:
                     self.error (
                        'ambiguous hook name {!r} for event {!r}: '
                        'could match {}\n'.format (
                           hook_name, event,
                           ', '.join ( hook.name for hook in hooks )
                        )
                     )
                  else:
                     hooks_to_unlink.append ( exact_matches[0] )
            # -- end for
         else:
            hooks = list (
               self.user_hooks.find_all_by_name_begin (
                  hook_name, event=None
               )
            )

            if not hooks:
               self.error (
                  "no hooks found matching {!r}\n".format ( hook_name )
               )
            elif len ( hooks ) == 1:
               #hooks_to_unlink = hooks
               hooks_to_unlink.append ( hooks[0] )
            else:
               # COULDFIX: it would be better to check if the hooks'
               #           realpaths (link dest) are identical
               exact_matches = [ k for k in hooks if k.name == hook_name ]
               num_event_matches = (
                  collections.Counter ( k.event for k in exact_matches )
               )
               if exact_matches and all (
                  k < 2 for k in num_event_matches.values()
               ):
                  #hooks_to_unlink = exact_matches
                  hooks_to_unlink.extend ( exact_matches )
               else:
                  self.error (
                     'ambiguous hook name {!r}: could match {}\n'.format (
                        hook_name,
                        ', '.join ( set ( k.name for k in hooks ) )
                     )
                  )
         # -- end if

         self.unlink_hooks ( hooks_to_unlink )
         # -- end <del>

      else:
         raise NotImplementedError ( command )
   # --- end of run (...) ---

# --- end of SetupHookEnvironment ---
