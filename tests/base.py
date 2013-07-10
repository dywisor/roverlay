# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import unittest

import roverlay
import roverlay.config.static



class BasicRoverlayTestCase ( unittest.TestCase ):
   CONFIG_FILE = "R-overlay.conf.tests"
   CONFIG      = None

   @classmethod
   def load_config ( cls ):
      # does nothing if already initialized
      if cls.CONFIG is None:
         roverlay.setup_initial_logger()
         cls.CONFIG = roverlay.load_config_file (
            cls.CONFIG_FILE, setup_logger=False
         )
   # --- end of load_config (...) ---

#   @classmethod
#   def setUpClass ( cls ):
#      pass

#   @classmethod
#   def tearDownClass ( cls ):
#      pass

class RoverlayTestCase ( BasicRoverlayTestCase ):

   @classmethod
   def setUpClass ( cls ):
      super ( RoverlayTestCase, cls ).setUpClass()
      cls.load_config()


def make_testsuite ( testcase_cls ):
   return unittest.TestSuite (
      map ( lambda s: testcase_cls ( "test_" + s ), testcase_cls.TESTSUITE )
   )
# --- end of make_testsuite (...) ---
