
from roverlay                      import config
from roverlay.depres               import listeners
from roverlay.depres.depresolver   import DependencyResolver
from roverlay.depres.simpledeprule import SimpleDependencyRulePool


def setup():
	res = DependencyResolver()
	# log everything
	res.set_logmask ( -1 )

	srule_pool = SimpleDependencyRulePool ( 'default pool', priority=45 )

	srule_files = config.get_or_fail ( 'DEPRES.simple_rules.files' )

	unres_listener = listeners.UnresolvableSetFileListener (
		config.get_or_fail ( 'LOG.FILE.unresolvable' )
	)

	if isinstance ( srule_files, str ):
		srule_pool.load_rule_file ( srule_files )
	else:
		for f in srule_files:
			srule_pool.load_rule_file ( f )

	res.add_rulepool ( srule_pool )
	res.add_listener ( unres_listener )
	return res
# --- end of setup (...) ---
