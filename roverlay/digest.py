import hashlib

def md5sum_file ( fh, binary_digest=False ):
	"""Returns the md5 sum for an already opened file."""
	md5 = hashlib.md5()
	blocksize = 16384

	block = fh.read ( blocksize )
	while block:
		md5.update ( block )
		block = fh.read ( blocksize )

	return md5.digest() if binary_digest else md5.hexdigest()
# --- end of md5sum_file (...) ---


_DIGEST_MAP = dict (
	md5 = md5sum_file,
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
