# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import tests.base

import roverlay.interface.root

class RoverlayInterfaceTestCase ( tests.base.RoverlayTestCase ):

   ROOT_INTERFACE = None

   @classmethod
   def setUpClass ( cls ):
      super ( RoverlayInterfaceTestCase, cls ).setUpClass()
      if cls.ROOT_INTERFACE is None:
         cls.ROOT_INTERFACE = roverlay.interface.root.RootInterface (
            config=cls.CONFIG
         )

   @classmethod
   def tearDownClass ( cls ):
      super ( RoverlayInterfaceTestCase, cls ).tearDownClass()
      if cls.ROOT_INTERFACE is not None:
         cls.ROOT_INTERFACE.close()
