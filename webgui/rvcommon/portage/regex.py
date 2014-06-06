# R overlay -- common webgui functionality, regex
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import operator
import re

# FIXME: "*" slot operator is illegal when a slot is set

_named_regex = lambda a, b: ( r'(?P<' + a + r'>' + b + r')' )
_format_all  = lambda s, A: [ s.format(a) for a in A ]

def _add_union_v ( iterables ):
   # iterable := str (->(str,)) or list/tuple/...
   if iterables:
      recur_result = list ( _add_union_v(iterables[:-1]) )
      if (
         isinstance ( iterables[-1], str )
         or not hasattr ( iterables[-1], '__iter__' )
      ):
         if recur_result:
            for res in recur_result:
               yield res + iterables[-1]
         else:
            yield iterables[-1]
      elif recur_result:
         for item in iterables[-1]:
            for res in recur_result:
               yield res + item
      else:
         for item in iterables[-1]:
            yield item
# --- end of _add_union_v (...) ---

def _add_union ( *iterables ):
   return list ( _add_union_v ( iterables ) )
# --- end of _add_union (...) ---


A_RE_USEFLAG_NAME            = r'[a-z-_]+'
A_RE_DEP_USEFLAG_SIGN        = r'[-]'
A_RE_DEP_USEFLAG_DEFAULT     = r'[(][+-][)]'
A_RE_DEP_USEFLAG_CONDITIONAL = r'[?=]'
A_RE_DEP_ATOM_USEFLAG = (
   "(?:{sign})?{name}(?:{default})?(?:{conditional})?".format (
      sign=A_RE_DEP_USEFLAG_SIGN, name=A_RE_USEFLAG_NAME,
      default=A_RE_DEP_USEFLAG_DEFAULT, conditional=A_RE_DEP_USEFLAG_CONDITIONAL
   )
)

##RE_DEP_ATOM_USE = (
##   r'(?:\[(?P<useflags>{0}(?:[,]{0})*)\])'.format ( A_RE_DEP_ATOM_USEFLAG )
##)

# accept empty "[]"
RE_DEP_ATOM_USE = (
   r'(?:\[(?P<useflags>{0}(?:[,]{0})*)?\])'.format ( A_RE_DEP_ATOM_USEFLAG )
)



# <digit>(<digit|.>*<digit>)?
#  more precisely <digit>(<digit|.>?<digit>+)*
_RE_DOT_DIGITS = r'[0-9](?:[0-9.]*[0-9])?'

A_RE_CATEGORY_NAME = r'[{0}{1}]*[{0}]'.format ( r'a-zA-Z+0-9', r'-_' )
#A_RE_PACKAGE_NAME  = A_RE_CATEGORY_NAME

# package name: disallow expressions ending in "-" followed by digits only
#
# a := always-allowed name chars without digits
# b := digits
# c := sometimes-allowed name chars, e.g. "-" and "_"
#
## expr := {ab}*{ab}                 (1) -- equiv {ab}{ab}*
## expr := {ab}{abc}*{a}             (2) -- superseeded by (3)
## expr := {ab}{abc}*{ab}*{a}{ab}*   (3) -- read {ab}<STH>{ab}*
##
## <<expr>> := {ab} ({abc}*{ab}*{a})? {ab}*
#
A_RE_PACKAGE_NAME = (
   r'[{a}{b}](?:[{a}{b}{c}]*[{a}{b}]*[{a}])?[{a}{b}]*'.format (
      a=r'a-zA-Z+', b=r'0-9', c=r'-_'
   )
)


#RE_DEP_ATOM_PREFIX             = r'(?P<prefix>([~]|[!]{1,2}))'
RE_DEP_ATOM_PREFIX_NEEDVER     = r'(?P<prefix>[~])'
RE_DEP_ATOM_PREFIX_DEFAULT     = r'(?P<prefix>[!]{1,2})'
# < | > | <= | >= | =
RE_DEP_ATOM_PREFIX_OP          = r'(?P<prefix_operator>(?:[<>]?[=]|[<>]))'
RE_DEP_ATOM_CATEGORY           = _named_regex ( 'category', A_RE_CATEGORY_NAME )
RE_DEP_ATOM_PACKAGE            = _named_regex ( 'package',  A_RE_PACKAGE_NAME )
# <digit>(<digit|.>*<digit>)?<char:a-z^>?
RE_DEP_ATOM_VERSION            = _named_regex ( 'version', _RE_DOT_DIGITS + '[a-zA-Z]?' )
# (alpha|beta|pre|rc|p)<digit>*<digit>
A_RE_DEP_ATOM_VERSION_SUFFIX   = r'(alpha|beta|pre|rc|p)([0-9]+)'
RE_DEP_ATOM_VERSION_SUFFIX     = (
   r'(?P<version_suffix>(?:_' + A_RE_DEP_ATOM_VERSION_SUFFIX + r')+)'
)
RE_DEP_ATOM_POSTFIX            = r'(?P<postfix>[*])'
# r<digit>*<digit>
RE_DEP_ATOM_REVISION           = r'(?:r(?P<revision>[0-9]+))'

## FIXME:
#
# <slot>                 := _RE_DOT_DIGITS
# <subslot>              := _RE_DOT_DIGITS
# <slot operator'subset> := =
# <slot operator'all>    := \* | <slot operator'subset>
#
# slot                   := [<slot>[/<subslot>]]<slot operator'subset>
# slot                   := <slot operator'all>
#
#  re.compile complains about field name redifinition
#   ==> using more than one regex
#   (a) <slot>, <subslot> with optional slot op
#   (b) slot op only
#
RE_DEP_ATOM_SLOT = (
   r'(?:(?P<slot>{d})(?:/(?P<subslot>{d}))?)(?P<slot_operator>[=])?'.format (
      d=_RE_DOT_DIGITS
   ),
   r'(?P<slot_operator>[=*])'
)

OLD_RE_DEP_ATOM_SLOT               = (
   (
      r'(?:'
         r'(?P<slot>{0})(?:/(?P<subslot>{0}))?'
      r')'
      r'(?P<slot_operator>[*=])?'
   ).format ( r'[0-9](?:[0-9.]*[0-9])?' )
)
##RE_DEP_ATOM_SLOT = OLD_RE_DEP_ATOM_SLOT


RE_DEP_ATOM_VERSION_STR = (
   # FIXME: '*' postfix after revision? (probably illegal)
   r'{version}{version_suffix}?(?:[-]{revision})?{postfix}?'.format (
      version        = RE_DEP_ATOM_VERSION,
      version_suffix = RE_DEP_ATOM_VERSION_SUFFIX,
      revision       = RE_DEP_ATOM_REVISION,
      postfix        = RE_DEP_ATOM_POSTFIX,
   )
)

RE_DEP_ATOM_USEFLAG = (
   '(?P<sign>{sign})?(?P<name>{name})'
   '(?P<default>{default})?(?P<conditional>{conditional})?'
).format (
   sign=A_RE_DEP_USEFLAG_SIGN, name=A_RE_USEFLAG_NAME,
   default=A_RE_DEP_USEFLAG_DEFAULT,
   conditional=A_RE_DEP_USEFLAG_CONDITIONAL
)



RE_DEP_ATOM = [
   expr.format (
      prefix_needver = RE_DEP_ATOM_PREFIX_NEEDVER,
      prefix_default = RE_DEP_ATOM_PREFIX_DEFAULT,
      prefix_op      = RE_DEP_ATOM_PREFIX_OP,
      category       = RE_DEP_ATOM_CATEGORY,
      package        = RE_DEP_ATOM_PACKAGE,
   ) for expr in (
      # 3 * len(RE_DEP_ATOM_SLOT) * len(RE_DEP_ATOM_USE~) => 6 combinations
      _add_union (
         # 3 combinations
         (
            # 2*1 combinations
            _add_union (
               (
                  r'{prefix_needver}{prefix_op}?',
                  r'{prefix_default}?{prefix_op}',
               ),
               ( '{category}/{package}[-]' + RE_DEP_ATOM_VERSION_STR ),
            )
            # 1 combination
            + [ r'{prefix_default}?{category}/{package}', ]
         ),
         _format_all ( r'(?:[:]{0})?', RE_DEP_ATOM_SLOT ),
         RE_DEP_ATOM_USE + '?'
      )
   )
]


# abstraction class for dealing with >=1 regexes
#
class MultiRegexProxy ( object ):

   DEBUG = False

   @classmethod
   def compile ( cls, expressions, convert=None ):
      if isinstance ( expressions, str ):
         expressions = ( expressions, )

      if not convert:
         expr_list = list ( expressions )
      elif convert is True:
         expr_list = [ ( r'^' + s + r'$' ) for s in expressions ]
      else:
         expr_list = [ convert(s) for s in expressions ]
      # -- end if

      assert expr_list
      if len ( expr_list ) == 1:
         return re.compile ( expr_list[0] )
      else:
         return cls ( expr_list )
   # --- end of compile (...) ---

   @classmethod
   def compile_exact ( cls, expressions ):
      return cls.compile ( expressions, convert=True )
   # --- end of compile_exact (...) ---

   @property
   def pattern ( self ):
      return [ r.pattern for r in self._compiled_regexes ]

   def __init__ ( self, expressions ):
      super ( MultiRegexProxy, self ).__init__()
      self._compiled_regexes = [ re.compile(s) for s in expressions ]

   def _foreach ( self, method_name, args, kwargs ):
      caller = operator.methodcaller ( method_name, *args, **kwargs )
      for re_obj in self._compiled_regexes:
         yield ( re_obj, caller ( re_obj ) )

   def _get_result_from_any ( self, method_name, args, kwargs ):
      for re_obj, result in self._foreach ( method_name, args, kwargs ):
         if result is not None:
            if self.DEBUG and args and args[0]:
               print ( "{!r} matched by {!r}".format(args[0],re_obj.pattern) )
               print(result.groups())
               print(result.groupdict())
            return result
      return None

   def search ( self, *args, **kwargs ):
      return self._get_result_from_any ( 'search', args, kwargs )

   def match ( self, *args, **kwargs ):
      return self._get_result_from_any ( 'match', args, kwargs )

   def foreach ( self, method_name, *args, **kwargs ):
      return self._foreach ( method_name, args, kwargs )

# --- end of MultiRegexProxy ---

def setup_debug():
   MultiRegexProxy.DEBUG = True
# --- end of setup_debug (...) ---


# compiled regexes
#
DEP_ATOM         = MultiRegexProxy.compile_exact ( RE_DEP_ATOM )
DEP_ATOM_USEFLAG = MultiRegexProxy.compile ( RE_DEP_ATOM_USEFLAG )
DEP_ATOM_VERSION = MultiRegexProxy.compile_exact ( RE_DEP_ATOM_VERSION_STR )
DEP_ATOM_VERSION_SUFFIX = MultiRegexProxy.compile_exact (
   A_RE_DEP_ATOM_VERSION_SUFFIX
)


if __name__ == '__main__':
   import sys

   for match in filter (
      None, map ( DEP_ATOM.match, filter ( None, sys.argv[1:] ) )
   ):
      print ( "{!s} : {!s}".format ( match.string, match.groupdict() ) )
