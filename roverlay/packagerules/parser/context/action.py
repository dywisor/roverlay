# R overlay -- package rule parser, action-block context
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import re

import roverlay.strutil

import roverlay.packagerules.actions.evar
import roverlay.packagerules.actions.info
import roverlay.packagerules.actions.relocate
import roverlay.packagerules.actions.trace
import roverlay.packagerules.parser.context.base

class RuleActionException ( ValueError ):
   pass
# --- end of RuleActionException ---

class ActionUnknown ( RuleActionException ):
   pass
# --- end of ActionUnknown ---

class ActionNeedsValue ( RuleActionException ):
   pass
# --- end of ActionNeedsValue ---

class ActionInvalid ( RuleActionException ):
   pass
# --- end of ActionInvalid ---


class RuleActionContext (
   roverlay.packagerules.parser.context.base.BaseContext
):
   """RuleActionContext parses action-blocks."""

   # keywords for the "ignore" action
   KEYWORDS_ACTION_IGNORE = frozenset ({
      'ignore',
      'do-not-process'
   })

   KEYWORDS_ACTION_TRACE = frozenset ({
      'trace',
   })


   # dict ( <keyword> => <evar class> )
   # Dict of evar action keywords (with corresponding classes)
   #
   KEYWORDS_EVAR = {
      'keywords' : roverlay.packagerules.actions.evar.KeywordsEvarAction,
   }

   # default info set-to/rename actions
   #  using the lazy variant for renaming
   #
   DEFAULT_MODIFY_INFO_ACTIONS = (
      roverlay.packagerules.actions.info.InfoSetToAction,
      roverlay.packagerules.actions.info.InfoRenameAction,
   )

   # dict { key => None | ( None|False|SetTo_Action, None|False|Rename_Action )
   #   where None  is "use default action(s)"
   #   and   False is "invalid"/"not supported"
   #
   # (see comment in packageinfo.py concerning keys that exist when calling
   #  apply_action() and enable lazy actions if necessary)
   #
   MODIFIABLE_INFO_KEYS = {
      'name'     : None,
      'category' : (
         None,
         roverlay.packagerules.actions.relocate.CategoryRenameAction,
      ),
      'destfile' : (
         roverlay.packagerules.actions.relocate.SrcDestSetToAction,
         roverlay.packagerules.actions.relocate.SrcDestRenameAction
      ),
   }

   # TODO / Notes:
   #
   # * "combined" actions, e.g. name,category as "pseudo" actions?
   #
   # dict { pseudo_key => tuple ( argparse_function, set { real key[s] } ) }
   #
##   DEMUX_INFO_KEYS = {
##      'cp' : ( argstr_parse(), { 'name', 'category', } )
##   }

   def __init__ ( self, namespace ):
      super ( RuleActionContext, self ).__init__ ( namespace )
      self._actions = list()
   # --- end of __init__ (...) ---

   def _add_action ( self, action ):
      if action.do_test ( return_on_error=False ):
         self._actions.append ( action )
   # --- end of _add_action (...) ---

   def _add_as_info_action ( self, keyword, argstr, orig_str, lino ):
      """Tries to add <keyword, argstr> as package info-manipulating action.

      Returns true if such an action has been created and added, else False.
      Invalid values/lines will be catched here. A return value of False
      simply means that keyword/argstr do not represent an info action.

      arguments:
      * keyword  --
      * argstr   --
      * orig_str --
      * lino     --

      Raises:
      * ActionUnknown
      * ActionNeedsValue
      """
      # get action_type_str (and, possibly, key)
      action_type_str, sepa, key = keyword.partition ( "_" )
      action_type_str = action_type_str.lower()

      if action_type_str == "set":
         # is a set-to info action, continue
         action_type = 0
      elif action_type_str == "rename":
         # is a rename info action, continue
         action_type = 1
      else:
         # not an info action
         return False
      # -- end if;

      if not sepa:
         # get key from argstr
         argv = roverlay.strutil.split_whitespace ( argstr, maxsplit=1 )
         if argv:
            key = roverlay.strutil.unquote ( argv [0].lower() )
            if not key:
               # better safe than sorry ;)
               #return False
               raise ActionUnknown ( orig_str )
         else:
            #return False
            raise ActionUnknown ( orig_str )


         # dont unquote value here,
         #  this operation might depend on key in future
         value = argv [1]
      else:
         value = argstr
      # -- end if;

      # get action class (raises KeyError)
      try:

         # ( ( cls_tuple or <default> ) [action_type] ) or <default>
         action_cls = (
            self.MODIFIABLE_INFO_KEYS [key]
            or self.DEFAULT_MODIFY_INFO_ACTIONS
         ) [action_type]

         if action_cls is None:
            action_cls = self.DEFAULT_MODIFY_INFO_ACTIONS [action_type]
      except KeyError:
         raise ActionUnknown ( orig_str )

      # create and add action
      if action_cls is False:
         raise ActionInvalid ( orig_str )
      elif action_type == 0:
         # info action (1 arg)
         value = roverlay.strutil.unquote ( value )

         if value:
            self._add_action ( action_cls ( key, value, lino ) )
         else:
            raise ActionNeedsValue ( orig_str )
      else:
         # rename action (1 arg)
         #  sed-like replace statement "s/a/b/flags?"
         #
         # FIXME/TODO *** flags are not implemented ***
         #
         # len ( value ) >= len (
         #    "s" + sepa + len(a)>=1 + sepa + len(b)>=1 + sepa + len(flags)>=0
         # )
         # => 6 relevant parts (3x sepa, 2x value), len (value) has to be > 5
         #

         value = roverlay.strutil.unquote ( value )

         if len ( value ) > 5 and value[0] == 's' and value[1] == value[-1]:

            # double-escaped backslash
            re_splitter = self.namespace.get_object (
               re.compile, '(?<!\\\)' + value [1]
            )

            # (redef argv)
            argv = re_splitter.split ( value, maxsplit=3 )

            if len ( argv ) > 3 and all ( argv[:4] ):
               raise NotImplementedError ( "flags are not supported yet." )

            elif len ( argv ) > 2 and all ( argv[:3] ):
               self._add_action (
                  action_cls (
                     key,
                     self.namespace.get_object ( re.compile, argv [1] ),
                     argv [2],
                     lino
                  )
               )
            else:
               raise ActionNeedsValue ( orig_str )
         else:
            raise ActionNeedsValue ( orig_str )
      # -- end if;

      return True
   # --- end of _add_as_info_action (...) ---

   def feed ( self, _str, lino ):
      """Feeds this action block with input.

      arguments:
      * _str --
      * lino --

      Raises:
      * InvalidContext
      """
      if _str in self.KEYWORDS_NOP_STATEMENT:
         pass
      elif _str in self.KEYWORDS_ACTION_IGNORE:
         if not self._actions:
            self._actions = None
         else:
            raise self.InvalidContext (
               "ignore action-block does not accept any other action."
            )
      elif self._actions is None:
         raise self.InvalidContext (
            "ignore action-block does not accept any other action."
         )
      else:
         # split _str into (<keyword>,<value>)
         argv = roverlay.strutil.split_whitespace ( _str, maxsplit=1 )

         if argv [0] in self.KEYWORDS_ACTION_TRACE:
            if len ( argv ) > 1 and argv [1]:
               self._add_action (
                  roverlay.packagerules.actions.trace.TraceAction (
                     roverlay.strutil.unquote ( argv [1] ),
                     lino
                  )
               )
            else:
               self._add_action (
                  roverlay.packagerules.actions.trace.MarkAsModifiedAction (
                     lino
                  )
               )

         elif len ( argv ) > 1 and (
            self._add_as_info_action ( argv [0], argv [1], _str, lino )
         ):
            pass

         else:
            evar_cls = self.KEYWORDS_EVAR.get ( argv [0], None )

            try:
               if evar_cls:
                  self._add_action (
                     evar_cls ( roverlay.strutil.unquote ( argv [1] ), lino )
                  )
               else:
                  raise ActionUnknown ( _str )

            except IndexError:
               raise ActionNeedsValue ( _str )
   # --- end of feed (...) ---

   def create ( self ):
      """Returns all created actions."""
      return self._actions
   # --- end of create (...) ---

# --- end of RuleActionContext ---
