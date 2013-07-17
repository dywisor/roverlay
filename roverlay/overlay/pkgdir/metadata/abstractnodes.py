# R overlay -- metadata package, basic metadata nodes
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""abstract metadata nodes

This module implements abstract metadata nodes.
Metadata (xml) files are created by using a tree-structure of metadata nodes,
where every node has 0..n child nodes.
"""

__all__ = [ 'MetadataLeaf', 'MetadataNode',
   'MetadataNodeNamedAccess', 'MetadataNodeOrdered'
]

from roverlay import strutil

import textwrap

INDENT = '\t'

def get_indent ( k ): return k * INDENT

# -- "abstract" metadata nodes --
class _MetadataBasicNode ( object ):
   """
   This is the most basic metadata node that should never be used directly.
   """

   # these chars lead to metadata.bad: invalid token
   INVALID_CHARS = "&<>"

   def __init__ ( self, name, flags ):
      """Initializes a _MetadataBasicNode.

      arguments:
      * name  -- name of this node, e.g. 'flag'
      * flags -- flags of this node, e.g. 'name=byte-compile'
      """
      self.name     = name
      self.flags    = flags
      # priority is used to sort nodes (e.g. longdescription after description)
      self.priority = 1000
      self._enabled = True
      self._set_level ( 0 )
   # --- end of __init__ (...) ---

   def active ( self ):
      """Returns True if this node is active."""
      return self._enabled
   # --- end of active (...) ---

   def _set_level ( self, _level, has_indent=True ):
      """Sets the level (depth) of this node.

      arguments:
      * _level     -- level to set
      * has_indent -- if this node should indent its subnodes (or text)
      """
      self.level = _level
      if has_indent:
         self.indent = get_indent ( self.level )
      else:
         self.indent = ''
   # --- end of _set_level (...) ---

   def set_flag ( self, flagname, flagvalue=None ):
      """Sets the specified flag.

      arguments:
      * flagname  -- flag name
      * flagvalue -- flag value, defaults to None->''
      """
      self.flags [flagname] = '' if flagvalue is None else flagvalue
   # --- end of set_flag (...) ---

   def _flaglist ( self ):
      """Returns a "flagname=flagvalue" list."""
      return [
         '{name}="{val}"'.format ( f_tup[0], f_tup[1] )
         for f_tup in self.flags.items()
      ]
   # --- end of _flaglist (...) ---


   def _flagstr ( self ):
      """Returns the string representation of this node's flags, including
      a leading whitespace char.
      """
      if self.flags is None:
         return ''

      ret = ' '.join ( self._flaglist() )
      if ret:
         # don't forget the leading space
         return ' ' + ret
      else:
         return ''
   # --- end of _flagstr (...) ---

   def _do_verify ( self ):
      """Verifies this node.
      Does nothing if self._verify is not implemented, else dies on error.
      """
      if hasattr ( self, '_verify' ) and not self._verify():
         raise Exception ( "verification failed for a metadata node." )
   # --- end of _do_verify (...) ---

   # not using __str__, make (recursive) node calls explicit
   def to_str ( self ):
      """Returns a string representing this node."""
      self._do_verify()
      return "{indent}<{name}{flags}></{name}>".format (
         indent=self.indent,
         name=self.name,
         flags=self._flagstr()
      )
   # --- end of to_str (...) ---


class MetadataNode ( _MetadataBasicNode ):
   """A _MetadataBasicNode with child nodes."""

   def __init__ ( self, name, flags=dict() ):
      super ( MetadataNode, self ) . __init__ ( name, flags )
      self.nodes = list()
   # --- end of __init__ (...) ---

   def add ( self, node ):
      """Adds a child node to this node. Fixes/sets the level of this node.

      arguments:
      * node --
      """
      node._set_level ( self.level + 1 )
      self.nodes.append ( node )
   # --- end of add (...) ---

   # copy add to _add_node
   _add_node = add

   def _sort_nodes ( self ):
      """Sorts the child nodes of this node."""
      self.nodes.sort ( key=lambda node : node.priority )
   # --- end of _sort_nodes (...) ---

   def _nodelist ( self ):
      """Returns a list of strings representing the child nodes."""
      return tuple (
         filter (
            lambda k: k is not None,
            [ node.to_str() for node in self.nodes if node.active() ]
         ),
      )
   # --- end of _nodelist (...) ---

   def _nodestr ( self ):
      """Returns a string representing all child nodes."""
      self._sort_nodes()
      node_repr = self._nodelist()
      if len ( node_repr ):
         # add newlines before/after and indent after node_repr!
         return "\n{node_text}\n{indent}".format (
            node_text='\n'.join ( node_repr ), indent=self.indent
         )
      else:
         return ''
   # --- end of _nodestr (...) ---

   def to_str ( self ):
      """Returns a string representing this node and all of its child nodes."""
      self._do_verify()
      return "{indent}<{name}{flags}>{text}</{name}>".format (
         indent=self.indent,
         name=self.name,
         flags=self._flagstr(),
         text=self._nodestr()
      )
   # --- end of to_str (...) ---


class MetadataNodeOrdered ( MetadataNode ):
   """A metadata node whose nodes have to be interpreted as an already
   ordered string."""
   # could derive MetadataNode from this
   def _sort_nodes ( self ): return


class MetadataLeaf ( _MetadataBasicNode ):
   """A metadata node that has no child nodes, only a string."""

   def __init__ ( self, name, flags=dict(), value=None ):
      self._text_wrapper     = None
      super ( MetadataLeaf, self ) . __init__ ( name, flags )

      self.value             = "" if value is None else value
      self.print_node_name   = True
      self.value_format      = 0

   def _set_level ( self, _level, has_indent=True ):
      super ( MetadataLeaf, self ) . _set_level ( _level, has_indent )

      # indenting multi-line text by one level more than self.indent
      self.text_indent = self.indent + INDENT

      # update text wrapper if existent
      if not self._text_wrapper is None:
         self._text_wrapper.subsequent_indent = self.text_indent

   def _default_value_str ( self ):
      """Returns the value string. Derived classes may override this."""
      def char_allowed ( c ):
         return c not in self.__class__.INVALID_CHARS
      # --- end of char_allowed (...) ---

      #if self.value_format == ?: format value ~

      return strutil.ascii_filter (
            str ( self.value ),
            additional_filter = char_allowed
      )
   # --- end of _value_str (...) ---

   def _pretty_value_str ( self ):
      """Returns a formatted value string (max line length etc.).
      Not used here, but subclasses can use it by simply writing
      '_value_str = MetadataLeaf._pretty_value_str' in the class body.
      """
      if not self.value: return ""

      if self._text_wrapper is None:
         self._text_wrapper = textwrap.TextWrapper (
            initial_indent='',
            subsequent_indent=self.text_indent,
            width=self.linewidth if hasattr ( self, 'linewidth' ) else 50
         )

      val_lines = self._text_wrapper.wrap ( self._default_value_str() )

      if len ( val_lines ) < 1:
         # why?
         return ""
      elif len ( val_lines ) == 1:
         # single line, no indent/newline
         return val_lines [0]
      else:
         # add newline before/after, add indent after
         val_lines [0] = '\n' + self.text_indent + val_lines [0]
         val_lines.append ( self.indent )
         return '\n'.join ( val_lines )
   # --- end of _pretty_value_str (...) ---

   def to_str ( self ):
      self._do_verify()
      if self.print_node_name:
         return "{indent}<{name}{flags}>{value}</{name}>".format (
            indent = self.indent,
            name   = self.name,
            flags  = self._flagstr(),
            value  = self._value_str() \
               if hasattr ( self, '_value_str' ) else self._default_value_str()
         )
      else:
         # not very useful, but allows to insert strings as nodes
         return self.indent + self._value_str()
   # --- end of to_str (...) ---

class MetadataNodeNamedAccess ( MetadataNode ):
   """A metadata node that offers key-based (dictionary) access to some of
   its nodes."""

   def __init__ ( self, name, flags=dict() ):
      super ( MetadataNodeNamedAccess, self ) . __init__ ( name, flags )
      # the access dict
      self.node_dict = dict()

   def add ( self, node, with_dict_entry=True, fail_if_existent=True ):
      """Adds a child node.

      arguments:
      * node             -- node to add
      * with_dict_entry  -- add node to the access dict, defaults to True
      * fail_if_existent -- fail if node's name already in the access dict,
                             defaults to True
      """

      super ( MetadataNodeNamedAccess, self ) . add ( node )
      if with_dict_entry:
         if fail_if_existent and node.name in self.node_dict:
            raise Exception ( "key exists." )
         else:
            self.node_dict [node.name] = node
   # --- end of add (...) ---

   def get ( self, node_name ):
      """Returns node by name.

      arguments:
      * node_name

      raises: KeyError if node_name not in the access dict
      """
      return self.node_dict [node_name]
   # --- end of get (...) ---

   def has_named ( self, node_name ):
      """Returns True if node_name in the access dict else False."""
      return node_name in self.node_dict
   # --- end of has_named (...) ---
