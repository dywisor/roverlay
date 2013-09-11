# R overlay -- setup script, base env
# -*- coding: utf-8 -*-

class SetupSubEnvironment ( object ):

   NEEDS_CONFIG_TREE = False

   ACTIONS = None

   def __init__ ( self, setup_env ):
      super ( SetupSubEnvironment, self ).__init__()

      self.setup_env = setup_env
      self.stdout    = setup_env.stdout
      self.stderr    = setup_env.stderr
      self.info      = setup_env.info
      self.error     = setup_env.error

      if self.NEEDS_CONFIG_TREE:
         self.config = self.setup_env.create_new_target_config()
      else:
         self.config = None

      self.setup()
   # --- end of __init__ (...) ---

   def setup ( self ):
      pass
   # --- end of setup (...) ---

   def run ( self, steps_to_skip=None, verbose_skip=True, steps=None ):
      pretend = self.setup_env.options ['pretend']
      ACTIONS = steps if steps is not None else self.ACTIONS

      if ACTIONS:
         if steps_to_skip:
            methods_to_call = [
               (
                  None if item[0] in steps_to_skip
                  else getattr ( self, 'do_' + item[0] )
               ) for item in ACTIONS
            ]
         else:
            methods_to_call = [
               getattr ( self, 'do_' + item[0] ) for item in ACTIONS
            ]

         wait_confirm_can_skip = self.setup_env.wait_confirm_can_skip


         for method, action in zip ( methods_to_call, ACTIONS ):
            if method is None:
               if verbose_skip:
                  self.info ( "{}: skipped.\n".format ( action[0] ) )

            elif not action[1]:
               method ( pretend=pretend )

            elif wait_confirm_can_skip (
               message=method.__doc__, append_newline=False
            ):
               method ( pretend=pretend )
            else:
               self.info ( "skipped.\n" )

      else:
         raise NotImplementedError (
            "{}.{}()".format ( self.__class__.__name__, "do_all" )
         )
   # --- end of run (...) ---

# --- end of SetupSubEnvironment ---
