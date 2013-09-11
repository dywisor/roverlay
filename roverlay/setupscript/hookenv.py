# R overlay -- setup script, env for managing hooks
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import errno
import os


import roverlay.static.hookinfo
import roverlay.util.counter


class HookScript ( object ):

   def __init__ ( self, fspath, filename=None ):
      super ( HookScript, self ).__init__()
      fname = (
         filename if filename is not None else os.path.basename ( fspath )
      )

      self.fspath  = fspath
      self.name    = os.path.splitext ( fname )[0] or fname
      static_entry = roverlay.static.hookinfo.get ( self.name, None )

      if static_entry is not None:
         self.default_events = static_entry[0]
         self.priority       = static_entry[1]
         self.is_hidden      = static_entry[2]
      else:
         self.default_events = False
         self.priority       = None
         self.is_hidden      = False
   # --- end of __init__ (...) ---

   def is_visible ( self ):
      return not self.is_hidden and (
         self.priority is None or self.priority >= 0
      )
   # --- end of is_visible (...) ---

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


# --- end of HookScript ---


class HookScriptDir ( object ):

   def __init__ ( self, root ):
      super ( HookScriptDir, self ).__init__()

      self.root      = root
      self._scripts  = collections.OrderedDict()
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      return bool ( self._scripts )
   # --- end of __bool__ (...) ---

   def get_script ( self, name ):
      script = self._scripts [name]
      return script if script.is_visible() else None
   # --- end of get_scripts (...) ---

   def iter_default_scripts ( self, unpack=False ):
      if unpack:
         for script in self._scripts.values():
            if script.default_events:
               for event in script.default_events:
                  yield ( event, script )
      else:
         for script in self._scripts.values():
            if script.default_events:
               yield script
   # --- end of iter_default_scripts (...) ---

   def get_default_scripts ( self ):
      scripts = dict()
      for event, script in self.iter_default_scripts ( unpack=True ):
         if event not in scripts:
            scripts [event] = [ script ]
         else:
            scripts [event].append ( script )

      return scripts
   # --- end of get_default_scripts (...) ---

   def iter_scripts ( self ):
      for script in self._scripts.values():
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
         for fname in filenames:
            fspath = root + os.sep + fname
            if os.path.isfile ( fspath ):
               script_obj = HookScript ( fspath, fname )
               self._scripts [script_obj.name] = script_obj
   # --- end of scan (...) ---

# --- end of HookScriptDir ---


class SetupHookEnvironment (
   roverlay.setupscript.baseenv.SetupSubEnvironment
):

   NEEDS_CONFIG_TREE = True

   def setup ( self ):
      additions_dir = self.config.get ( 'OVERLAY.additions_dir', None )
      if additions_dir:
         self.user_hook_root = os.path.join ( additions_dir, 'hooks' )
         self.writable       = self.setup_env.private_file.check_writable (
            self.user_hook_root + os.sep + '.keep'
         )
      else:
         self.user_hook_root = None
         self.writable       = None

      self.hook_root = HookScriptDir (
         os.path.join ( self.setup_env.data_root, 'hooks' )
      )
      self.hook_root.scan()
      self._prio_gen = roverlay.util.counter.UnsafeCounter ( 30 )
   # --- end of setup (...) ---

   def _link_hook ( self, source, link ):
      if os.path.lexists ( link ):
         linkdest = os.path.realpath ( link )

         message = 'Skipping activation of hook {!r} - '.format ( link )

         if linkdest == source or linkdest == os.path.realpath ( source ):
            self.info ( message + "already set up.\n" )
            return True

         elif link != linkdest:
            # symlink or link was relative
            self.error ( message + "is a link to another file.\n" )
         else:
            self.error ( message + "exists, but is not a link.\n" )

         return None
      else:
         return self.setup_env.private_file.symlink ( source, link )
   # --- end of _link_hook (...) ---

   def link_hooks_v ( self, event_name, hooks ):
      success = False

      if self.writable and self.user_hook_root:
         destdir = self.user_hook_root + os.sep + event_name
         self.setup_env.private_dir.dodir ( destdir )

         to_link = []
         for script in hooks:
            script.set_priority_from_generator ( self._prio_gen )
            to_link.append (
               ( script.fspath, destdir + os.sep + script.get_dest_name() )
            )

         success = True
         for source, link_name in to_link:
            if self._link_hook ( source, link_name ) is False:
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

# --- end of SetupHookEnvironment ---
