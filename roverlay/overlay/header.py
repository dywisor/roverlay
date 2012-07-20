class EbuildHeader ( object ):
	def __init__ ( self, default_header ):
		self.default_header = default_header
		self.eclasses       = ()

		self._cached_header = None
	# --- end of __init__ (...) ---

	def set_eclasses ( self, eclass_names ):
		self.eclasses = eclass_names
	# --- end of set_eclasses (...) ---

	def get ( self, use_cached=True ):
		if self._cached_header is None or not use_cached:
			self._cached_header = self._make()
		return self._cached_header
	# --- end of get (...) ---

	def _make ( self ):
		if self.eclasses:
			inherit = 'inherit ' + ' '.join ( sorted ( self.eclasses ) )
		else:
			inherit = None

		# header and inherit is expected and therefore the first condition here
		if inherit and self.default_header:
			return self.default_header + '\n' + inherit

		elif inherit:
			return inherit

		elif self.default_header:
			return self.default_header

		else:
			return None
	# --- end of _make (...) ---
