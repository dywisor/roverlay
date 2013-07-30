# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

class MethodNotImplementedError ( NotImplementedError ):
   def __init__ ( self, obj, method, msg=None ):
      if isinstance ( obj, str ):
         obj_name = obj
      elif hasattr ( obj, '__class__' ):
         obj_name = obj.__class__.__name__
      elif hasattr ( obj, '__name__' ):
         obj_name = obj.__name__
      else:
         obj_name = repr ( obj )

      if isinstance ( method, str ):
         method_name = method
      elif hasattr ( method, '__name__' ):
         method_name = method.__name__
      else:
         method_name = repr ( method )

      method_str = "{}.{}()".format ( obj_name, method_name )

      if msg:
         super ( MethodNotImplementedError, self ).__init__ (
            method_str + ': ' + str ( msg )
         )
      else:
         super ( MethodNotImplementedError, self ).__init__ ( method_str )
   # --- end of __init__ (...) ---

# --- end of MethodNotImplementedError ---

class MethodNotImplemented ( MethodNotImplementedError ):
   # compat class
   pass
# --- end of MethodNotImplemented ---

class AbstractMethodError ( MethodNotImplementedError ):
   def __init__ ( self, obj, method ):
      super ( AbstractMethodError, self ).__init__ (
         obj, method, "has to be implemented by derived classes"
      )

# --- end of AbstractMethodError ---

def _get_exception_wrapper ( err_cls, func ):
   def wrapped ( obj, *args, **kwargs ):
      raise err_cls ( obj, func )
   # --- end of wrapped (...) ---

   if func is not None:
      wrapped.__name__ = func.__name__
      wrapped.__doc__  = func.__doc__
      wrapped.__dict__.update ( func.__dict__ )
   return wrapped

# --- end of _get_exception_wrapper (...) ---

def abstractmethod ( func=None ):
   return _get_exception_wrapper ( AbstractMethodError, func )
# --- end of abstractmethod (...) ---

def not_implemented ( func=None ):
   return _get_exception_wrapper ( MethodNotImplementedError, func )
# --- end of not_implemented (...) ---
