# R overlay -- abstract package rule generators, addition control
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import absolute_import

# TODO: cleanup:
#   BitmaskMapCreator / AdditionControlPackageRuleGenerator naming
#   ...
#


import abc
import collections
import fnmatch
import re



import roverlay.packagerules.generators.abstract.addition_control

import roverlay.packagerules.abstract.acceptors
import roverlay.packagerules.acceptors.stringmatch
import roverlay.packagerules.acceptors.util

import roverlay.overlay.abccontrol
from roverlay.overlay.abccontrol import AdditionControlResult


from roverlay.packagerules.abstract.acceptors import Acceptor_AND

from roverlay.packagerules.acceptors.stringmatch import (
   StringAcceptor, ExactRegexAcceptor,
)

from roverlay.packagerules.acceptors.util import (
   get_category, get_ebuild_name, get_ebuild_version_tuple,
)

import roverlay.util.fileio
import roverlay.util.namespace

import roverlay.util.portage_regex.default
import roverlay.util.portage_regex.wildcard
from roverlay.util.portage_regex.default  import RE_PACKAGE_EBUILD_FILE
from roverlay.util.portage_regex.wildcard import (
   RE_WILDCARD_PACKAGE, RE_WILDCARD_CATEGORY
)




class TokenValueError ( ValueError ):
   pass

class InvalidTokenInputString ( TokenValueError ):
   pass

class TokenItemNotSupported ( TokenValueError ):
   pass


def _read_list_file (
   filepath,
   _read_text_file=roverlay.util.fileio.read_text_file
):
   def strip_line ( s ):
      return s.strip()

   if filepath:
      for line in _read_text_file ( filepath, preparse=strip_line ):
         # skip line if <>
         yield line
# --- end of _read_list_file (...) ---


class AdditionControlPackageRuleGenerator (
   roverlay.packagerules.generators.abstract.addition_control.\
      AbstractAdditionControlPackageRuleGenerator
):

   #TOKEN_ITEM_IS_SPECIAL = 0 ## implicit
   TOKEN_ITEM_IS_STR      = 1
   TOKEN_ITEM_IS_REGEX    = 2

   TokenItemTuple = collections.namedtuple (
      "TokenItemTuple", "item_type value"
   )

   # PackageToken: tuple ( None|$PN, None|$PV, None|$PR )
   #  (revision not implemented because it cannot be matched in package rules
   #   -- always 0)
   #  condition: not all ( item is None for item in <PackageToken> )
   #              and all not-None items must evaluate to True
   #             <=> any ( <PackageToken> )
   #
   PackageToken  = collections.namedtuple ( 'PackageToken', 'name version' )

   # CategoryToken: tuple ( $CATEGORY )
   #  same conditions as for PackageToken apply,
   #   which effectively means that $CATEGORY must a non-empty str
   #
   CategoryToken = collections.namedtuple ( 'CategoryToken', 'name' )

   DEFAULT_CATEGORY_TOKEN = CategoryToken (
      TokenItemTuple (
         TOKEN_ITEM_IS_STR,
         roverlay.packagerules.acceptors.util.DEFAULT_CATEGORY_REPLACEMENT
      )
   )


   def create_token_item_from_str ( self, s ):
      get_obj = self.namespace.get_object_v

      if not s:
         return None

      elif any ( char in "?*" for char in s ):
         s_stripped = s.strip("*")
         if not s_stripped or (
            s_stripped == "?" and s_stripped != s
         ):
            # "****", "?*", "*?", ... => match all
            return True

         else:
            return get_obj (
               self.__class__.TokenItemTuple,
               (
                  self.__class__.TOKEN_ITEM_IS_REGEX,
                  get_obj ( fnmatch.translate, ( s, ) )
               )
            )

      else:
         return get_obj (
            self.__class__.TokenItemTuple,
            ( self.__class__.TOKEN_ITEM_IS_STR, s )
         )
   # --- end of create_token_item_from_str (...) ---

   def validate_token ( self, package_token ):
      all_none       = True
      any_nonspecial = False

      for item in package_token:
         if item:
            all_none = False
            if item is not True:
               any_nonspecial = True
      # -- end for

      if all_none:
         assert not any_nonspecial
         return None
      elif any_nonspecial:
         return package_token
      else:
         # FIXME: remove assert
         assert all ( item in ( True, None ) for item in package_token ), package_token
         return True
   # --- end of validate_token (...) ---

   def _create_package_token ( self, name_str, version_str, revision_str ):
      if revision_str:
         raise TokenItemNotSupported (
            "revision {!s}".format ( revision_str )
         )

      package_token = self.namespace.get_object_v (
         self.__class__.PackageToken,
         (
            self.create_token_item_from_str ( name_str ),
            self.create_token_item_from_str ( version_str ),
##          self.create_token_item_from_str ( revision_str ),
         )
      )

      return self.validate_token ( package_token )
   # --- end of _create_package_token (...) ---

   def _create_category_token ( self, category_str ):
      if category_str == self.default_category:
         # validate_token() not necessary (assumption)
         return self.DEFAULT_CATEGORY_TOKEN
      else:
         category_token = self.namespace.get_object_v (
            self.__class__.CategoryToken,
            (
               self.create_token_item_from_str ( category_str ),
            )
         )

      return self.validate_token ( category_token )
   # --- end of _create_category_token (...) ---

   def create_category_token ( self, input_str ):
      # input_str doesn't need much parsing,
      #  not using RE_WILDCARD_CATEGORY for now
##      re_match = RE_WILDCARD_CATEGORY.match ( input_str )
##      if not re_match:
##         raise InvalidTokenInputString ( input_str )
##
##      match_vars = re_match.groupdict()
##
##      if not match_vars ['CATEGORY']:
##         raise InvalidTokenInputString ( input_str )

      if not input_str:
         raise InvalidTokenInputString ( input_str )
      else:
         return self._create_category_token ( input_str )
   # --- end of create_category_token (...) ---


   def create_token (
      self, input_str, with_category=True, package_regex=RE_WILDCARD_PACKAGE
   ):
      re_match = package_regex.match ( input_str )

      if not re_match:
         raise InvalidTokenInputString (
            "{!s}: not matched by regex".format ( input_str )
         )

      match_vars = re_match.groupdict()


      package_token = self._create_package_token (
         match_vars ['PN'], match_vars ['PV'], match_vars ['revision']
      )

      if not package_token:
         raise InvalidTokenInputString ( input_str )


      if with_category:
         category_token = self._create_category_token (
            match_vars ['CATEGORY']
         )

         if not category_token:
            if match_vars ['CATEGORY']:
               raise InvalidTokenInputString (
                  "{!s}: invalid category str {!s}".format (
                     input_str, match_vars ['CATEGORY']
                  )
               )
            # --

            # => match-all
            category_token = True
         # -- end if

         return ( category_token, package_token )

      elif match_vars ['CATEGORY']:
         raise InvalidTokenInputString (
            "{!s}: must not contain CATEGORY".format ( input_str )
         )
      else:
         return package_token
   # --- end of create_token (...) ---

   def create_token_for_ebuild_filepath ( self, efile ):
      return self.create_token (
         efile, with_category=True, package_regex=RE_PACKAGE_EBUILD_FILE
      )
   # --- end of create_token_for_ebuild_filepath (...) ---

   def create_package_token ( self, input_str ):
      return self.create_token ( input_str, with_category=False )
   # --- end of create_package_token (...) ---


   def __init__ ( self, default_category ):
      super ( AdditionControlPackageRuleGenerator, self ).__init__()
      self.namespace        = roverlay.util.namespace.SimpleNamespace()
      self.default_category = default_category
   # --- end of __init__ (...) ---

   def clear_object_cache ( self ):
      if self.namespace:
         self.namespace.zap(True)
   # --- end of clear_object_cache (...) ---

   def __del__ ( self ):
      try:
         self.clear_object_cache()
      except NotImplementedError:
         pass

   def token_item_to_acceptor ( self, token_item, value_getter, priority ):
      if token_item in ( True, None ):
         # should be catched elsewhere
         return None

      elif token_item.item_type == self.__class__.TOKEN_ITEM_IS_STR:
         acceptor_cls = StringAcceptor


      elif token_item.item_type == self.__class__.TOKEN_ITEM_IS_REGEX:
         acceptor_cls = ExactRegexAcceptor

      else:
         raise AssertionError (
            "invalid token item type: {!s}".format ( token_item.item_type )
         )
      # -- end if

      return self.namespace.get_object_v (
         acceptor_cls, ( priority, value_getter, token_item.value )
      )
   # --- end of token_item_to_acceptor (...) ---

   def category_token_to_acceptor ( self, category_token, priority ):
      assert category_token and category_token is not True

      return self.token_item_to_acceptor (
         category_token.name, get_category, priority
      )
   # --- end of category_token_to_acceptor (...) ---

   def package_token_to_acceptor ( self, package_token, priority ):
      assert package_token and package_token is not True

      relevant_items = [
         item_and_getter for item_and_getter in zip (
            package_token,
            (
               get_ebuild_name,
               get_ebuild_version_tuple
            )
         ) if item_and_getter[0] and item_and_getter[0] is not True
      ]

      if not relevant_items:
         raise TokenValueError ( package_token )

      elif len(relevant_items) == 1:
         return self.token_item_to_acceptor (
            relevant_items[0][0], relevant_items[0][1], priority
         )
      else:
         sub_acceptors = [
            self.token_item_to_acceptor ( item, getter, 0 )
            for item, getter in relevant_items
         ]

         combined_acceptor = Acceptor_AND ( priority=priority )
         for sub_acceptor in sub_acceptors:
            combined_acceptor.add_acceptor ( sub_acceptor )

         return combined_acceptor
   # --- end of package_token_to_acceptor (...) ---

# --- end of AdditionControlPackageRuleGenerator ---


class BitmaskMapCreator ( object ):
   """creates a "bitmask" => "acceptor chain" map"""

   def __init__ ( self, rule_generator ):
      super ( BitmaskMapCreator, self ).__init__()
      self.rule_generator = rule_generator
      self.data           = rule_generator.create_new_bitmask_map()

   def get_bitmask_map ( self ):
      return self.data

   def get_bitmask_map_copy ( self ):
      return self.data.copy()

   def _insert_package ( self, bitmask_arg, package_str, package_regex ):
      category_token, package_token = self.rule_generator.create_token (
         package_str, with_category=True, package_regex=package_regex
      )

      if isinstance ( bitmask_arg, str ):
         bitmask_int = AdditionControlResult.convert_str ( bitmask_arg )
      else:
         bitmask_int = int ( bitmask_arg )


      try:
         cat_entry = self.data [category_token]
      except KeyError:
         self.data [category_token] = { package_token: bitmask_int }
      else:
         try:
            pkg_entry = cat_entry [package_token]
         except KeyError:
            cat_entry [package_token] = bitmask_int
         else:
            pkg_entry |= bitmask_int
         # -- end try <package entry exists>
      # -- end try <category entry exists>
   # --- end of _insert_package (...) ---

   def _split_bitmask_line ( self, line, default_bitmask ):
      # str<[bitmask,]arg> => ( bitmask||default_bitmask, arg )
      args = line.split ( None, 1 )

      if len(args) == 2:
         # convert bitmask str now
         return ( AdditionControlResult.convert_str(args[0]), args[1] )

      elif default_bitmask or (
         default_bitmask == 0 and default_bitmask is not False
         # ? or default_bitmask is 0
      ):
         return ( default_bitmask, args[0] )

      else:
         raise ValueError ( line )
   # --- end of _split_bitmask_line (...) ---

   def _insert_packages_v (
      self, bitmask, arglist, package_regex, extended_format
   ):
      insert_package = self._insert_package

      if extended_format:
         split_bitmask_line = self._split_bitmask_line

         for arg in arglist:
            call_args = split_bitmask_line ( arg, bitmask )
            insert_package ( call_args[0], call_args[1], package_regex )

      else:
         for arg in arglist:
            insert_package ( bitmask, arg, package_regex )
   # --- end of _insert_packages_v (...) ---

   def insert_packages_v ( self, bitmask, packages, extended_format=False ):
      self._insert_packages_v (
         bitmask, packages, RE_WILDCARD_PACKAGE, extended_format
      )
   # --- end of insert_packages_v (...) ---

   def insert_package ( self, bitmask, package, *args, **kwargs ):
      self.insert_packages_v ( bitmask, ( package, ), *args, **kwargs )

   def insert_packages ( self, bitmask, *packages, **kwargs ):
      self.insert_packages_v ( bitmask, packages, **kwargs )

   def insert_ebuild_files_v (
      self, bitmask, ebuild_files, extended_format=False
   ):
      self._insert_packages_v (
         bitmask, ebuild_files, RE_PACKAGE_EBUILD_FILE, extended_format
      )
   # --- end of insert_ebuild_files_v (...) ---

   def insert_ebuild_file ( self, bitmask, ebuild_file, *args, **kwargs ):
      self.insert_ebuild_files_v (
         bitmask, ( ebuild_file, ), *args, **kwargs
      )

   def insert_ebuild_files ( self, bitmask, *ebuild_files, **kwargs ):
      self.insert_ebuild_files_v ( bitmask, ebuild_files, **kwargs )


   def feed ( self,
      bitmask, package_list=None, ebuild_file_list=None,
      extended_format=False
   ):
      if package_list:
         self.insert_packages_v ( bitmask, package_list, extended_format )


      if ebuild_file_list:
         self.insert_ebuild_files_v (
            bitmask, ebuild_file_list, extended_format
         )

   # --- end of feed (...) ---

   def feed_from_file (
      self, bitmask, package_list_file=None, ebuild_list_file=None,
      extended_format=False,
   ):
      # or ebuild_file_list_file

      self.feed (
         bitmask,
         _read_list_file ( package_list_file ),
         _read_list_file ( ebuild_list_file ),
         extended_format = extended_format,
      )
   # --- end of feed_from_file (...) ---

# --- end of BitmaskMapCreator ---



def create_addition_control_package_rule (
   default_category,

   cmdline_package_default              = None,
   cmdline_package_force_deny           = None,
   cmdline_package_deny_replace         = None,
   cmdline_package_force_replace        = None,
   cmdline_package_replace_only         = None,
   cmdline_package_revbump_on_collision = None,

   cmdline_ebuild_default               = None,
   cmdline_ebuild_force_deny            = None,
   cmdline_ebuild_deny_replace          = None,
   cmdline_ebuild_force_replace         = None,
   cmdline_ebuild_replace_only          = None,
   cmdline_ebuild_revbump_on_collision  = None,

   cmdline_package_extended             = None,
   cmdline_ebuild_extended              = None,


   file_package_default                 = None,
   file_package_force_deny              = None,
   file_package_deny_replace            = None,
   file_package_force_replace           = None,
   file_package_replace_only            = None,
   file_package_revbump_on_collision    = None,

   file_ebuild_default                  = None,
   file_ebuild_force_deny               = None,
   file_ebuild_deny_replace             = None,
   file_ebuild_force_replace            = None,
   file_ebuild_replace_only             = None,
   file_ebuild_revbump_on_collision     = None,

   file_package_extended                = None,
   file_ebuild_extended                 = None,
):
   """All-in-one function that takes lists of packages, ebuild paths, list
   files, ... as input, creates a "bitmask" -> "acceptor chain" map and
   converts it into a single, nested package rule object or None.

   *** SLOW ***

   Returns: package rule or None

   Note: the returned has to be prepared manually (rule.prepare()),
         which is usually done by the PackagRules top-level rule

   arguments:
   * default_category         -- name of the default overlay category
                                  Mandatory argument.
   * cmdline_package_<policy> -- list of packages [None]
   * cmdline_ebuild_<policy>  -- list of ebuilds  [None]
   * file_package_<policy>    -- package list file[s] [None]
   * file_ebuild_<policy>     -- ebuild  list file[s] [None]
   * file_package_extended    -- package list file[s] in extended format [None]
   * file_ebuild_extended     -- ebuild  list file[s] in extended format [None]

   Note: file_* parameters support only a single input file, currently.
   """
   argv_locals = locals().copy()
   get_args    = lambda pre, attr_name: (
      argv_locals [pre + '_package_' + attr_name],
      argv_locals [pre + '_ebuild_'  + attr_name]
   )
##   argv_locals = {
##      k: v for locals().items()
##         if ( k.startswith("cmdline_") or k.startswith("file_") )
##   }

   if not default_category:
      raise ValueError ( "no default category given (or empty)." )

   rule_generator    = AdditionControlPackageRuleGenerator ( default_category )
   bitmask_mapgen    = BitmaskMapCreator ( rule_generator )
   feed_bitmask      = bitmask_mapgen.feed
   filefeed_bitmask  = bitmask_mapgen.feed_from_file


   for bitmask, desc in AdditionControlResult.PKG_DESCRIPTION_MAP.items():
      attr_name = desc.replace ( '-', '_' )
      # any() not strictly necessary here

      args = get_args ( "cmdline", attr_name )

      if any ( args ):
         feed_bitmask ( bitmask, args[0], args[1] )


      args = get_args ( "file", attr_name )

      if any ( args ):
         filefeed_bitmask ( bitmask, args[0], args[1] )
   # --

   if cmdline_package_extended or cmdline_ebuild_extended:
      feed_bitmask (
         None, cmdline_package_extended, cmdline_ebuild_extended,
         extended_format=True
      )
   # --

   if file_package_extended or file_ebuild_extended:
      filefeed_bitmask (
         None, file_package_extended, file_ebuild_extended,
         extended_format=True
      )
   # --

   add_control_rule = rule_generator.compile_bitmask_map (
      bitmask_mapgen.get_bitmask_map()
   )

   # not necessary (GC)
   rule_generator.clear_object_cache()
   bitmask_mapgen.data.clear()
   del bitmask_mapgen
   del rule_generator

   return add_control_rule
# --- end of create_addition_control_package_rule (...) ---
