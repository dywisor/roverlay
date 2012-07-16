
from roverlay                      import config
from roverlay.depres               import listeners, deptype
from roverlay.depres.depresolver   import DependencyResolver
from roverlay.depres.simpledeprule import SimpleDependencyRulePool


def setup ( err_queue ):
	res = DependencyResolver ( err_queue=err_queue )
	# log everything
	res.set_logmask ( -1 )

	srule_files = config.get ( 'DEPRES.simple_rules.files', None )
	if srule_files:
		res.get_reader().read ( srule_files )

	unres_file = config.get ( 'LOG.FILE.unresolvable', None )
	if unres_file:
		unres_listener = listeners.UnresolvableSetFileListener ( unres_file )
		res.add_listener ( unres_listener )
	return res
# --- end of setup (...) ---
