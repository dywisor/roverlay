# R overlay -- ebuild creation
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""ebuild creation

This module puts all parts of the ebuild package together and provides
easy-to-use ebuild creation access.
"""

__all__ = [ 'EbuildCreation', ]

import logging

from roverlay.ebuild import depres, ebuilder, evars

LOGGER = logging.getLogger ( 'EbuildCreation' )

# USE_FULL_DESCRIPTION
#  * True: use Title and Description for ebuild's DESCRIPTION variable
#  * else: use Title _or_ Description
USE_FULL_DESCRIPTION = False

# FALLBACK_DESCRIPTION is used as DESCRIPTION= value if not empty and
#  the R package has no Title/Description
FALLBACK_DESCRIPTION = "<none>"

class EbuildCreation ( object ):
   """Used to create an ebuild using DESCRIPTION data."""

   def __init__ ( self, package_info, err_queue, depres_channel_spawner=None ):
      """Initializes the creation of an ebuild.

      arguments:
      * package_info           --
      * depres_channel_spawner -- function that returns a communication
                                   channel to the resolver
      """
      self.package_info = package_info
      self.package_info.set_readonly()

      self.logger = LOGGER.getChild ( package_info ['name'] )

      # > 0 busy/working; 0 == done,success; < 0 done,fail
      self.status  = 1
      # function reference that points to the next task
      self._resume = self._run_prepare
      self.paused  = False

      self.depres_channel_spawner = depres_channel_spawner

      self.err_queue = err_queue

      #self.use_expand_flag_names = None
   # --- end of __init__ (...) ---

   def done    ( self ) : return self.status  < 1
   def busy    ( self ) : return self.status  > 0
   def success ( self ) : return self.status == 0
   def fail    ( self ) : return self.status  < 0

   def run ( self ):
      """Creates an ebuild and stores it directly in the assigned PackageInfo
      instance. Returns None (implicit)."""
      # FIXME: totally wrong __doc__

      if self.status < 1:
         raise Exception ( "Cannot run again." )

      try:
         self.paused = False
         while self.status > 0 and not self.paused:
            resume_func  = self._resume
            self._resume = None
            if not resume_func():
               s = self.status
               if s > 0:
                  s *= (-1)
                  self.status = s
               # else already set by _resume()
               self.logger.info (
                  'Cannot create an ebuild for this package '
                  '(status={:d}).'.format ( s )
               )

         if self.status == 0:
            self.logger.debug ( "Ebuild is ready." )
            return True
         else:
            return False
      except:
         # set status to "fail due to exception"
         self.status = -10
         raise
   # --- end of run (...) ---

   def _get_ebuild_description ( self, desc ):
      """Creates a DESCRIPTION variable."""
      # FIXME: could be moved to _run_create()

      description = None
      if USE_FULL_DESCRIPTION:
         # use Title and Description for DESCRIPTION=
         if 'Title' in desc:
            description = desc ['Title']

         if 'Description' in desc:
            if description:
               description += '// ' + desc ['Description']
            else:
               description = desc ['Description']

      else:
         # use either Title or Description for DESCRIPTION=
         # (Title preferred 'cause it should be shorter)
         if 'Title' in desc:
            description = desc ['Title']

         if not description and 'Description' in desc:
            description = desc ['Description']


      if description:
         return evars.DESCRIPTION ( description )
      elif FALLBACK_DESCRIPTION:
         return evars.DESCRIPTION ( FALLBACK_DESCRIPTION )
      else:
         return None
   # --- end of _get_ebuild_description (...) ---

   def _run_prepare ( self ):
      self.status = 2

      p_info = self.package_info

      # read DESCRIPTION data
      p_info.update_now ( make_desc_data=True )
      if p_info ['desc_data'] is None:
         self.logger.warning (
            'desc empty - cannot create an ebuild for this package.'
         )
         return False
      else:
         # resolve dependencies
         dep_resolution = depres.EbuildDepRes (
            self.package_info, self.logger,
            run_now=True, depres_channel_spawner=self.depres_channel_spawner,
            err_queue=self.err_queue
         )
         if dep_resolution.success():
            self.dep_resolution = dep_resolution

            self.selfdeps = frozenset (
               dep_resolution.get_mandatory_selfdeps()
            )
            self.optional_selfdeps = frozenset (
               dep_resolution.get_optional_selfdeps()
            )

            if (
               p_info.init_selfdep_validate ( self.selfdeps )
               or self.optional_selfdeps
            ):
               # selfdep reduction is required before ebuild creation can
               # proceed
               self.paused  = True
               self._resume = self._run_create
               self.logger.debug ( "paused - waiting for selfdep validation" )
               return True
            else:
               return self._run_create()
         else:
            return False
   # --- end of _run_prepare (...) ---

   def _run_create ( self ):
      self.status    = 3
      p_info         = self.package_info
      dep_resolution = self.dep_resolution
      desc           = self.package_info ['desc_data']

      if p_info.end_selfdep_validate():
         ebuild      = ebuilder.Ebuilder()
         evars_dep   = dep_resolution.get_evars()
         evars_extra = p_info.get_evars()

         if evars_extra:
            ebuild.use ( *evars_extra )

            #evars_overridden = tuple ( ebuild.get_names() )
            # if k.name not in evars_overridden: ebuild.use ( k )
         #else:
         #   ...

         # add *DEPEND to the ebuild
         ebuild.use_list ( evars_dep )

         # IUSE
         if dep_resolution.has_suggests:
            rsuggests = ebuild.get ( 'R_SUGGESTS' )
            self.use_expand_flag_names = set ( rsuggests.get_flag_names() )
            ebuild.use ( evars.IUSE ( sorted ( rsuggests.get_flags() ) ) )
#         else:
#            ebuild.use ( evars.IUSE() )

         # DESCRIPTION
         ebuild.use ( self._get_ebuild_description ( desc ) )

         # SRC_URI
         ebuild.use ( evars.SRC_URI (
            src_uri      = p_info ['SRC_URI'],
            src_uri_dest = p_info.get ( "src_uri_dest", do_fallback=True )
         ) )

         # LICENSE (optional)
         license_str = desc.get ( 'License' )
         if license_str:
            ebuild.use ( evars.LICENSE ( license_str ) )

         # HOMEPAGE (optional)
         homepage_str = desc.get ( 'Homepage' )
         if homepage_str:
            ebuild.use ( evars.HOMEPAGE ( homepage_str ) )


         #ebuild_text = ebuild.to_str()
         ## FIXME: debug rstrip()
         ebuild_text = ebuild.to_str().rstrip()

         p_info.update_now (
            ebuild=ebuild_text,
            has_suggests=dep_resolution.has_suggests,
         )

         self.status = 0
         return True
      elif (
         hasattr ( self, 'selfdeps' ) or hasattr ( self, 'optional_selfdeps' )
      ):
         self.logger.debug ( "selfdep validation failed." )
         if hasattr ( self, 'selfdeps' ):
            for selfdep in self.selfdeps:
               self.logger.debug (
                  "selfdep {}: {}".format (
                     selfdep.dep, "OK" if selfdep.is_valid() else "FAIL"
                  )
               )
         if hasattr ( self, 'optional_selfdeps' ):
            for selfdep in self.optional_selfdeps:
               self.logger.debug (
                  "optional selfdep {}: {}".format (
                     selfdep.dep, "OK" if selfdep.is_valid() else "FAIL"
                  )
               )


         return False
      else:
         raise AssertionError (
            "selfdep validation must not fail if no selfdeps are present!"
         )
   # --- end of _run_create (...) ---

# --- end of EbuildCreation ---
