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
      return cls ( cls.OV_KEYWORDS[vstr] )
   # --- end of from_str (...) ---

   def __init__ ( self, value ):
      super ( HookOverwriteControl, self ).__init__()
      assert isinstance ( value, int ) and value >= 0
      self.value = value
   # --- end of __init__ (...) ---

   def can_overwrite ( self, mask=None ):
      if mask is None:
         return self.value == self.OV_NONE
      else:
         return self.value & mask
   # --- end of can_overwrite (...) ---

   def overwrite_dead_symlinks ( self ):
      return self.value & self.OV_SYM_DEAD

   def overwrite_symlinks ( self ):
      return self.value & self.OV_SYM

   def overwrite_all ( self ):
      return self.value == self.OV_ALL

   def get_str ( self ):
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

   CACHE_REF = True

   def __init__ ( self,
      fspath, filename=None, priority=None, is_hidden=False
   ):
      """HookScriptBase constructor.

      arguments:
      * fspath    -- absolute path to the hook script
      * filename  -- name of the hook script
                      Defaults to os.path.basename(fspath).
      * priority  -- priority of the hook script. Defaults to auto-detect.
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
         cls=self.__class__.__name__,
         name=self.name,
         h=yesno ( self.is_hidden ),
         p=(
            "auto" if self.priority is None else
               ( "IGNORE" if self.priority < 0 else self.priority )
         ),
      )
   # --- end of __str__ (...) ---

   def get_static_info ( self ):
      return roverlay.static.hookinfo.get ( self.name, None )
   # --- end of get_static_info (...) ---

   def is_visible ( self ):
      return not self.is_hidden and (
         self.priority is None or self.priority >= 0
      )
   # --- end of is_visible (...) ---

   @roverlay.util.objects.abstractmethod
   def get_hookscript ( self ):
      pass
   # --- end of get_hookscript (...) ---

   @roverlay.util.objects.abstractmethod
   def get_hookscript_path ( self ):
      pass
   # --- end of get_hookscript_path (...) ---

   @roverlay.util.objects.abstractmethod
   def get_dest_name ( self, *args, **kwargs ):
      pass
   # --- end of get_dest_name (...) ---

# --- end of HookScriptBase ---


class UserHookScript ( HookScriptBase ):

   def __init__ ( self, fspath, filename=None, event=None ):
      super ( UserHookScript, self ).__init__ (
         fspath, filename=filename, priority=True
      )

      self.hook_script_fspath = os.path.realpath ( self.fspath )
      if (
         os.path.islink ( self.fspath ) or not os.path.lexists ( self.fspath )
      ):
         self.hook_script_ref = None
      else:
         self.hook_script_ref = False


      self.event = event
   # --- end of __init__ (...) ---

   def set_hookscript ( self, script_obj, strict=True ):
      if script_obj and self.hook_script_ref is False:
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
      return self.hook_script_ref is not None
   # --- end of has_hookscript (...) ---

   def get_hookscript ( self ):
      ref = self.hook_script_ref
      if ref is False:
         return None
      elif ref is None:
         raise roverlay.util.objects.ObjectDisappeared()
      else:
         return ref.deref_safe()
   # --- end of get_hookscript (...) ---

   def get_hookscript_path ( self ):
      return self.hook_script_fspath
   # --- end of get_hookscript_path (...) ---

   def get_dest_name ( self ):
      return self.filename
   # --- end of get_dest_name (...) ---

# --- end of UserHookScript ---


class HookScript ( HookScriptBase ):

   def __init__ ( self, fspath, filename=None ):
      super ( HookScript, self ).__init__ ( fspath, filename=filename )

      static_entry = self.get_static_info()
      if static_entry is not None:
         self.default_events = static_entry[0]
         self.priority       = static_entry[1]
         self.is_hidden      = static_entry[2]
      else:
         self.default_events = False

      self.user_script_refs = set()
   # --- end of __init__ (...) ---

   def add_user_script ( self, user_script ):
      self.user_script_refs.add ( user_script.get_ref() )
   # --- end of add_user_script (...) ---

   def iter_user_scripts ( self, ignore_missing=True ):
      if ignore_missing:
         for ref in self.user_script_refs:
            obj = ref.deref_unsafe()
            if obj is not None:
               yield obj
      else:
         for ref in self.user_script_refs:
            yield obj.deref_safe()
   # --- end of iter_user_scripts (...) ---

   def set_priority_from_generator ( self, number_gen, only_if_unset=True ):
      if self.priority is None:
         self.priority = next ( number_gen )
         return True
      elif only_if_unset or self.priority < 0:
         return False
      else:
         self.priority = next ( number_gen )
         return True
   # --- end of set_priority_from_generator (...) ---

   def get_dest_name ( self, file_ext='.sh', digit_len=2 ):
      # file_ext has to be .sh, else the script doesn't get recognized
      # by mux.sh

      prio = self.priority
      if prio is None or prio < 0:
         raise AssertionError ( "hook script has no priority." )

      return "{prio:0>{l}d}-{fname}{f_ext}".format (
         prio=prio, fname=self.name, f_ext=file_ext, l=digit_len,
      )
   # --- end of get_dest_name (...) ---

   def get_hookscript ( self ):
      return self
   # --- end of get_hookscript (...) ---

   def get_hookscript_path ( self ):
      return self.fspath
   # --- end of get_hookscript_path (...) ---

# --- end of HookScript ---


class HookScriptDirBase ( roverlay.util.objects.Referenceable ):

   HOOK_SCRIPT_CLS = None

   def __init__ ( self, root ):
      super ( HookScriptDirBase, self ).__init__()

      self.root     = root
      self.scripts  = collections.OrderedDict()
      self.writable = None
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      return bool ( self.scripts )
   # --- end of __bool__ (...) ---

   def get_fspath ( self, relpath=None ):
      if relpath:
         return self.root + os.sep + str ( relpath )
      else:
         return self.root
   # --- end of get_fspath (...) ---

   def get_script ( self, name ):
      script = self.scripts [name]
      return script if script.is_visible() else None
   # --- end of get_scripts (...) ---

   def iter_scripts ( self ):
      for script in self.scripts.values():
         if script.is_visible():
            yield script
   # --- end of iter_scripts (...) ---

   def scan ( self ):
      root = self.root
      try:
         filenames = sorted ( os.listdir ( root ) )
      except OSError as oserr:
         if oserr.errno != errno.ENOENT:
            raise
      else:
         HOOK_CLS = self.HOOK_SCRIPT_CLS
         for fname in filenames:
            fspath = root + os.sep + fname
            if os.path.isfile ( fspath ):
               script_obj = HOOK_CLS ( fspath, filename=fname )
               self.scripts [script_obj.name] = script_obj
   # --- end of scan (...) ---

# --- end of HookScriptDirBase ---


class NestedHookScriptDirBase ( HookScriptDirBase ):
   SUBDIR_CLS       = collections.OrderedDict
   DIRNAMES_IGNORE  = frozenset({ '.*', })
   FILENAMES_IGNORE = frozenset({ '.*', })

   def dirname_filter ( self, dirname, _fnmatch=fnmatch.fnmatch ):
      for pattern in self.DIRNAMES_IGNORE:
         if _fnmatch ( dirname, pattern ):
            return False
      return True
   # --- end of dirname_filter (...) ---

   def get_script ( self, name ):
      return [
         script for script in self.iter_scripts() if script.name == name
      ]
   # --- end of get_script (...) ---

   def filename_filter ( self, filename, _fnmatch=fnmatch.fnmatch ):
      for pattern in self.FILENAMES_IGNORE:
         if _fnmatch ( filename, pattern ):
            return False
      return True
   # --- end of filename_filter (...) ---

   def create_hookscript ( self, fspath, filename, root ):
      return self.HOOK_SCRIPT_CLS ( fspath, filename=filename )
   # --- end of create_hookscript (...) ---

   def scan ( self, prune_empty=True ):
      SUBDIR_CLS = self.SUBDIR_CLS

      self.scripts = roverlay.fsutil.get_fs_dict (
         self.root, create_item=self.create_hookscript,
         dict_cls=self.SUBDIR_CLS, dirname_filter=self.dirname_filter,
         filename_filter=self.filename_filter, include_root=False,
         prune_empty=True,
      )

      for event, hook in self.iter_scripts():
         if hook.event is None:
            hook.event = event
   # --- end of scan (...) ---

   def iter_scripts ( self ):
      # roverlay uses per-event subdirs containing hook files
      SUBDIR_CLS = self.SUBDIR_CLS
      for event, subdir in self.scripts.items():
         if isinstance ( subdir, SUBDIR_CLS ):
            for hook in subdir.values():
               if isinstance ( hook, HookScriptBase ) and hook.is_visible():
               #if not isinstance ( hook, SUBDIR_CLS ):
                  yield ( event, hook )
   # --- end of iter_scripts (...) ---

# --- end of NestedHookScriptDirBase ---


class UserHookScriptDir ( NestedHookScriptDirBase ):

   HOOK_SCRIPT_CLS = UserHookScript

   def create_hookdir_refs ( self,
      hook_dir, overwrite=False, compare_fspath=True
   ):
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
      # try exact fs path matches first, then use name-based ones
      self.create_hookdir_refs ( hook_dir, compare_fspath=True )
      self.create_hookdir_refs ( hook_dir, compare_fspath=False )
   # --- end of make_hookdir_refs (...) ---

   def register_hook_link_unsafe ( self, event_name, hook, link, link_name ):
      subdir = self.scripts.get ( event_name, None )
      if subdir is None or link_name not in subdir:
         if subdir is None:
            subdir = self.SUBDIR_CLS()
            self.scripts [event_name] = subdir
         # -- end if

         entry = self.HOOK_SCRIPT_CLS ( link, filename=link_name )
         subdir [link_name] = entry
      else:
         entry = subdir [link_name]
      # -- end if

      entry.set_hookscript ( hook, strict=False )
      if entry.event is None:
         entry.event = event_name
      elif entry.event != event_name:
         raise AssertionError ( "entry.event != event_name" )
      return True
   # --- end of register_hook_link_unsafe (...) ---

   def iter_nonlinked ( self ):
      for event, script in self.iter_scripts():
         if not script.has_hookscript():
            yield script
   # --- end of iter_nonlinked (...) ---

# --- end of UserHookScriptDir ---


class HookScriptDir ( HookScriptDirBase ):

   HOOK_SCRIPT_CLS = HookScript

   def iter_linked ( self ):
      # 2-tuple ( hook_script, list ( linked_user_scripts ) )
      for script in self.iter_scripts():
         yield ( script, list ( script.iter_user_scripts() ) )
   # --- end of iter_linked (...) ---

   def iter_default_scripts ( self, unpack=False ):
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
      return roverlay.util.dictwalk.dictmerge (
         self.iter_default_scripts ( unpack=True ),
         get_value=lambda kv:kv[1]
      )
   # --- end of get_default_scripts (...) ---

# --- end of HookScriptDir ---



class SetupHookEnvironment (
   roverlay.setupscript.baseenv.SetupSubEnvironment
):

   NEEDS_CONFIG_TREE = True

   def format_hook_info_lines ( self,
      info, sort_info=True, append_newline=False
   ):
      max_name_len = min ( 30, max ( len(x[0]) for x in info ) )

      event_names  = set()
      for name, ev_prio in info:
         event_names.update ( item[0] for item in ev_prio )

      event_words = [
         ( ev, (4+len(ev)) * ' ' ) for ev in sorted ( event_names )
      ]

      if sort_info:
         my_info = sorted (
            info,
            key=lambda k: ( not k[1], k[0] )
         )
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
      return [
         ( s.name, [ ( s.event or "undef", s.priority ) ] )
         for event, s in self.user_hooks.iter_scripts()
      ]
   # --- end of get_user_hook_info (...) ---

   def gen_hook_info_lines ( self, append_newline=True ):
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
      self.hook_overwrite_control = self.setup_env.hook_overwrite

      additions_dir = self.config.get ( 'OVERLAY.additions_dir', None )

      self.hook_root = HookScriptDir (
         os.path.join ( self.setup_env.data_root, 'hooks' )
      )
      self.hook_root.scan()
      self._prio_gen = roverlay.util.counter.UnsafeCounter ( 30 )


      if additions_dir:
         self.user_hooks = UserHookScriptDir (
            os.path.join ( additions_dir, 'hooks' )
         )
         self.user_hooks.writable = (
            self.setup_env.private_file.check_writable (
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
      success = False

      if self.user_hooks is not None and self.user_hooks.writable:

         destdir = self.user_hooks.get_fspath ( event_name )
         self.setup_env.private_dir.dodir ( destdir )

         # note that there is a race condition when users manipulate their
         # hook dir while running roverlay-setup
         to_link = []
         for script in hooks:
            script.set_priority_from_generator ( self._prio_gen )
            dest_name = script.get_dest_name()
            link = destdir + os.sep + dest_name

            if self.check_link_allowed ( script.fspath, link, dest_name ):
               to_link.append ( ( script, dest_name, link ) )
         # -- end for

         register_link = self.user_hooks.register_hook_link_unsafe
         symlink       = self.setup_env.private_file.symlink
         success       = True

         for script, dest_name, link in to_link:
            have_link = symlink ( script.fspath, link )
            if have_link:
               register_link ( event_name, script, link, dest_name )
            elif have_link is not None:
               success = False
      # -- end if

      return success
   # --- end of link_hooks_v (...) ---

   def enable_defaults ( self ):
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
      # TODO
      self.info ( '\n'.join ( self.gen_hook_info_lines() ) )
   # --- end of run (...) ---

# --- end of SetupHookEnvironment ---
