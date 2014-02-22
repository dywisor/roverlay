# R overlay -- util, progressbar
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import division

import abc
import sys

import roverlay.util.objects


class AbstractProgressBarBase ( roverlay.util.objects.AbstractObject ):
   """Abstract base class for progress bars."""

   @abc.abstractmethod
   def setup ( self, *args, **kwargs ):
      """Initialization code for __init__() and reset().

      Returns: None

      arguments:
      * *args, **kwargs -- progress bar data
      """
      pass
   # --- end of setup (...) ---

   def reset ( self, *args, **kwargs ):
      """Finalizes the current progress bar and resets it afterwards.

      Returns: None

      arguments:
      * *args, **kwargs -- passed to setup()
      """
      self.print_newline()
      self.setup ( *args, **kwargs )
   # --- end of reset (...) ---

   def __init__ ( self, *args, **kwargs ):
      """Initializes a progress bar instance by calling its setup() method.

      arguments:
      * *args, **kwargs -- passed to setup()
      """
      super ( AbstractProgressBarBase, self ).__init__()
      self.setup ( *args, **kwargs )
   # --- end of __init__ (...) ---

   @abc.abstractmethod
   def write ( self, message ):
      """(Over-)writes the progress bar, using the given message.

      Note: message should not contain newline chars.

      Returns: None

      arguments:
      * message --
      """
      raise NotImplementedError()
   # --- end of write (...) ---

   @abc.abstractmethod
   def print_newline ( self ):
      """
      Finalizes the current progress bar, usually by printing a newline char.

      Returns: None
      """
      raise NotImplementedError()
   # --- end of print_newline (...) ---

   @abc.abstractmethod
   def update ( self, *args, **kwargs ):
      """Updates the progress bar using the given data.

      Returns: None

      arguments:
      * *args, **kwargs -- not specified by this class
      """
      raise NotImplementedError()
   # --- end of update (...) ---

   def __enter__ ( self ):
      # "with"-statement, setup code
      return self

   def __exit__ ( self, _type, value, traceback ):
      # "with"-statement, teardown code
      self.print_newline()

# --- end of AbstractProgressBarBase ---


class AbstractProgressBar ( AbstractProgressBarBase ):
   """
   Abstract base class for progress bars that write to a stream, e.g. stdout.
   """

   CARRIAGE_RET_CHR = chr(13)
   #BACKSPACE_CHR    = chr(8)

   def setup ( self, stream=None ):
      self.stream = ( sys.stdout if stream is None else stream )
   # --- end of __init__ (...) ---

   def write ( self, message ):
      self.stream.write ( self.CARRIAGE_RET_CHR + message )
      self.stream.flush()
   # --- end of write (...) ---

   def print_newline ( self ):
      self.stream.write ( "\n" )
      self.stream.flush()
   # --- end of print_newline (...) ---

# --- end of AbstractProgressBar ---


class AbstractPercentageProgressBar ( AbstractProgressBar ):
   """Base class for displaying progress as percentage 0.00%..100.00%."""
   # not a real progress bar, just a progress indicator

   # str for formatting the percentage
   #  by default, reserve space for 7 chars ("ddd.dd%")
   #  might be set by derived classes and/or instances
   PERCENTAGE_FMT = "{:>7.2%}"

   def setup ( self, message_header=None, stream=None ):
      super ( AbstractPercentageProgressBar, self ).setup ( stream=stream )
      self.message_header = message_header
   # --- end of setup (...) ---

   @abc.abstractmethod
   def get_percentage ( self, *args, **kwargs ):
      """Returns a float or int expressing a percentage.

      Any value < 0 is interpreted as "UNKNOWN".

      arguments:
      * *args, **kwargs -- progress information (from update())
      """
      raise NotImplementedError()
   # --- end of get_percentage (...) ---

   def _update ( self, percentage ):
      if self.message_header:
         message = str(self.message_header) + " "
      else:
         message = ""

      if percentage < 0:
         message += "UNKNOWN"
      else:
         message += self.PERCENTAGE_FMT.format ( percentage )

      self.write ( message )
   # --- end of _update (...) ---

   def update ( self, *args, **kwargs ):
      self._update ( self.get_percentage ( *args, **kwargs ) )
   # --- end of update (...) ---

# --- end of AbstractPercentageProgressBar ---


class NullProgressBar ( AbstractProgressBarBase ):
   """A progress bar that discards any information."""

   def setup ( self, *args, **kwargs ):
      pass

   def write ( self, *args, **kwargs ):
      pass

   def print_newline ( self, *args, **kwargs ):
      pass

   def update ( self, *args, **kwargs ):
      pass

# --- end of NullProgressBar ---


class DownloadProgressBar ( AbstractPercentageProgressBar ):
   """A progress bar for file transfers,
   expressing a percentage "bytes transferred / total size".

   Note:
    update() shouldn't be called too often as writing to console is rather slow
   """

   def setup ( self, filename=None, filesize=None, stream=None ):
      super ( DownloadProgressBar, self ).setup (
         message_header = (
            ( "Fetching " + str(filename) ) if filename else None
         ),
         stream = stream
      )
      self.filesize = filesize
   # --- end of setup (...) ---

   def get_percentage ( self, current_filesize ):
      return ( current_filesize / self.filesize ) if self.filesize else -1.0
   # --- end of get_percentage (...) ---

# --- end of DownloadProgressBar ---
