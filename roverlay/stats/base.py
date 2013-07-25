# R overlay -- stats collection, data types
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from . import abstract

class RepoStats ( abstract.RoverlayStats ):

   _MEMBERS = frozenset ({ 'pkg_count', })

   def __init__ ( self ):
      super ( RepoStats, self ).__init__()
      self.pkg_count = abstract.DetailedCounter (
         description="package count"
      )
   # --- end of __init__ (...) ---

   def package_file_found ( self, repo ):
      self.pkg_count.inc ( repo.name )
   # --- end of add_package (...) ---

# --- end of RepoStats ---


class DistmapStats ( abstract.RoverlayStats ):

   _MEMBERS = frozenset ({ 'pkg_count', })

   def __init__ ( self ):
      super ( DistmapStats, self ).__init__()
      self.pkg_count = abstract.DetailedCounter (
         description="distmap package count"
      )
   # --- end of __init__ (...) ---

   def file_added ( self, *origin ):
      self.pkg_count.inc ( *origin )
   # --- end of file_added (...) ---

   def file_removed ( self, *origin ):
      self.pkg_count.dec ( *origin )
   # --- end of file_removed (...) ---

# --- end of DistmapStats ---


class OverlayCreationStats ( abstract.RoverlayStats ):

   #_MEMBERS = frozenset({})

   def __init__ ( self ):
      super ( OverlayCreationStats, self ).__init__()
   # --- end of __init__ (...) ---

   def get_relevant_package_count ( self ):
      print ( "get_relevant_package_count(): method stub" )
      return 0
   # --- end of get_relevant_package_count (...) ---

   def __str__ ( self ):
      return "*** no overlay creation stats available ***"
   # --- end of __str__ (...) ---

# --- end of OverlayCreationStats ---


class OverlayStats ( abstract.RoverlayStats ):

   _MEMBERS = frozenset ({
      'ebuilds_scanned', 'ebuild_count', 'ebuilds_written',
   })

   def __init__ ( self ):
      super ( OverlayStats, self ).__init__()
      # ebuilds_scanned: ebuild count prior to running overlay creation
      self.ebuilds_scanned = abstract.Counter ( "pre" )

      # ebuild count: ebuild count after writing the overlay
      self.ebuild_count    = abstract.Counter ( "post" )

      self.ebuilds_written = abstract.Counter ( "written" )
   # --- end of __init__ (...) ---

# --- end of OverlayStats ---
