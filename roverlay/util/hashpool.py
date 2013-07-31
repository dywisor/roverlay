# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

try:
   import concurrent.futures
except ImportError:
   sys.stderr.write (
      '!!! concurrent.futures is not available.\n'
      '    Falling back to single-threaded variants.\n\n'
   )
   HAVE_CONCURRENT_FUTURES = False
else:
   HAVE_CONCURRENT_FUTURES = True


import roverlay.digest

def _calculate_hashes ( hash_job, hashes ):
   hash_job.hashdict.update (
      roverlay.digest.multihash_file ( hash_job.filepath, hashes )
   )
# --- end of _calculate_hashes (...) ---

class Hashjob ( object ):
   def __init__ ( self, filepath, hashdict=None ):
      self.filepath = filepath
      self.hashdict = dict() if hashdict is None else hashdict
   # --- end of __init__ (...) ---


class HashPool ( object ):
   def __init__ ( self, hashes, max_workers ):
      super ( HashPool, self ).__init__()
      self.hashes      = frozenset ( hashes )
      self._jobs       = dict()
      self.max_workers = int ( max_workers )
   # --- end of __init__ (...) ---

   def add ( self, backref, filepath, hashdict=None ):
      self._jobs [backref] = Hashjob ( filepath, hashdict )
   # --- end of add (...) ---

   def run ( self ):
      #with concurrent.futures.ProcessPoolExecutor ( self.max_workers ) as exe:
      with concurrent.futures.ThreadPoolExecutor ( self.max_workers ) as exe:
         running_jobs = frozenset (
            exe.submit ( _calculate_hashes, job, self.hashes )
            for job in self._jobs.values()
         )

         # wait
         for finished_job in concurrent.futures.as_completed ( running_jobs ):
            if finished_job.exception() is not None:
               raise finished_job.exception()
   # --- end of run (...) ---

   def reset ( self ):
      self._jobs.clear()
   # --- end of reset (...) ---

   def get ( self, backref ):
      return self._jobs [backref].hashdict
   # --- end of get (...) ---
