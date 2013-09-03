# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

try:
   import copyreg
except ImportError:
   # python 2
   import copy_reg as copyreg

try:
   import concurrent.futures
except ImportError:
   import sys
   sys.stderr.write (
      '!!! concurrent.futures is not available.\n'
      '    Falling back to single-threaded variants.\n\n'
   )
   del sys
   HAVE_CONCURRENT_FUTURES = False
else:
   HAVE_CONCURRENT_FUTURES = True


import roverlay.digest

class HashFunction ( object ):

   def __init__ ( self, hashes ):
      super ( HashFunction, self ).__init__()
      self.hashes = frozenset ( hashes )
   # --- end of __init__ (...) ---

   def multihash_file ( self, filepath ):
      return roverlay.digest.multihash_file ( filepath, self.hashes )
   # --- end of multihash_file (...) ---

   def calculate ( self, hash_job ):
      hash_job.hashdict.update ( self.multihash_file ( hash_job.filepath ) )
      return hash_job
   # --- end of calculate (...) ---

   __call__ = calculate

   def pack ( self ):
      return ( self.__class__, ( self.hashes, ) )
   # --- end of pickle (...) ---

# --- end of HashFunction ---

copyreg.pickle ( HashFunction, HashFunction.pack )


class HashJob ( object ):
   def __init__ ( self, filepath, hashdict=None ):
      super ( HashJob ).__init__()
      self.filepath = filepath
      self.hashdict = dict() if hashdict is None else hashdict
   # --- end of __init__ (...) ---

# --- end of HashJob ---



class HashPool ( object ):
   def __init__ ( self, hashes, max_workers, use_threads=None ):
      super ( HashPool, self ).__init__()
      self.hashfunc    = HashFunction ( hashes )
      self._jobs       = dict()
      self.max_workers = (
         int ( max_workers ) if max_workers is not None else max_workers
      )

      if use_threads or use_threads is None:
         self.executor_cls = concurrent.futures.ThreadPoolExecutor
      else:
         self.executor_cls = concurrent.futures.ProcessPoolExecutor
   # --- end of __init__ (...) ---

   def add ( self, backref, filepath, hashdict=None ):
      self._jobs [backref] = HashJob ( filepath, hashdict )
   # --- end of add (...) ---

   def extend ( self, iterable ):
      for backref, filepath in iterable:
         self._jobs [backref] = HashJob ( filepath, None )
   # --- end of extend (...) ---

   def extend_with_hashdict ( self, iterable ):
      for backref, filepath, hashdict in iterable:
         self._jobs [backref] = HashJob ( filepath, hashdict )
   # --- end of extend_with_hashdict (...) ---

   def get_executor ( self ):
      return self.executor_cls ( self.max_workers )
   # --- end of get_executor (...) ---

   def is_concurrent ( self ):
      return HAVE_CONCURRENT_FUTURES and (
         self.max_workers is None or self.max_workers > 0
      )
   # --- end of is_concurrent (...) ---

   def run_as_completed ( self ):
      if self.is_concurrent():
         with self.get_executor() as exe:
            for backref, hash_job in zip (
               self._jobs.keys(),
               exe.map ( self.hashfunc, self._jobs.values() )
            ):
               yield ( backref, hash_job.hashdict )
      else:
         for backref, hash_job in self._jobs.items():
            self.hashfunc.calculate ( hash_job )
            yield ( backref, hash_job.hashdict )
   # --- end of run_as_completed (...) ---

   def run ( self ):
      if self.is_concurrent():
         with self.get_executor() as exe:
            running_jobs =  frozenset (
               exe.submit ( self.hashfunc, job )
               for job in self._jobs.values()
            )

            # wait
            for finished_job in (
               concurrent.futures.as_completed ( running_jobs )
            ):
               if finished_job.exception() is not None:
                  raise finished_job.exception()
               elif finished_job.cancelled():
                  break
      else:
         for hash_job in self._jobs.values():
            self.hashfunc.calculate ( hash_job )
   # --- end of run (...) ---

   def reset ( self ):
      self._jobs.clear()
   # --- end of reset (...) ---

   def get ( self, backref ):
      return self._jobs [backref].hashdict
   # --- end of get (...) ---

# --- end of HashPool ---
