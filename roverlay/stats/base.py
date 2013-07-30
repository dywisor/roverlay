# R overlay -- stats collection, data types
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from . import abstract

class RepoStats ( abstract.RoverlayStats ):

   _MEMBERS = ( 'sync_time', 'queue_time', 'pkg_count', )

   def __init__ ( self ):
      super ( RepoStats, self ).__init__()
      self.sync_time  = abstract.TimeStats ( 'sync_time' )
      self.queue_time = abstract.TimeStats ( 'queue_time' )
      self.pkg_count  = abstract.DetailedCounter (
         description="package count"
      )
   # --- end of __init__ (...) ---

   def package_file_found ( self, repo ):
      self.pkg_count.inc ( repo.name )
   # --- end of add_package (...) ---

# --- end of RepoStats ---


class DistmapStats ( abstract.RoverlayStats ):

   _MEMBERS = ( 'pkg_count', )

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


class OverlayCreationWorkerStats ( abstract.RoverlayStats ):

   _MEMBERS = ( 'pkg_processed', 'pkg_fail', 'pkg_success', )

   def __init__ ( self ):
      self.pkg_processed = abstract.Counter ( "processed" )
      self.pkg_fail      = abstract.DetailedCounter ( "fail" )
      self.pkg_success   = abstract.Counter ( "success" )
   # --- end of __init__ (...) ---

# --- end of OverlayCreationWorkerStats ---


class OverlayCreationStats ( OverlayCreationWorkerStats ):

   DESCRIPTION = "overlay creation"

   _MEMBERS = (
      ( 'creation_time', 'pkg_queued', 'pkg_filtered', 'pkg_dropped', )
      + OverlayCreationWorkerStats._MEMBERS
   )

   def __init__ ( self ):
      super ( OverlayCreationStats, self ).__init__()
      self.pkg_queued    = abstract.Counter ( "queued" )
      self.pkg_dropped   = abstract.Counter ( "dropped" )
      self.pkg_filtered  = abstract.Counter ( "filtered" )
      self.creation_time = abstract.TimeStats ( "ebuild creation" )
   # --- end of __init__ (...) ---

   def get_relevant_package_count ( self ):
      return self.pkg_queued
      #return self.pkg_queued - self.pkg_fail.get ( "empty_desc" )
   # --- end of get_relevant_package_count (...) ---

   @classmethod
   def get_new ( cls ):
      return OverlayCreationWorkerStats()
   # --- end of get_new (...) ---

# --- end of OverlayCreationStats ---


class OverlayStats ( abstract.RoverlayStats ):

   DESCRIPTION = "overlay"

   _MEMBERS = (
      'scan_time', 'write_time',
      'ebuilds_scanned', 'ebuild_count', 'revbump_count', 'ebuilds_written',
   )

   def __init__ ( self ):
      super ( OverlayStats, self ).__init__()
      # ebuilds_scanned: ebuild count prior to running overlay creation
      self.ebuilds_scanned = abstract.Counter ( "pre" )

      # ebuild count: ebuild count after writing the overlay
      self.ebuild_count    = abstract.Counter ( "post" )

      self.revbump_count   = abstract.Counter ( "revbumps" )
      self.ebuilds_written = abstract.Counter ( "written" )

      self.write_time      = abstract.TimeStats ( "write_time" )
      self.scan_time       = abstract.TimeStats ( "scan_time" )
   # --- end of __init__ (...) ---

   def set_ebuild_written ( self, p_info ):
      self.ebuilds_written.inc()
      # direct dict access
      if p_info._info.get ( 'rev', 0 ) > 0:
         self.revbump_count.inc()
   # --- end of set_ebuild_written (...) ---

# --- end of OverlayStats ---
