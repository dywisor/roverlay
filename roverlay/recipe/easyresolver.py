
from roverlay                      import config
from roverlay.depres               import listeners
from roverlay.depres.depresolver   import DependencyResolver
from roverlay.depres.simpledeprule import SimpleDependencyRulePool


def setup():
	res = DependencyResolver()
	# log everything
	res.set_logmask ( -1 )

	srule_pool = SimpleDependencyRulePool ( 'default pool', priority=45 )

	srule_files = config.get ( 'DEPRES.simple_rules.files', None )

	if srule_files:
		if isinstance ( srule_files, str ):
			srule_pool.load_rule_file ( srule_files )
		else:
			for f in srule_files:
				srule_pool.load_rule_file ( f )

		res.add_rulepool ( srule_pool )

	unres_file = config.get ( 'LOG.FILE.unresolvable', None )
	if unres_file:
		unres_listener = listeners.UnresolvableSetFileListener ( unres_file )
		res.add_listener ( unres_listener )
	return res
# --- end of setup (...) ---
