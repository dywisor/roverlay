# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import print_function

import random

import roverlay.interface.depres

import tests.base
import tests.interface
import tests.static.depres

from tests.static.depres import DEPRES_DATA, DEPRES_RULES, DEPRES_INCLUDE



def suite():
   return tests.base.make_testsuite ( DepresTestCase )


as_iterable = lambda s : ( s, ) if isinstance ( s, str ) else s

class DepresTestCase ( tests.interface.RoverlayInterfaceTestCase ):

   TESTSUITE = [
      'sanity_checks',
      'visualize',
      'depres_static', 'depres_static_randomized',
      'load_rules',
   ]

   DEPRES_INTERFACE = None

   @classmethod
   def setUpClass ( cls ):
      super ( DepresTestCase, cls ).setUpClass()
      cls.ROOT_INTERFACE.register_interface (
         "depres", roverlay.interface.depres.DepresInterface, force=True
      )
      cls.DEPRES_INTERFACE = cls.ROOT_INTERFACE.spawn_interface ( "depres" )
      cls.DEPRES_INTERFACE.set_greedy ( False )
      # for now, tuples are expected when running tests
      #  (AssertEquals ( <expected result>, <result> )
      #
      cls.DEPRES_INTERFACE.want_tuple = True
   # --- end of setUpClass (...) ---

   def setUp ( self ):
      #ref
      self.depres = self.__class__.DEPRES_INTERFACE
      self.depres.get_new_pool()
   # --- end of setUp (...) ---

   def tearDown ( self ):
      self.depres.discard_pool()
      self.depres.discard_empty_pools()
      self.depres.update()
   # --- end of tearDown (...) ---

   def do_depres_test ( self, rule_names, test_data ):
      unpacked = lambda T: \
         ( "" if T[0] is None else T[0] ) if T and len ( T ) == 1 else T

      self.depres.compile_rules()
      self.tearDown()
      self.depres.get_new_pool()
      for rule_name in rule_names:
         self.assertTrue (
            self.depres.add_rule_list ( DEPRES_RULES [rule_name] )
         )
      self.assertTrue ( self.depres.compile_rules() )

      for depstr, t_expected_result in test_data:
         expected_result = unpacked ( t_expected_result )
         result          = unpacked ( self.depres.resolve ( depstr ) )


         self.assertEquals (
            result, expected_result,
            "{!r} should be resolved as {!r} and not {!r}".format (
               depstr, expected_result, result
            )
         )
   # --- end of do_depres_test (...) ---

   def do_randomized_depres_test (
      self, rule_names, test_data, allow_modify=False
   ):
      if allow_modify and isinstance ( test_data, list ):
         rand_list = test_data
      else:
         rand_list = list ( test_data )
      random.shuffle ( rand_list )
      return self.do_depres_test ( rule_names, rand_list )
   # --- end of do_randomized_depres_test (...) ---

   def get_depres_include ( self, dataset_name ):
      if dataset_name in DEPRES_INCLUDE:
         return as_iterable ( DEPRES_INCLUDE [dataset_name] )
      else:
         return ( dataset_name, )
   # --- end of get_depres_include (...) ---

   def test_visualize ( self ):
      for name, ruleset in DEPRES_RULES.items():
         self.depres.compile_rules()
         self.tearDown()
         self.depres.get_new_pool()

         self.assertTrue ( self.depres.add_rule_list ( ruleset ) )
         self.assertTrue ( self.depres.compile_rules() )

         vis = self.depres.visualize_pool()
         self.assertIsInstance ( vis, str )
         self.assertEquals (
            bool ( not self.depres.get_pool().empty() ), bool ( vis )
         )
   # --- end of test_visualize (...) ---

   def test_sanity_checks ( self ):
      for dataset_name in DEPRES_DATA.keys():
         if dataset_name in DEPRES_INCLUDE:
            ruleset_list = as_iterable ( DEPRES_INCLUDE [dataset_name] )
         else:
            ruleset_list = ( dataset_name, )

         for ruleset_name in ruleset_list:
            self.assertIn (
               ruleset_name, DEPRES_RULES,
               "missing ruleset {!r} for depres test {!r}".format (
                  ruleset_name, dataset_name
               )
            )
   # --- end of test_sanity_checks (...) ---

   def test_depres_static ( self ):
      for name, test_data in DEPRES_DATA.items():
         self.do_depres_test (
            self.get_depres_include ( name ),
            DEPRES_DATA [test_data] if isinstance ( test_data, str )
               else test_data
         )
   # --- end of test_depres_static (...) ---

   def test_depres_static_randomized ( self ):
      data_keys = list ( DEPRES_DATA.keys() )
      random.shuffle ( data_keys )

      for name in data_keys:
         test_data = DEPRES_DATA [name]
         self.do_randomized_depres_test (
            self.get_depres_include ( name ),
            DEPRES_DATA [test_data] if isinstance ( test_data, str )
               else test_data
         )
   # --- end of test_depres_static_randomized (...) ---

   def test_load_rules ( self ):
      self.depres.discard_all_pools()
      if self.CONFIG.get ( "DEPRES.simple_rules.files", None ):
         self.depres.load_rules_from_config ( ignore_missing=True )
         self.depres.discard_all_pools()
      else:
         self.skipTest ( "No rule files configured." )
   # --- end of test_load_rules (...) ---
