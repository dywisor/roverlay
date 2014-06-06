# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

import functools

from django.test import TestCase
from django.core.exceptions import ValidationError

import rvcommon.portage.regex
#rvcommon.portage.regex.setup_debug()

from rvcommon.portage import models

DependencyAtom = models.DependencyAtom


def get_nested_attr ( obj, name ):
   """Returns a 'nested' attribute, e.g. obj.another_obj.value."""
   return functools.reduce ( getattr, name.split("."), obj )

def dep_atom_from_str ( s ):
   return DependencyAtom._from_str ( DependencyAtom, s )


# Create your tests here.

class DependencyAtomTests ( TestCase ):

   # *_DEP_ATOMS syntax:
   #  *_DEP_ATOM := list (
   #     dep_atom_str | tuple( dep_atom_str,None|False|dict<values> )
   #  )

   BAD_DEP_ATOMS = (
      "cat/pkg-0",
      "=c_at/p-_k_-g-2-2",
      "~c_at/p-_k_-g-2.2.",
      "=cat/pkg-1.0a:",
      "=cat/pkg-1.0a=",
      "=cat/p-k-g-1.0a:2-r2",
      "<cat/pkg-2.5.4_p0_p1_p2_p3_p4_alpha134=[a,-b,c(+),-d(-)]",
      "bad/slot-operator:2*",
   )

   GOOD_DEP_ATOMS = (
      ## from man 5 ebuild
      # "Atom Bases"
      "sys-apps/sed",
      "sys-libs/zlib",
      "net-misc/dhcp",
      # "Atom Prefix Operators"
      ">media-libs/libgd-1.6",
      ">=media-libs/libgd-1.6",
      "=media-libs/libgd-1.6",
      "<=media-libs/libgd-1.6",
      "<media-libs/libgd-1.6",
      # "Extended Atom Prefixes and Postfixes"
      "~net-libs/libnet-1.0.2a",
      "!app-text/dos2unix",
      "!!<sys-apps/portage-2.1.4_rc1",
      "=dev-libs/glib-2*",
      "!=net-fs/samba-2*",
      # "Atom Slots"
      "x11-libs/qt:3",
      "~x11-libs/qt-3.3.8:3",
      ">=x11-libs/qt-3.3.8:3",
      "=x11-libs/qt-3.3*:3",
      # "Sub Slots"
      "dev-libs/icu:0/0",
      "dev-libs/icu:0/49",
      "dev-lang/perl:0/5.12",
      "dev-libs/glib:2/2.30",
      # "Atom Slot Operators"
      "dev-libs/icu:*",
      "dev-lang/perl:*",
      "dev-libs/glib:*",
      "dev-libs/icu:=",
      "dev-lang/perl:=",
      "dev-libs/glib:=",
      "dev-libs/icu:0=",
      "dev-lang/perl:0=",
      "dev-libs/glib:2=",
      "dev-libs/icu:0/0=",
      "dev-libs/icu:0/49=",
      "dev-lang/perl:0/5.12=",
      "dev-libs/glib:2/2.30=",
      # "Atom USE defaults"
      "media-video/ffmpeg[threads(+)]",
      "media-video/ffmpeg[-threads(-)]",
      # "Dynamic Dependencies" -- not supported



      "cat/pkg-a2",
      "cat/pkg-2a",
      "c_at/p-_k_-g-2-a++",
      (
         "cat/pkg", {
            'package.category.name': 'cat', 'package.name': 'pkg'
         }
      ),
      (
         ">dev-lang/R-5.0_alpha1_beta2-r2", {
            'package.category.name': 'dev-lang', 'package.name': 'R',
            'version': '5.0', '!revision': '2', 'revision': 2,
            'version_suffix': 'alpha1_beta2',
         }
      ),
      (
         "!!=cat/p-k-g-2.5.4*:4.0/3.1=[a,-b,c(+),-d(-)]", {
            'package.category.name': 'cat', 'package.name': 'p-k-g',
            'prefix'            : DependencyAtom.ATOM_PREFIX_BLOCKBLOCK,
            'prefix_operator'   : DependencyAtom.ATOM_PREFIX_OP_EQ,
            'version'           : '2.5.4',
            'version_suffix'    : None,
            'revision'          : None,
            'postfix'           : DependencyAtom.ATOM_POSTFIX_V_ANY,
            'slot'              : '4.0',
            'subslot'           : '3.1',
            'slot_operator'     : DependencyAtom.ATOM_SLOTOP_REBUILD,
            'useflags'          : 'a,-b,c(+),-d(-)',
         }
      ),
      (
         "<cat/pkg-2.5.4_p0_p1_p2_p3_p4_alpha134:4.0/3.1=[a,-b,c(+),-d(-)]", {
            'package.category.name': 'cat', 'package.name': 'pkg',
            'prefix'            : DependencyAtom.ATOM_PREFIX_NONE,
            'prefix_operator'   : DependencyAtom.ATOM_PREFIX_OP_LT,
            'version'           : '2.5.4',
            'version_suffix'    : 'p0_p1_p2_p3_p4_alpha134',
            'revision'          : None,
            'postfix'           : DependencyAtom.ATOM_POSTFIX_NONE,
            'slot'              : '4.0',
            'subslot'           : '3.1',
            'slot_operator'     : DependencyAtom.ATOM_SLOTOP_REBUILD,
            'useflags'          : 'a,-b,c(+),-d(-)',
         }
      ),
   )

   def compare_obj_to_attr_dict ( self, atom_str, obj, attr_dict ):
      if not attr_dict:
         return

      for attr_name, expected_value in attr_dict.items():
         if attr_name[0] == '~':
            self.assertRaises ( AttributeError, get_nested_attr, obj, attr_name[1:] )
            continue

         elif attr_name[0] == '!':
            cmp_funcs = ( self.assertNotEqual, self.assertIsNot )
            attr_name = attr_name[1:]

         else:
            cmp_funcs = ( self.assertEqual, self.assertIs )

         attr = get_nested_attr ( obj, attr_name )

         if any ( expected_value is k for k in ( None, True, False ) ):
            cmp_func = cmp_funcs [1]
         else:
            cmp_func = cmp_funcs [0]

         if cmp_func:
            cmp_func (
               attr, expected_value,
               "{s!r}: {func.__name__}, {attr_name!s}".format (
                  func=cmp_func,
                  s=atom_str, attr_name=attr_name
               )
            )
         # -- end if
      # -- end for
   # --- end of compare_obj_to_attr_dict (...) ---

   def test_good_str_construction ( self ):
      for item in self.__class__.GOOD_DEP_ATOMS:
         if isinstance ( item, str ):
            atom_str           = item
            expected_attr_dict = None
         else:
            atom_str           = item[0]
            expected_attr_dict = item[1]
         # -- end if

         obj = dep_atom_from_str ( atom_str )
         self.compare_obj_to_attr_dict ( atom_str, obj, expected_attr_dict )
   # --- end of test_good_str_construction (...) ---

   def test_bad_str_construction ( self ):
      for item in self.__class__.BAD_DEP_ATOMS:
         if isinstance ( item, str ):
            atom_str           = item
            expected_attr_dict = None
         else:
            assert len(item) == 2
            atom_str           = item[0]
            expected_attr_dict = item[1]
         # -- end if

         if expected_attr_dict is None:
            try:
               self.assertRaises ( ValueError, dep_atom_from_str, atom_str )
            except AssertionError:
               print(atom_str)
               raise
         else:
            obj = dep_atom_from_str ( atom_str )
            # ?
            self.compare_obj_to_attr_dict ( atom_str, obj, expected_attr_dict )
   # --- end of test_bad_str_construction (...) ---

# --- end of DependencyAtomTests ---
