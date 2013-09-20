# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import weakref
import sys

if sys.hexversion >= 0x3000000:
   from ._abc3 import AbstractObject
else:
   from ._abc2 import AbstractObject

__all__ = [
   'get_object_ref', 'abstractmethod', 'not_implemented', 'AbstractObject',
]


class ObjectDisappeared ( Exception ):
   pass
# --- end of ObjectDisappeared ---

class SafeWeakRef ( weakref.ref ):
   """A weak reference that supports 'safe' dereferencing, i.e. raising an
   exception if the referenced object does no longer exist."""

   def deref_unsafe ( self ):
      """Dereferences without checking whether the object exists.

      Returns: the object / None
      """
      return weakref.ref.__call__ ( self )
   # --- end of deref_unsafe (...) ---

   def deref_safe ( self ):
      """Safely dereferences the object.

      Returns: the object

      Raises: ObjectDisappeared if the object does no longer exist.
      """
      obj = self.deref_unsafe()
      if obj is not None:
         return obj
      else:
         raise ObjectDisappeared()
   # --- end of deref_safe (...) ---

   __call__ = deref_safe
   deref    = deref_safe

   def __bool__ ( self ):
      """Returns True if the referenced object exists, else False."""
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
   """A 'reference' to None (compat object)."""

   __instance = None

   @classmethod
   def get_static ( cls, obj=None ):
      assert obj is None
      if cls.__instance is None:
         cls.__instance = cls ( obj=obj )
      return cls.__instance
   # --- end of get_static (...) ---

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
   """Returns a reference to the given object, either by using the object's
   get_ref() function (if defined) or by creating a SafeWeakRef/NoneRef
   instance.

   arguments:
   * obj --
   """
   if obj is None:
      return NoneRef.get_static()
   elif isinstance ( obj, ( SafeWeakRef, NoneRef, weakref.ref ) ):
      return obj
   elif hasattr ( obj, 'get_ref' ):
      return obj.get_ref()
   else:
      return SafeWeakRef ( obj )
# --- end of get_object_ref (...) ---


class MethodNotImplementedError ( NotImplementedError ):

   def __init__ ( self, obj, method, msg=None, params=None ):
      """Constructor for MethodNotImplementedError.

      arguments:
      * obj    -- object/class to which the method is bound
      * method -- method that is not implemented
      * msg    -- additional information (if set)
      * params -- an iterable of parameters (args/kwargs) that the method
                  accepts (used for generating more meaningful messages)
      """
      super ( MethodNotImplementedError, self ).__init__ (
         self._get_error_message ( obj, method, msg, params )
      )
   # --- end of __init__ (...) ---

   # or staticmethod, unbound, ...
   @classmethod
   def _compare_arg_count ( self, params, method ):
         if (
            hasattr ( method, '__code__' ) and
            hasattr ( method.__code__, 'co_argcount' )
         ):
            plen = len ( params )
            if (
               plen != method.__code__.co_argcount and (
                  params[0] in { 'self', 'cls' } or
                  ( plen + 1 ) != method.__code__.co_argcount
               )
            ):
               raise AssertionError (
                  "params, arg count mismatch: {:d} != {:d}".format (
                     len ( params ), method.__code__.co_argcount
                  )
               )
            del plen
         # -- end if __debug__
   # --- end of _compare_arg_count (...) ---

   @classmethod
   def _get_error_message ( cls, obj, method, msg=None, params=None ):
      # obj_name =
      if isinstance ( obj, str ):
         obj_name = obj
      elif hasattr ( obj, '__class__' ):
         obj_name = obj.__class__.__name__
      elif hasattr ( obj, '__name__' ):
         obj_name = obj.__name__
      else:
         obj_name = repr ( obj )

      # method_name =
      if isinstance ( method, str ):
         method_name = method
      elif hasattr ( method, '__name__' ):
         method_name = method.__name__
      else:
         method_name = repr ( method )

      # method str =
      if params:
         if __debug__:
            cls._compare_arg_count ( params, method )

         method_str = "{}.{} ( {} )".format (
            obj_name, method_name, ', '.join ( params )
         )
      else:
         method_str = "{}.{}()".format ( obj_name, method_name )

      # method_str +=
      if msg:
         return method_str + ': ' + str ( msg )
      else:
         return method_str
   # --- end of _get_error_message (...) ---

# --- end of MethodNotImplementedError ---

class MethodNotImplemented ( MethodNotImplementedError ):
   # compat class
   pass
# --- end of MethodNotImplemented ---

class AbstractMethodError ( MethodNotImplementedError ):
   def __init__ ( self, obj, method, params=None ):
      super ( AbstractMethodError, self ).__init__ (
         obj, method, "has to be implemented by derived classes",
         params=params,
      )

# --- end of AbstractMethodError ---

def _create_exception_wrapper ( err_cls, func, err_args=(), err_kwargs={} ):
   """Returns a method that raises the given exception when called.

   arguments:
   * err_cls -- class/constructor of the exception that should be raised.
                Has to accept 2 args:
                - object to which the method is bound
                - the actual function
   * func    -- function to be wrapped
   """
   def wrapped ( obj, *args, **kwargs ):
      raise err_cls ( obj, func, *err_args, **err_kwargs )
   # --- end of wrapped (...) ---

   if func is not None:
      wrapped.__name__ = func.__name__
      wrapped.__doc__  = func.__doc__
      wrapped.__dict__.update ( func.__dict__ )
   return wrapped
# --- end of _create_exception_wrapper (...) ---

def _get_exception_wrapper ( err_cls, func=None, err_args=(), err_kwargs={} ):
   if func is None:
      return lambda real_func: _create_exception_wrapper (
         err_cls, real_func, err_args, err_kwargs
      )
   else:
      return _create_exception_wrapper ( err_cls, func, err_args, err_kwargs )
# --- end of _get_exception_wrapper (...) ---

def abstractmethod ( func=None, **kwargs ):
   return _get_exception_wrapper (
      AbstractMethodError, func, err_kwargs=kwargs
   )
# --- end of abstractmethod (...) ---

def not_implemented ( func=None, **kwargs ):
   return _get_exception_wrapper (
      MethodNotImplementedError, func, err_kwargs=kwargs
   )
# --- end of not_implemented (...) ---


class Referenceable ( object ):

   CACHE_REF = False

   def __init__ ( self, *args, **kwargs ):
      """Initializes a referenceable object. Ignores all args/kwargs."""
      super ( Referenceable, self ).__init__()
      self._cached_selfref = None
      if self.CACHE_REF:
         self.cache_ref()
   # --- end of __init__ (...) ---

   def cache_ref ( self ):
      """Creates a cached reference and sets get_ref() so that the cached ref
      is returned (when called)."""
      self._cached_selfref = self.get_new_ref()
      self.get_ref = self._get_cached_ref
   # --- end of cache_ref (...) ---

   def _get_cached_ref ( self ):
      """Returns the cached reference."""
      return self._cached_selfref
   # --- end of _get_cached_ref (...) ---

   def get_new_ref ( self ):
      """Returns a new reference."""
      return SafeWeakRef ( self )
   # --- end of get_new_ref (...) ---

   # initially, get_ref() is get_new_ref()
   get_ref = get_new_ref

# --- end of Referenceable ---


class ReferenceTree ( Referenceable ):
   """A Referenceable that is part of a tree-like data structure with weak
   backreferences (each object has one ancestor or None)."""

   def __init__ ( self, parent ):
      """Intializes this referencable object.

      arguments:
      * parent -- the parent object (typically not a reference)
      """
      super ( ReferenceTree, self ).__init__()
      self.parent_ref = None
      self.set_parent ( parent )
   # --- end of __init__ (...) ---

   def set_parent ( self, parent ):
      """(Re-)sets the parent object.

      arguments:
      * parent -- the parent object (typically not a reference)
      """
      self.parent_ref = get_object_ref ( parent )
   # --- end of set_parent (...) ---

   def get_parent ( self ):
      """Returns the parent object (dereferenced parent object reference)."""
      return self.parent_ref.deref_safe()
   # --- end of get_parent (...) ---

   #get_upper() is an alias to get_parent()
   get_upper = get_parent

# --- end of ReferenceTree ---


class ObjectView ( object ):
   """A view object (=expose a (sub-)set of another object's data) that
   uses weak references."""

   ObjectDisappeared = ObjectDisappeared

   def __init__ ( self, obj ):
      """Initializes an object view.

      arguments:
      * obj -- object to be "viewed"
      """
      super ( ObjectView, self ).__init__()
      self.obj_ref      = get_object_ref ( obj )
      self.deref_unsafe = self.obj_ref.deref_unsafe
      self.deref_safe   = self.obj_ref.deref_safe
      self.deref        = self.obj_ref.deref_safe
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      """Returns True if the actual object exists, else False."""
      return bool ( self.obj_ref )
   # --- end of __bool__ (...) ---

   @abstractmethod
   def update ( self ):
      """Updates this view (collect data from the actual object etc.)."""
      pass
   # --- end of update (...) ---

# --- end of ObjectView ---


class PersistentContent ( object ):

   def __init__ ( self, *args, **kwargs ):
      super ( PersistentContent, self ).__init__()
      self._dirty = False
   # --- end of __init__ (...) ---

   @property
   def dirty ( self ):
      return self._dirty
   # --- end of dirty (...) ---

   def set_dirty ( self ):
      self._dirty = True
   # --- end of set_dirty (...) ---

   def reset_dirty ( self, value=False ):
      self._dirty = bool ( value )
   # --- end of reset_dirty (...) ---

# --- end of PersistentContent ---
