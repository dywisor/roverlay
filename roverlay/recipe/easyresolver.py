# R overlay -- recipe, easyresolver
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""initializes a dependency resolver with listener modules"""

__all__ = [ 'setup', ]

from roverlay                    import config
from roverlay.depres             import listeners
from roverlay.depres.depresolver import DependencyResolver


def setup ( err_queue ):
   """Initializes and returns a dependency resolver.
   Also reads dependency rules and attaches listener modules as configured.

   arguments:
   * err_queue -- error queue for the resolver
   """
   res = DependencyResolver ( err_queue=err_queue )
   # log everything
   res.set_logmask ( -1 )

   srule_files = config.get ( 'DEPRES.simple_rules.files', None )
   if srule_files:
      res.get_reader().read ( srule_files )

   unres_file = config.get ( 'LOG.FILE.unresolvable', None )
   if unres_file:
      unres_listener = listeners.UnresolvableSetFileListener ( unres_file )
      res.add_listener ( unres_listener )
   return res
# --- end of setup (...) ---
