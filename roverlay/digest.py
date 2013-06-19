# R overlay -- roverlay package, digest
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides digest related utility functions (e.g. md5sum_file())"""

__all__ = [ 'digest_compare', 'digest_supported',
   'dodigest_file', 'md5sum_file'
]

import hashlib
import portage.util.whirlpool

_HASH_CREATE_MAP = {
   'md5'       : hashlib.md5,
   'sha1'      : hashlib.sha1,
   'sha256'    : hashlib.sha256,
   'sha512'    : hashlib.sha512,
   'whirlpool' : portage.util.whirlpool.new,
}

def _generic_obj_hash ( hashobj, fh, binary_digest=False, blocksize=16384 ):
   block = fh.read ( blocksize )
   while block:
      hashobj.update ( block )
      block = fh.read ( blocksize )

   return hashobj.digest() if binary_digest else hashobj.hexdigest()
# --- end of _hashsum_generic (...) ---

def multihash ( fh, hashlist, binary_digest=False, blocksize=16384 ):
   """Calculates multiple digests for an already openened file and returns the
   resulting hashes as dict.

   arguments:
   * fh            -- file handle
   * hashlist      -- iterable with hash names (e.g. md5)
   * binary_digest -- whether the hashes should be binary or not
   * blocksize     -- block size for reading
   """
   hashobj_dict = {
      h: _HASH_CREATE_MAP[h]() for h in hashlist
   }
   block = fh.read ( blocksize )
   while block:
      for hashobj in hashobj_dict.values():
         hashobj.update ( block )
      block = fh.read ( blocksize )

   if binary_digest:
      return { h: hashobj.digest() for h, hashobj in hashobj_dict.items() }
   else:
      return { h: hashobj.hexdigest() for h, hashobj in hashobj_dict.items() }
# --- end of multihash (...) ---

def multihash_file ( filepath, digest_types, **kwargs ):
   """Calculates multiple digests for the given file path.

   Returns an empty dict if digest_types is empty.

   arguments:
   * filepath     --
   * digest_types --
   * **kwargs     -- passed to multihash()
   """
   if digest_types:
      with open ( filepath, mode='rb' ) as fh:
         hashdict = multihash ( fh, digest_types, **kwargs )
      return hashdict
   else:
      return dict()
# --- end of multihash_file (...) ---

def md5sum_file ( fh, binary_digest=False ):
   """Returns the md5 sum for an already opened file."""
   return _generic_obj_hash ( hashlib.md5(), fh, binary_digest )
# --- end of md5sum_file (...) ---

def sha1_file ( fh, binary_digest=False ):
   return _generic_obj_hash ( hashlib.sha1(), fh, binary_digest )
# --- end of sha1_file (...) ---

def sha256_file ( fh, binary_digest=False ):
   return _generic_obj_hash ( hashlib.sha256(), fh, binary_digest )
# --- end of sha256_file (...) ---

def sha512_file ( fh, binary_digest=False ):
   return _generic_obj_hash ( hashlib.sha512(), fh, binary_digest )
# --- end of sha512_file (...) ---

def whirlpool_file ( fh, binary_digest=False ):
   return _generic_obj_hash (
      portage.util.whirlpool.new(), fh, binary_digest
   )
# --- end of whirlpool_file (...) ---

# TODO: remove
_DIGEST_MAP = dict (
   md5       = md5sum_file,
   sha1      = sha1_file,
   sha256    = sha256_file,
   sha512    = sha512_file,
   whirlpool = whirlpool_file,
)

def digest_supported ( digest_type ):
   """Returns True if the given digest type is supported, else False."""
   return digest_type in _DIGEST_MAP
# --- digest_supported (...) ---

def dodigest_file ( _file, digest_type, binary_digest=False ):
   ret = None
   with open ( _file, mode='rb' ) as fh:
      ret = _DIGEST_MAP [digest_type] ( fh, binary_digest=binary_digest )
   return ret
# --- end of dodigest_file (...) ---

def digest_compare ( _file, digest, digest_type, binary_digest=False ):
   return digest == dodigest_file ( _file, digest_type, binary_digest )
# --- end of digest_compare (...) ---
