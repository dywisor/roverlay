# R overlay -- create status reports based on templates
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# --- TODO/FIXME ---
# * what happens if the database has UNKNOWNS?
# * RRA creation doesn't seem to be correct
#

from __future__ import print_function

import os
import sys
import cgi
import cgitb
import weakref


# using mako
import mako.exceptions
import mako.lookup
import mako.template


import roverlay.argparser
import roverlay.runtime
import roverlay.tools.shenv
import roverlay.db.rrdtool
import roverlay.util.common
import roverlay.stats.rating

# temporary import
import roverlay.db.rrdgraph


class DBStats ( roverlay.stats.rating.RoverlayNumStatsRating ):

   def __init__ ( self, db_cache, description=None ):
      super ( DBStats, self ).__init__ (
         db_cache['values'], description=description
      )
      self.lastupdate = db_cache['lastupdate']
      self.suggestions = None
   # --- end of __init__ (...) ---

   def make_suggestions ( self, pure_text=False ):
      self.suggestions = list ( self.get_suggestions ( pure_text=pure_text ) )
      return bool ( self.suggestions )
   # --- end of __init__ (...) ---

# --- end of DBStats ---




class ReferenceableDict ( dict ):
   def ref ( self ):
      return weakref.ref ( self )
   # --- end of ref (...) ---

   def sorted_items ( self, keysort=None ):
      if keysort is None:
         return sorted ( self.items(), key=lambda kv: kv[0] )
      else:
         return sorted ( self.items(), key=lambda kv: keysort ( kv[0] ) )
   # --- end of sorted_items (...) ---

   def sorted_env_vars ( self, keysort=None ):
      # return list with "scalar" types only
      return list (
         kv for kv in self.sorted_items ( keysort=keysort )
            if isinstance ( kv[1], ( str, int, float ) )
      )
   # --- end of sorted_env_vars (...) ---

# --- end of ReferenceableDict ---

class SelfReferencingDict ( ReferenceableDict ):
   SELFREF_KEY = 'dictref'

##   def __setitem__ ( self, key, *args, **kw ):
##      if key == self.__class__.SELFREF_KEY:
##         raise AttributeError (
##            "{!r} is readonly.".format ( self.__class__.SELFREF_KEY )
##         )
##      else:
##         return super ( SelfReferencingDict, self ).__setitem__ (
##            key, *args, **kw
##         )
##   # --- end of __setitem__ (...) ---

   def __init__ ( self, *args, **kwargs ):
      super ( SelfReferencingDict, self ).__init__ ( *args, **kwargs )
      self [self.__class__.SELFREF_KEY] = self.ref()
      # or use __getitem__
   # --- end of __init__ (...) ---

# --- end of SelfReferencingDict ---


class StatusRuntimeEnvironment ( roverlay.runtime.RuntimeEnvironmentBase ):
   ARG_PARSER_CLS = roverlay.argparser.RoverlayStatusArgumentParser

   TEMPLATE_ENCODING = 'utf-8'

   SCRIPT_MODE_FILE_EXT = {
      'cli' : '.txt',
      'cgi' : '.html',
      'html': '.html',
   }

   # variables from /etc/nginx/fastcgi.conf
   #  (will be kept in template env dict depending on script mode)
   #
   #  sed -nr -e 's,^fastcgi_param\s+(\S+)\s+.*$,"\1"\,,p' \
   #     /etc/nginx/fastcgi.conf | sort
   #
   NGINX_CGI_VARS = frozenset ({
      "CONTENT_LENGTH",
      "CONTENT_TYPE",
      "DOCUMENT_ROOT",
      "DOCUMENT_URI",
      "GATEWAY_INTERFACE",
      "HTTPS",
      "QUERY_STRING",
      "REDIRECT_STATUS",
      "REMOTE_ADDR",
      "REMOTE_PORT",
      "REQUEST_METHOD",
      "REQUEST_URI",
      "SCRIPT_FILENAME",
      "SCRIPT_NAME",
      "SERVER_ADDR",
      "SERVER_NAME",
      "SERVER_PORT",
      "SERVER_PROTOCOL",
      "SERVER_SOFTWARE",
   })

   # common cgi vars as listed in
   #  /usr/lib/python3.2/cgi.py
   #
   COMMON_CGI_VARS = frozenset ({
      "AUTH_TYPE",
      "CONTENT_LENGTH",
      "CONTENT_TYPE",
      "DATE_GMT",
      "DATE_LOCAL",
      "DOCUMENT_NAME",
      "DOCUMENT_ROOT",
      "DOCUMENT_URI",
      "GATEWAY_INTERFACE",
      "LAST_MODIFIED",
      #"PATH",
      "PATH_INFO",
      "PATH_TRANSLATED",
      "QUERY_STRING",
      "REMOTE_ADDR",
      "REMOTE_HOST",
      "REMOTE_IDENT",
      "REMOTE_USER",
      "REQUEST_METHOD",
      "SCRIPT_NAME",
      "SERVER_NAME",
      "SERVER_PORT",
      "SERVER_PROTOCOL",
      "SERVER_ROOT",
      "SERVER_SOFTWARE",
      "HTTP_ACCEPT",
      "HTTP_CONNECTION",
      "HTTP_HOST",
      "HTTP_PRAGMA",
      "HTTP_REFERER",
      "HTTP_USER_AGENT",
   })


   def do_setup_mako ( self ):
      template_dirs = []
      self.default_template = 'status'

      if 'template' in self.options:
         # not ideal, but should suffice
         #  otherwise, introduce a --template-name arg
         #
         fspath = os.path.abspath (
            self.options ['template'].rstrip ( os.sep )
         )
         if os.path.isfile ( fspath ):
            dirname, basename = os.path.split ( fspath )
            assert dirname and basename
            template_dirs.append ( dirname )
            self.default_template = basename
         else:
            self.default_template = self.options ['template']
      # -- end if

      if self.installed:
         template_dirs.append (
            self.config.get_or_fail ( 'INSTALLINFO.libexec' )
         )

      extra_dirs = self.config.get ( 'STATS.TEMPLATE.root' )
      if extra_dirs:
         template_dirs.extend ( extra_dirs )

      if not template_dirs:
         raise Exception ( "no template directories found!" )


      module_dir = self.config.get ( 'STATS.TEMPLATE.module_dir', None )
      if module_dir is None:
         module_dir = self.config.get ( 'CACHEDIR.root', None )
         if module_dir:
            module_dir += os.sep + 'mako_templates'

      # use per-version module dirs
      #  modules generated with python2.7 are not compatible with python3.2
      if module_dir:
         module_dir += ( os.sep +
            'python_' + '.'.join ( map ( str, sys.version_info[:2] ) )
         )
         # 'python_' + hex ( sys.hexversion>>16 )


      self._mako_lookup = mako.lookup.TemplateLookup (
         directories=template_dirs, module_directory=module_dir,
         output_encoding=self.TEMPLATE_ENCODING,
      )
   # --- end of do_setup_mako (...) ---

   def do_setup ( self ):
      self.do_setup_parser()
      script_mode = self.options ['script_mode']
      assert script_mode and script_mode.islower()
      if script_mode == 'cgi':
         cgitb.enable()

      self.do_setup_config()
      self.template_vars = SelfReferencingDict (
         roverlay.tools.shenv.setup_env()
      )
      roverlay.tools.shenv.restore_msg_vars ( self.template_vars )
      #self.template_vars ['ROVERLAY_PHASE'] = 'status_' + self.command
      self.template_vars ['ROVERLAY_PHASE'] = 'status'

      try:
         del self.template_vars ['STATS_DB']
      except KeyError:
         pass

      self.script_mode = script_mode
      self.outfile     = self.options ['outfile']
      if self.outfile == '-':
         self.outfile = None

      self.template_vars ['EXE']         = sys.argv[0]
      self.template_vars ['EXE_NAME']    = os.path.basename ( sys.argv[0] )
      self.template_vars ['SCRIPT_MODE'] = script_mode



      if script_mode == 'cgi':
         # inherit cgi-related vars from os.environ
         self.set_template_vars (
            roverlay.util.common.keepenv_v (
               self.NGINX_CGI_VARS|self.COMMON_CGI_VARS
            ),
            CGI_FORM=cgi.FieldStorage( keep_blank_values=0 ),
         )
         # TODO (maybe):
         #  set default_template depending on CGI_FORM
         #
      # -- end if


      self.stats_db      = None
      self.graph_factory = None
      stats_db_file      = self.config.get ( 'RRD_DB.file', None )

      if stats_db_file:
         self.stats_db = roverlay.db.rrdtool.RRD (
            stats_db_file, readonly=True
         )
         self.stats_db.make_cache()
         self.graph_factory = roverlay.db.rrdgraph.RRDGraphFactory (
            rrd_db=self.stats_db,
        )


         # transfer db cache to template_vars
         # * copy lastupdate
         # * import values
         #
         self.set_template_vars (
            self.stats_db.cache ['values'],
            lastupdate=self.stats_db.cache ['lastupdate'],
            STATS_DB_FILE=stats_db_file,
            STATS_DB=DBStats ( self.stats_db.cache ),
         )

      # -- end if

      self.do_setup_mako()
   # --- end of do_setup (...) ---

   def get_template ( self,
      template_name,
      file_extensions=[ '', ],
      add_mode_ext=True
   ):
      my_template = None

      if add_mode_ext:
         fext_list = (
            [ self.get_script_mode_file_ext() ] + list ( file_extensions )
         )
      else:
         fext_list = file_extensions

      # TODO/FIXME: does TemplateLookup support file extension_s_ lookup?
      last_fext_index = len ( fext_list ) - 1
      for index, f_ext in enumerate ( fext_list ):
         if index == last_fext_index:
            my_template = self._mako_lookup.get_template (
               template_name + f_ext
            )
         else:
            try:
               my_template = self._mako_lookup.get_template (
                  template_name + f_ext
               )
            except mako.exceptions.TopLevelLookupException:
               pass
            else:
               break
         # -- end if

      return my_template
   # --- end of get_template (...) ---

   def serve_template ( self,
      template_name=None, catch_exceptions=True, lookup_kwargs={}
   ):
      try:
         my_template = self.get_template (
            template_name=(
               template_name if template_name is not None
               else self.default_template
            ),
            **lookup_kwargs
         )
         ret = my_template.render ( **self.template_vars )
      except:
         if catch_exceptions:
            if self.script_mode in { 'cgi', 'html' }:
               ret = mako.exceptions.html_error_template().render()
            else:
               ret = mako.exceptions.text_error_template().render()
         else:
            raise
      # -- end if
      return ret
   # --- end of serve_template (...) ---

   def set_template_vars ( self, *args, **kwargs ):
      for kw in args:
         self.template_vars.update ( kw )
      self.template_vars.update ( kwargs )
   # --- end of setup_vars (...) ---

   def write_cgi_header ( self, stream, encode=False, force=False ):
      if force or self.script_mode == 'cgi':
         content_type = self.options ['cgi_content_type']
         if content_type:
            header = "Content-Type: {}\n\n".format ( content_type )
            if encode:
               stream.write ( header.encode ( self.TEMPLATE_ENCODING ) )
            else:
               stream.write ( header )
            return True
      return False
   # --- end of write_cgi_header (...) ---

   @classmethod
   def encode ( cls, text ):
      return str ( text ).encode ( cls.TEMPLATE_ENCODING )
   # --- end of encode (...) ---

   @classmethod
   def decode ( cls, data, force=False ):
      if force or not isinstance ( data, str ):
         return data.decode ( cls.TEMPLATE_ENCODING )
      else:
         return str ( data )
   # --- end of decode (...) ---

   def get_script_mode_file_ext ( self ):
      return self.SCRIPT_MODE_FILE_EXT.get (
         self.script_mode, ( '.' + self.script_mode )
      )
   # --- end of get_script_mode_file_ext (...) ---

# --- end of StatusRuntimeEnvironment ---

def graph_example ( main_env, dump_file="/tmp/roverlay_graph.png" ):
   """graph creation - work in progress"""

   graph = main_env.graph_factory.get_new()
   graph.title = "R_Overlay"
   graph.colors = [
      # colors from munin (Munin::Master::GraphOld[.pm])
      'BACK#F0F0F0',   # Area around the graph
      'FRAME#F0F0F0',  # Line around legend spot
      'CANVAS#FFFFFF', # Graph background, max contrast
      'FONT#666666',   # Some kind of gray
      'AXIS#CFD6F8',   # And axis like html boxes
      'ARROW#CFD6F8',  # And arrow, ditto.
   ]

   graph.end   = "now"
   graph.start = "end-" + str ( graph.SECONDS_DAY//4 ) + "s"
   graph.extra_options.extend ((
      '--width', '400', '--border', '0',
      '--font', 'DEFAULT:0:DejaVuSans,DejaVu Sans,DejaVu LGC Sans,Bitstream Vera Sans',
      '--font', 'LEGEND:7:DejaVuSansMono,DejaVu Sans Mono,DejaVu LGC Sans Mono,Bitstream Vera Sans Mono,monospace',

   ))

   graph.add_def  ( "pkg_success", "pc_success", "MAX" )
   graph.add_def  ( "pkg_fail",  "pc_fail", "MAX" )

   graph.add_vdef ( "pkg_success_max", "pkg_success,MAXIMUM" )
   graph.add_vdef ( "pkg_success_min", "pkg_success,MINIMUM" )
   graph.add_vdef ( "pkg_fail_max",  "pkg_fail,MAXIMUM" )
   graph.add_vdef ( "pkg_fail_min",  "pkg_fail,MINIMUM" )

   graph.add_arg ( "COMMENT:            " )
   graph.add_arg ( "COMMENT:     min " )
   graph.add_arg ( "COMMENT:     max\l" )

   graph.add_line ( "pkg_success", "blue", width=1, legend="pkg success" )
   graph.add_print ( "pkg_success_min", "%7.0lf %S", inline=True )
   graph.add_print ( "pkg_success_max", "%7.0lf %S\l", inline=True )



   #graph.add_line ( "pkg_fail", "red",  width=1, legend="pkg fail   " )
   graph.add_area ( "pkg_fail", "red", legend="pkg fail   " )
   graph.add_print ( "pkg_fail_min", "%7.0lf %S", inline=True )
   graph.add_print ( "pkg_fail_max", "%7.0lf %S\l", inline=True )

   graph.make()

   image = graph.get_image()
   if image:
      with open ( dump_file, 'wb' ) as FH:
         FH.write ( graph.get_image() )

# --- end of graph_example (...) ---

def main_installed ( *args, **kwargs ):
   return main ( True, *args, **kwargs )
# --- end of main_installed (...) ---

def main ( installed, *args, **kw ):

   main_env = StatusRuntimeEnvironment ( installed, *args, **kw )
   main_env.setup()

   #graph_example ( main_env )

   output_encoded = main_env.serve_template()

   if main_env.outfile:
      with open (
         main_env.outfile,
         'w' + ( 'b' if not isinstance ( output, str ) else 't' )
      ) as FH:
         # COULDFIX: write cgi header to file?
         #main_env.write_cgi_header ( FH, encode=True )
         FH.write ( output_encoded )
   else:
      output = main_env.decode ( output_encoded ).lstrip ( '\n' )
      main_env.write_cgi_header ( sys.stdout )
      sys.stdout.write ( output )
# --- end of main (...) ---
