# R overlay -- stats collection, rrdtool graph creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import sys
import time

import roverlay.util.objects


# a few colors for drawing graphs (as str)
#  RRGGBB[AA], rgb+alpha
COLORS = {
   'white'    : 'ffffff',
   'silver'   : 'c0c0c0',
   'gray'     : '808080',
   'grey'     : '808080',
   'black'    : '000000',
   'red'      : 'ff0000',
   'maroon'   : '800000',
   'yellow'   : 'ffff00',
   'olive'    : '808000',
   'lime'     : '00ff00',
   'green'    : '008000',
   'aqua'     : '00ffff',
   'teal'     : '008080',
   'blue'     : '0000ff',
   'navy'     : '000080',
   'fuchsia'  : 'ff00ff',
   'purple'   : '800080',
}


class RRDGraphArg ( object ):

   def gen_options ( self, options, no_key=False ):
      for attr_name in options:
         #attr = getattr ( self, attr_name, None )
         attr = getattr ( self, attr_name.lower().replace ( '-', '_' ) )
         if attr is not None:
            if no_key:
               yield ':' + str ( attr )
            elif attr is True:
               yield ':' + attr_name
            else:
               yield ':{k}={v}'.format ( k=attr_name, v=str ( attr ) )
   # --- end of gen_options (...) ---

   def get_options_str ( self, *options ):
      return ''.join ( self.gen_options ( options, no_key=False ) )
   # --- end of get_options_str (...) ---

   def get_options_str_nokey ( self, *options ):
      return ''.join ( self.gen_options ( options, no_key=True ) )
   # --- end of get_options_str_nokey (...) ---


   @roverlay.util.objects.abstractmethod
   def get_str ( self, rrd_db ):
      pass
   # --- end of get_str (...) ---

   def get_color_suffix ( self, color ):
      if color is None:
         return ''
      elif color in COLORS:
         return '#' + COLORS [color]
      else:
         return '#' + str ( color ).lstrip ( '#' )
   # --- end of get_color_suffix (...) ---

# --- end of RRDGraphArg ---

class RRDGraphArg_DEF ( RRDGraphArg ):

   def __init__ ( self,
      name, ds_name, cf, rrdfile=None, step=None, start=None, stop=None
   ):
      super ( RRDGraphArg_DEF, self ).__init__()
      self.name    = name
      self.rrdfile = rrdfile
      self.ds_name = ds_name
      self.cf      = cf
      self.step    = step
      self.start   = start
      self.stop    = stop
   # --- end of __init__ (...) ---

   def get_str ( self, rrd_db ):
      rrdfile = self.rrdfile if self.rrdfile is not None else rrd_db.filepath
      return (
         "DEF:{vname}={rrdfile}:{ds_name}:{cf}".format (
            vname=self.name, rrdfile=rrdfile, ds_name=self.ds_name, cf=self.cf
         )
         + self.get_options_str ( 'step', 'start', 'stop' )
      )
   # --- end of get_str (...) ---

# --- end of RRDGraphArg_DEF ---

class RRDGraphArg_CDEF ( RRDGraphArg ):

   DEFTYPE = 'CDEF'

   def __init__ ( self, name, rpn, expression=None ):
      super ( RRDGraphArg_CDEF, self ).__init__()
      self.name       = name
      self.rpn        = rpn
      self.expression = expression
   # --- end of __init__ (...) ---

   def get_str ( self, rrd_db ):
      if self.expression is None:
         return "{deftype}:{vname}={rpn}".format (
            deftype=self.__class__.DEFTYPE, vname=self.name, rpn=self.rpn
         )
      else:
         return "{deftype}:{vname}={rpn} {expr}".format (
            deftype=self.__class__.DEFTYPE,
            vname=self.name, rpn=self.rpn, expr=self.expression
         )
   # --- end of get_str (...) ---

# --- end of RRDGraphArg_CDEF ---

class RRDGraphArg_VDEF ( RRDGraphArg_CDEF ):
   DEFTYPE = 'VDEF'
# --- end of RRDGraphArg_VDEF ---

class RRDGraphArg_AREA ( RRDGraphArg ):

   def __init__ ( self,
      value, color=None, legend=None, stack=None, skipscale=None
   ):
      super ( RRDGraphArg_AREA, self ).__init__()
      self.value     = value
      self.color     = color
      self.legend    = legend
      self.stack     = stack
      self.skipscale = skipscale
   # --- end of __init__ (...) ---

   def get_str ( self, rrd_db ):
      return (
         "AREA:{value}{vcolor}".format (
            value=self.value, vcolor=self.get_color_suffix ( self.color )
         )
         + self.get_options_str_nokey ( 'legend' )
         + self.get_options_str ( 'STACK', 'skipscale' )
      )
   # --- end of get_str (...) ---

# --- end of RRDGraphArg_AREA ---

class RRDGraphArg_LINE ( RRDGraphArg ):

   def __init__ ( self,
      value, color=None, width=None, legend=None, stack=None, skipscale=None,
      dashes=None, dash_offset=None,
   ):
      super ( RRDGraphArg_LINE, self ).__init__()
      self.width       = width
      self.value       = value
      self.color       = color
      self.legend      = legend
      self.stack       = stack
      self.skipscale   = skipscale
      self.dashes      = dashes
      self.dash_offset = dash_offset
   # --- end of __init__ (...) ---

   def get_str ( self, rrd_db ):
      if self.width is not None:
         if isinstance ( self.width, str ):
            width = self.width
         else:
            width = str ( float ( self.width ) )
      else:
         width = ""

      width
      return (
         'LINE' + width + ':{value}{vcolor}'.format (
            value=self.value, vcolor=self.get_color_suffix ( self.color ),
         ) + self.get_options_str_nokey ( 'legend' )
         + self.get_options_str (
            'STACK', 'skipscale', 'dashes', 'dash-offset'
         )
      )
   # --- end of get_str (...) ---

# --- end of RRDGraphArg_AREA ---

class RRDGraphArg_PRINT ( RRDGraphArg ):

   ARG_TYPE = 'PRINT'

   def __init__ ( self, name, format_str=None ):
      super ( RRDGraphArg_PRINT, self ).__init__()
      self.name = name
      if format_str is None:
         self.format_str = '%.0lf %S'
      else:
         self.format_str = format_str
   # --- end of __init__ (...) ---

   def get_str ( self, rrd_db ):
      return self.ARG_TYPE + ':' + self.name + ':' + self.format_str
   # --- end of get_str (...) ---

# --- end of RRDGraphArg_PRINT ---

class RRDGraphArg_GPRINT ( RRDGraphArg_PRINT ):
   ARG_TYPE = 'GPRINT'
# --- end of RRDGraphArg_GPRINT ---


class RRDGraph ( object ):

   GRAPH_COMMAND  = 'graphv'

   SECONDS_MINUTE = 60
   SECONDS_HOUR   = SECONDS_MINUTE*60
   SECONDS_DAY    = SECONDS_HOUR*24
   SECONDS_WEEK   = SECONDS_DAY*7
   SECONDS_MONTH  = SECONDS_DAY*31
   SECONDS_YEAR   = SECONDS_DAY*365

   OPTIONS_ATTR = (
      'start', 'end', 'imgformat', 'title', 'vertical_label'
   )

   def __init__ ( self, rrd_db, **kwargs ):
      super ( RRDGraph, self ).__init__()
      self.image_data     = None
      self.rrd_db         = rrd_db
      self.extra_options  = list()
      self.args           = list()

      self.start          = None
      self.end            = None
      self.imgformat      = 'PNG'
      self.title          = None
      self.vertical_label = None
      self.colors         = []

      self.__dict__.update ( kwargs )
   # --- end of __init__ (...) ---

   def get_image ( self ):
      if self.image_data:
         return self.image_data ['image_data']
      else:
         return None
   # --- end of get_image (...) ---

   def get_timespan ( self, delta, stop=None, delta_factor=1.0 ):
      t_stop = time.time() - 1 if stop is None else stop
      return ( int ( t_stop - ( delta_factor * delta ) ), int ( t_stop ) )
   # --- end of get_timespan (...) ---

   def set_timespan ( self, delta, stop=None, delta_factor=SECONDS_DAY, recursive=False ):
      self.start, self.end = self.get_timespan (
         delta, stop=stop, delta_factor=delta_factor
      )
      if recursive:
         for arg in self.args:
            if isinstance ( arg, RRDGraphArg ):
               if hasattr ( arg, 'start' ):
                  arg.start = self.start
               if hasattr ( arg, 'stop' ):
                  arg.stop = self.end
   # --- end of set_timespan (...) ---

   def add_arg ( self, arg ):
      self.args.append ( arg )
      return arg
   # --- end of add_arg (...) ---

   def add_args ( self, *args ):
      self.args.extend ( args )
   # --- end of add_args (...) ---

   def add_def ( self, name, ds_name, cf, step=None ):
      return self.add_arg (
         RRDGraphArg_DEF (
            name=name, ds_name=ds_name, cf=cf, rrdfile=None, step=step,
         )
      )
   # --- end of add_def (...) ---

   def add_cdef ( self, name, rpn, expression=None ):
      return self.add_arg (
         RRDGraphArg_CDEF ( name=name, rpn=rpn, expression=expression )
      )
   # --- end of add_cdef (...) ---

   def add_vdef ( self, name, rpn, expression=None ):
      return self.add_arg (
         RRDGraphArg_VDEF ( name=name, rpn=rpn, expression=expression )
      )
   # --- end of add_vdef (...) ---

   def add_line (
      self, value, color, width=None, legend=None, extra_kwargs={}
   ):
      return self.add_arg (
         RRDGraphArg_LINE (
            value=value, color=color, width=width, legend=legend,
            **extra_kwargs
         )
      )
   # --- end of add_line (...) ---

   def add_area (
      self, value, color, legend=None, stack=None, skipscale=None
   ):
      return self.add_arg (
         RRDGraphArg_AREA (
            value=value, color=color, legend=legend,
            stack=stack, skipscale=skipscale
         )
      )
   # --- end of add_area (...) ---

   def add_print ( self, name, format_str=None, inline=False ):
      if inline:
         return self.add_arg ( RRDGraphArg_GPRINT ( name, format_str ) )
      else:
         return self.add_arg ( RRDGraphArg_PRINT ( name, format_str ) )
   # --- end of add_print (...) ---

   def add_def_line (
      self, name, ds_name, cf, color, step=None,
      width=None, legend=None, line_kwargs={}
   ):
      self.add_def ( name, ds_name, cf, step )
      self.add_line ( name, color, width, legend, line_kwargs )
   # --- end of add_def_line (...) ---

   def add_def_area (
      self, name, ds_name, cf, color, step=None,
      legend=None, stack=None, skipscale=None
   ):
      self.add_def ( name, ds_name, cf, step ),
      self.add_area ( name, color, legend, stack, skipscale )
   # --- end of add_def_area (...) ---

   def add_option ( self, option, *values ):
      if values:
         for value in values:
            self.extra_options.append ( option )
            self.extra_options.append ( value )
      else:
         self.extra_options.append ( option )
   # --- end of add_option (...) ---

   def construct_args ( self ):
      def gen_args():
         yield self.GRAPH_COMMAND
         yield '-'

         for attr_name in self.OPTIONS_ATTR:
            #attr = getattr ( self, attr_name, None )
            attr = getattr ( self, attr_name )
            if attr:
               yield '--' + attr_name.replace ( '_', '-' )
               yield str ( attr )
         # -- end for

         for color_spec in self.colors:
            yield '--color'
            yield str ( color_spec )

         for arg in self.extra_options:
            yield str ( arg )

         for arg in self.args:
            if isinstance ( arg, RRDGraphArg ):
               yield arg.get_str ( self.rrd_db )
            else:
               yield str ( arg )
      # --- end of gen_args (...) ---

      return tuple ( gen_args() )
   # --- end of construct_args (...) ---

   def make ( self ):
      def parse_output ( data, include_raw_data=False ):
         # output format:
         #   <key> = <value>\n
         # special case:
         #   image = BLOB_SIZE:<size>\n<image data>
         #

         WHITESPACE = ' '
         EQUAL      = '='
         NEWLINE    = '\n'

         # mode / data receive "protocol":
         # 0 -> read key,
         # 1 -> have first whitespace,
         # 2 -> have equal sign,
         # 3 -> have second whitespace <=> want value,
         # newline during 3 -> commit key/value, reset to mode 0
         #
         mode    = 0
         key     = ""
         value   = None
         get_chr = chr if sys.hexversion >= 0x3000000 else ( lambda b: b )


         for index, b in enumerate ( data ):
            c = get_chr ( b )
            if mode == 0:
               if c == WHITESPACE:
                  # done with key
                  mode += 1
               else:
                  # append to key
                  key += c
            elif mode == 1:
               if c == EQUAL:
                  mode += 1
               else:
                  raise Exception (
                     "expected equal sign after whitespace."
                  )
            elif mode == 2:
               if c == WHITESPACE:
                  mode += 1
                  value = ""
               else:
                  raise Exception (
                     "expected whitesapce after equal sign."
                  )
            elif c == NEWLINE:
               mode = 0

               if key == 'image':
                  img_size = int ( value.partition ( 'BLOB_SIZE:' ) [-1] )
                  img_data = data[index+1:index+img_size+1]
                  if len ( img_data ) == img_size:
                     yield ( "image_data", img_data )
                  else:
                     raise Exception (
                        "cannot read image (got {} out of {} bytes).".format (
                           len ( img_data ), img_size
                        )
                     )

                  yield ( "image_info", value )
                  yield ( "image_size", img_size )

                  # *** BREAK ***
                  break
               else:
                  try:
                     if key in { 'value_min', 'value_max' }:
                        c_val = float ( value )
                     else:
                        c_val = int ( value )
                     ival = int ( value )
                  except ValueError:
                     yield ( key, value )
                  else:
                     yield ( key, c_val )

                  key   = ""
                  value = None
            else:
               value += c
         # -- end for

         if include_raw_data:
            yield ( "raw_data", data )

      # --- end of parse_output (...) ---

      retcode, output = self.rrd_db._call_rrdtool (
         self.construct_args(), return_success=True, get_output=True,
         binary_stdout=True,
      )

      if retcode == os.EX_OK:
         self.image_data = dict ( parse_output ( output[0] ) )
         return True
      else:
         # discard output
         return False
   # --- end of make (...) ---

# --- end of RRDGraph  ---

class RRDGraphFactory ( object ):

   def __init__ ( self, rrd_db, graph_kwargs=None ):
      super ( RRDGraphFactory, self ).__init__()
      self.rrd_db          = rrd_db
      self.graph_kwargs    = dict() if graph_kwargs is None else graph_kwargs
      self.default_args    = list()
      self.default_options = list()
   # --- end of __init__ (...) ---

   def get_new ( self ):
      graph = RRDGraph ( self.rrd_db, **self.graph_kwargs )

      if self.default_args:
         graph.args.extend ( self.default_args )

      if self.default_options:
         graph.extra_options.extend ( self.default_options )

      return graph
   # --- end of get_new (...) ---

# --- end of RRDGraphFactory ---
