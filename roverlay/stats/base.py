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

# --- end of OverlayCreationStats ---


class OverlayStats ( abstract.RoverlayStats ):

   _MEMBERS = frozenset({ 'ebuild_count', })

   def __init__ ( self ):
      super ( OverlayStats, self ).__init__()
      # ebuild_count counts *physical* ebuilds
      #  number of created ebuilds is part of overlay creation stats
      self.ebuild_count = abstract.DetailedCounter (
         description="ebuild count"
      )
   # --- end of __init__ (...) ---

   def ebuild_added ( self, origin ):
      self.ebuild_count.inc ( origin )
   # --- end of ebuild_added (...) ---

# --- end of OverlayStats ---
