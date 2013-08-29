# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import weakref

class ObjectDisappeared ( Exception ):
   pass
# --- end of ObjectDisappeared ---

class SafeWeakRef ( weakref.ref ):

   def deref_unsafe ( self ):
      return super ( SafeWeakRef, self ).__call__()
   # --- end of deref_unsafe (...) ---

   def deref_safe ( self ):
      obj = super ( SafeWeakRef, self ).__call__()
      if obj is not None:
         return obj
      else:
         raise ObjectDisappeared()
   # --- end of deref_safe (...) ---

   __call__ = deref_safe
   deref    = deref_safe

   def __bool__ ( self ):
      return self.deref_unsafe() is not None
   # --- end of __bool__ (...) ---

   def __repr__ ( self ):
      obj = self.deref_unsafe()
      if obj:
         return "<{} at 0x{:x} to {!r} at 0x{:x}>".format (
            self.__class__.__name__, id ( self ),
            obj.__class__.__name__, id ( obj )
         )
      else:
         return "<{} at 0x{:x} to None>".format (
            self.__class__.__name__, id ( self )
         )
   # --- end of __repr__ (...) ---

# --- end of SafeWeakRef ---


class NoneRef ( object ):

   def __init__ ( self, obj=None ):
      super ( NoneRef, self ).__init__()
      assert obj is None
   # --- end of NoneRef (...) ---

   def deref_unsafe ( self ):
      return None
   # --- end of deref_unsafe (...) ---

   def deref_safe ( self ):
      raise ObjectDisappeared()
   # --- end of deref_safe (...) ---

   __call__ = deref_safe
   deref    = deref_safe

   def __bool__ ( self ):
      return False
   # --- end of __bool__ (...) ---

   def __repr__ ( self ):
      return "<NoneRef at 0x{:x}>".format ( id ( self ) )
   # --- end of __repr__ (...) ---

# --- end of NoneRef ---

def get_object_ref ( obj ):
   if obj is None:
      return NoneRef()
   elif hasattr ( obj, 'get_ref' ):
      return obj.get_ref()
   else:
      return SafeWeakRef ( obj )
# --- end of get_object_ref (...) ---


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


class Referenceable ( object ):

   CACHE_REF = False

   def __init__ ( self, *args, **kwargs ):
      super ( Referenceable, self ).__init__()
      self._cached_selfref = None
      if self.CACHE_REF:
         self.cache_ref()
   # --- end of __init__ (...) ---

   def cache_ref ( self ):
      self._cached_selfref = self.get_new_ref()
      self.get_ref = self._get_cached_ref
   # --- end of cache_ref (...) ---

   def _get_cached_ref ( self ):
      return self._cached_selfref
   # --- end of _get_cached_ref (...) ---

   def get_new_ref ( self ):
      return SafeWeakRef ( self )
   # --- end of get_new_ref (...) ---

   get_ref = get_new_ref

# --- end of Referenceable ---


class ReferenceTree ( Referenceable ):

   def __init__ ( self, parent ):
      super ( ReferenceTree, self ).__init__()
      self.parent_ref = None
      self.set_parent ( parent )
   # --- end of __init__ (...) ---

   def set_parent ( self, parent ):
      self.parent_ref = get_object_ref ( parent )
   # --- end of set_parent (...) ---

   def get_parent ( self ):
      return self.parent_ref.deref_safe()
   # --- end of get_parent (...) ---

   get_upper = get_parent

# --- end of ReferenceTree ---


class ObjectView ( object ):

   ObjectDisappeared = ObjectDisappeared

   def __init__ ( self, obj ):
      super ( ObjectView, self ).__init__()
      self.obj_ref = get_object_ref ( obj )
      self.deref_unsafe = self.obj_ref.deref_unsafe
      self.deref_safe   = self.obj_ref.deref_safe
      self.deref        = self.obj_ref.deref_safe
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      return bool ( self.obj_ref )
   # --- end of __bool__ (...) ---

   @abstractmethod
   def update ( self ):
      pass
   # --- end of update (...) ---

# --- end of ObjectView ---
