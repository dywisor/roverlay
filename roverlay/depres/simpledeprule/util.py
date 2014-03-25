# R overlay -- simple dependency rules
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.


class RuleFileSyntaxError ( Exception ):
   pass


def get_int_range_or_list (
   value_str, default_low=0, default_high=1000, list_sepa=','
):
   low, sepa, high = value_str.partition ( '..' )
   if sepa:
      i_low  = int ( low ) if low else default_low
      i_high = (
         int ( high ) if high else (
            i_low if default_high is True else default_high
         )
      )
      return ( True, i_low, i_high )
   else:
      return ( False,
         tuple ( int ( k ) for k in value_str.split ( list_sepa ) )
      )
# --- end get_int_range_or_list (...) ---



class SlotRestrict ( object ):
   def accepts ( self, k ):
      """Returns True if k is allowed, else False.

      arguments:
      * k -- int
      """
      return True

   def __bool__ ( self ):
      return True

   def __nonzero__ ( self ):
      return self.__bool__()

   def noexport ( self ):
      pass

   def __str__ ( self ):
      return ''
# --- end of SlotRestrict ---

class SlotSetRestrict ( SlotRestrict ):
   def __init__ ( self, iterable ):
      self._slotset = frozenset ( iterable )

   def accepts ( self, k ):
      """Returns True if k is allowed, else False.

      arguments:
      * k -- slot (str)
      """
      return k in self._slotset

   def __str__ ( self ):
      return ','.join ( sorted ( self._slotset ) )
   # --- end of __str__ (...) ---

# --- end of SlotSetRestrict ---

class SlotValueCreatorBase ( object ):

   def calculate_slot ( self, fuzzy, slot_value ):
      return slot_value

   def get_slot ( self, *args, **kwargs ):
      raise NotImplementedError()
   # --- end of get_slot (...) ---

   def __str__ ( self ):
      raise NotImplementedError()
   # --- end of __str__ (...) ---


class SingleIndexValueCreator ( SlotValueCreatorBase ):
   def __init__ ( self, index ):
      super ( SingleIndexValueCreator, self ).__init__()
      self._index = index
   # --- end of __init__ (...) ---

   def get_slot ( self, fuzzy ):
      version_components = fuzzy ['version_strlist']
      if len ( version_components ) > self._index:
         return version_components [self._index]
      else:
         return None
   # --- end of get_slot (...) ---

   def __str__ ( self ):
      return str ( self._index )


class IndexRangeSlotValueCreator ( SlotValueCreatorBase ):
   def __init__ ( self, low, high ):
      super ( IndexRangeSlotValueCreator, self ).__init__()
      self._low  = low
      self._high = high + 1 if high >= 0 else high

   def get_slot ( self, fuzzy ):
      # if self._low > self._high
      # if self._high < 0: -- dont care
      version_components = fuzzy ['version_strlist']
      if len ( version_components ) >= self._high:
         return '.'.join ( version_components [self._low:self._high] )
      else:
         return None
   # --- end of get_slot (...) ---

   def __str__ ( self ):
      return str ( self._low ) + '..' + str (
         ( self._high - 1 ) if self._high > 0 else self._high
      )

class ImmediateSlotValueCreator ( SlotValueCreatorBase ):
   def __init__ ( self, v_str ):
      super ( ImmediateSlotValueCreator, self ).__init__()
      self._value = v_str
      numparts = len ( v_str.split ( "." ) )
      assert numparts > 0

      if numparts < 2:
         self._slot_calculator = SingleIndexValueCreator ( 0 )
      else:
         self._slot_calculator = IndexRangeSlotValueCreator ( 0, numparts-1 )
   # --- end of __init__ (...) ---

   def calculate_slot ( self, fuzzy, slot_value ):
      cval = self._slot_calculator.get_slot ( fuzzy )
      return slot_value if cval is None else cval
   # --- end of calculate_slot (...) ---

   def get_slot ( self, *args, **kwargs ):
      return self._value
   # --- end of get_slot (...) ---

   def __str__ ( self ):
      return "i" + self._value

def get_slot_parser ( vstr ):
   if vstr [0] == 'i':
      # "immediate" value
      s = vstr [1:]
      return ImmediateSlotValueCreator ( v_str=s )
   else:
      range_or_list = get_int_range_or_list ( vstr, default_high=True )
      if range_or_list [0]:
         if range_or_list[1] == range_or_list[2]:
            return SingleIndexValueCreator ( index=range_or_list[1] )
         else:
            return IndexRangeSlotValueCreator (
               low=range_or_list[1], high=range_or_list[2]
            )
      elif len ( range_or_list[1] ) < 2:
         return SingleIndexValueCreator ( index=range_or_list[1][0] )
      else:
         raise RuleFileSyntaxError (
            "slot part selection must not be a list"
         )
# --- end of get_slot_parser (...) ---

def get_slot_restrict ( vstr ):
   if vstr:
      return SlotSetRestrict ( vstr.split ( ',' ) )
   else:
      return None
# --- end of get_slot_restrict (...) --
