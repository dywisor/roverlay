import sys
import threading

class _EQueue ( object ) : pass

class NopErrorQueue ( _EQueue ):
	"""This can be used as error queue in single-threaded execution."""
	def __init__ ( self ):
		self.empty = True

	def push ( self, context, error ):
		self.empty = False
		sys.stderr.write ( "Exception from {!r}:\n".format ( context ) )
		raise error

	def really_empty ( self ): return self.empty
	def attach_queue ( self, q, unblock_item ): pass
	def remove_queue ( self, q ): pass
	def unblock_queues ( self ): pass
	def peek ( self ): return ( None, None )
	def get_all ( self ): return ( ( None, None ), )
	def get_exceptions ( self ): return ()


#class ErrorQueue ( NopErrorQueue ):
class ErrorQueue ( _EQueue ):
	"""This is the error queue for threaded execution."""
	# (it's not a queue)

	def __init__ ( self ):
		self.empty              = True
		self._exceptions        = list()
		# this error queue is able to unblock waiting queues (in future; TODO)
		#  id -> queue [, unblocking_item:=None]
		self._queues_to_unblock = dict()

		self._lock = threading.Lock()

	def really_empty ( self ):
		"""Returns true if no exception stored. Uses a lock to ensure
		correctness of the result.
		"""
		with self._lock:
			self.empty = len ( self._exceptions ) == 0
		return self.empty

	def _unblock_queues ( self ):
		"""Sends an unblock item to all attached queues."""
		for q, v in self._queues_to_unblock.values():
			try:
				q.put_nowait ( v )
			except:
				pass

	def push ( self, context, error ):
		"""Pushes an exception. This also triggers on-error mode, which
		unblock all attached queues.

		arguments:
		* context -- the origin of the exception
		* error   -- the exception
		"""
		with self._lock:
			self._exceptions.append ( ( context, error ) )
			self.empty = False
			self._unblock_queues()

	def unblock_queues ( self ):
		"""Unblocks all attached queues."""
		with self._lock:
			self._unblock_queues()

	def attach_queue ( self, q, unblock_item ):
		"""Attaches a queue. Nothing will be done with it, unless an exception
		is pushed to this ErrorQueue, in which case all attached queues will
		be unblocked which allows queue-waiting threads to end.

		arguments:
		* q            -- queue
		* unblock_item -- item that is used for unblocking, e.g. 'None'
		"""
		with self._lock:
			self._queues_to_unblock [id (q)] = ( q, unblock_item )

	def remove_queue ( self, q ):
		"""Removes a queue. It will no longer receive an unblock item if
		on error mode.

		arguments:
		* q -- queue to remove
		"""
		self._lock.acquire()
		try:
			del self._queues_to_unblock [id (q)]
		except KeyError:
			pass
		finally:
			self._lock.release()

	def peek ( self ):
		"""Returns the latest pushed exception."""
		return self._exceptions [-1]

	def get_all ( self ):
		"""Returns all pushed exceptions."""
		# not copying, caller shouldn't modify the exception list
		return self._exceptions

	def get_exceptions ( self ):
		"""Similar to get_all, but a generator that filters out no-op exception
		pushes that are used to trigger on-error mode without a valid exception.
		"""
		for e in self._exceptions:
			if isinstance ( e [1], ( Exception, KeyboardInterrupt ) ):
				yield e
