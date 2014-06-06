# R overlay -- common webgui functionality, roverlay<=>webgui adapter
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import absolute_import

## roverlay modules
import roverlay.interface.main
import roverlay.interface.depres

import roverlay.depres
import roverlay.depres.deptype
import roverlay.depres.simpledeprule.pool
import roverlay.depres.simpledeprule.rules
import roverlay.depres.simpledeprule.util

# alias
_DEPRULE_UTIL = roverlay.depres.simpledeprule.util

from roverlay.depres import deptype
from roverlay.depres.simpledeprule.rules import (
   SimpleDependencyRule,
   SimpleFuzzyDependencyRule,
   SimpleFuzzyIgnoreDependencyRule,
   SimpleFuzzySlotDependencyRule,
   SimpleIgnoreDependencyRule
)
from roverlay.depres.simpledeprule.pool import SimpleDependencyRulePool


## roverlay webgui modules
import rvcommon.util
import rvcommon.portage.adapter
import rvcommon.portage.models
import rvcommon.depres.models

from rvcommon.portage.adapter import (
   resolving_to_dep_atom, dep_atom_to_resolving
)
from rvcommon.util    import (
   create_model, get_or_create_model, get_revmap, get_intmask_translator
)
from rvcommon.depres  import models

if __debug__:
   for name in rvcommon.portage.models.EXPORT_MODELS:
      assert hasattr ( models, name )


## EXPORT_ADAPTERS
EXPORT_ADAPTERS = [
   'DepruleInterface',
   #'deconstruct_slot_parser',
   #'deconstruct_slot_restrict',
   #'deptype_to_matchtype',
   #'get_slot_option_kwargs',
   #'get_slot_parser',
   #'get_slot_restrict',
   #'matchtype_to_deptype',
   'model_to_rule',
   'models_to_rule_pools',
   'models_to_rules',
   #'mto_slot_mode',
   #'otm_slot_mode',
   #'rule_pool_mask_to_deptype',
   'rule_pools_to_models',
   'rule_pools_to_models_v',
   'rule_to_model',
   #'slot_options_to_model',
   #'slot_parser_to_model',
]
__all__ = EXPORT_ADAPTERS




# dict ( deprule class (object, cls) => deprule identifier (model, int) )
RULE_CLS_TO_KEY_MAP = {
   SimpleDependencyRule              : models.SimpleDependencyRule.RULETYPE_NORMAL,
   SimpleFuzzyDependencyRule         : models.SimpleDependencyRule.RULETYPE_FUZZY,
   SimpleFuzzyIgnoreDependencyRule   : models.SimpleDependencyRule.RULETYPE_FUZZY_IGNORE,
   SimpleFuzzySlotDependencyRule     : models.SimpleDependencyRule.RULETYPE_FUZZY_SLOT,
   SimpleIgnoreDependencyRule        : models.SimpleDependencyRule.RULETYPE_NORMAL_IGNORE,
}
RULE_KEY_TO_CLS_MAP = get_revmap ( RULE_CLS_TO_KEY_MAP )

# n-tuple of 2-tuples <model_value, object_value>
#  any match/deptype not listed here will be discard during translation

# * match_type => deptype
#
_MATCHTYPE_DEPTYPE_MAP = tuple ((
   ( models.SimpleDependencyRule.MATCHTYPE_EXTERNAL, deptype.external ),
   ( models.SimpleDependencyRule.MATCHTYPE_INTERNAL, deptype.internal ),
   ( models.SimpleDependencyRule.MATCHTYPE_SELFDEP,  deptype.selfdep  ),
))

# * slot_mode(model) => slot_mode(object)
#
_SLOTMODE_TRANSLATE_MAP = tuple ((
   # ( 0, 0 ),
   ( models.FuzzySlotOptions.SLOT_FLAG_WITH_VERSION, 1 ),
   ( models.FuzzySlotOptions.SLOT_FLAG_OPEN, 2 ),
))




# model-to-object
_intmask_mto = lambda m: get_intmask_translator ( m, 0, 1 )
# object-to-model
_intmask_otm = lambda m: get_intmask_translator ( m, 1, 0 )

matchtype_to_deptype = _intmask_mto ( _MATCHTYPE_DEPTYPE_MAP )
deptype_to_matchtype = _intmask_otm ( _MATCHTYPE_DEPTYPE_MAP )
mto_slot_mode        = _intmask_mto ( _SLOTMODE_TRANSLATE_MAP )
otm_slot_mode        = _intmask_otm ( _SLOTMODE_TRANSLATE_MAP )

def rule_pool_mask_to_deptype ( mask ):
   return mask & deptype.RESOLVE_ALL



def get_slot_restrict ( values ):
   """Creates a 'slot restrict' object.

   Returns: a slot restrict object or None

   arguments:
   * values -- a list of values or None
   """
   return _DEPRULE_UTIL.SlotSetRestrict(values) if values else None
# --- end of get_slot_restrict (...) ---

def deconstruct_slot_restrict ( slot_restrict ):
   """The inverse of get_slot_restrict(). Creates a list of values.

   Note that
      deconstruct_slot_restrict(get_slot_restrict(X)) != X and
      get_slot_restrict(deconstruct_slot_restrict(Y)) != Y
   due to unordered data types in slot restrict objects.

   Returns: list of values or None

   arguments:
   * slot_restrict -- slot restrict object or None
   """
   if slot_restrict:
      # hacky, accessing a "hidden" attribute
      return sorted ( slot_restrict._slotset )
   else:
      return None
# --- end of deconstruct_slot_restrict (...) ---

def get_slot_parser ( model_obj ):
   """Creates a 'slot parser' object, which is responsible for (dynamically)
   constructing slot values in fuzzy dependency rules.

   Returns: a slot parser object or None

   arguments:
   * model_obj -- a SlotPartsSelection model instance or None
   """
   if not model_obj:
      return None
   elif model_obj.is_immediate:
      return _DEPRULE_UTIL.ImmediateSlotValueCreator (
         model_obj.get_immediate()
      )
   else:
      low  = model_obj.get_low()
      high = model_obj.get_high()

      if high is None or low == high:
         return _DEPRULE_UTIL.SingleIndexValueCreator ( index=low )
      else:
         return _DEPRULE_UTIL.IndexRangeSlotValueCreator ( low=low, high=high )
      # -- end if <<high>>
   # -- end if <model_obj>
# --- end of get_slot_parser (...) ---

def deconstruct_slot_parser ( slot_parser ):
   """Deconstructs a slot parser object into arguments suitable for creating
   a SlotPartsSelection model instance.

   Returns: args as dictionary or None

   arguments:
   * slot_parser -- slot parser object or None
   """
   if not slot_parser:
      return None

   kwargs = { 'is_immediate': False, }
   if isinstance ( slot_parser, _DEPRULE_UTIL.ImmediateSlotValueCreator ):
      kwargs ['is_immediate'] = True
   elif not isinstance ( slot_parser, _DEPRULE_UTIL.SlotValueCreatorBase ):
      raise TypeError ( slot_parser )

   kwargs ['value'] = [ str(a) for a in slot_parser.get_constructor_args() ]
   return kwargs
# --- end of deconstruct_slot_parser (...) ---

def slot_parser_to_model ( slot_parser ):
   """The inverse of get_slot_parser().
   Does not accept None.

   Returns: SlotPartsSelection model instance

   arguments:
   * slot_parser -- slot parser object, must not be None
   """
   assert slot_parser is not None
   kwargs = deconstruct_slot_parser ( slot_parser )
   return get_or_create_model ( models.SlotPartsSelection, **kwargs )
# --- end of slot_parser_to_model (...) ---

def slot_options_to_model ( deprule ):
   """Creates a FuzzySlotOptions model instance for the given dependency rule.

   Returns: FuzzySlotOptions model instance

   arguments:
   * deprule -- dependency rule object, has to be a fuzzy slot dep rule
                and must not be None
   """
   get_slot_selection = (
      lambda k: None if k is None else slot_parser_to_model(k)
   )

   return get_or_create_model (
      models.FuzzySlotOptions,
      accepted_values = deconstruct_slot_restrict ( deprule.slot_restrict ),
      slot_parts      = get_slot_selection ( deprule.slotparts ),
      subslot_parts   = get_slot_selection ( deprule.subslotparts ),
      flags           = otm_slot_mode ( deprule.mode ),
      slot_operator   = (
         models.FuzzySlotOptions [deprule.slot_operator]
         if deprule.slot_operator else models.FuzzySlotOptions.SLOTOP_NONE
      ),
   )
# --- end of slot_options_to_model (...) ---

def get_slot_option_kwargs ( model_obj ):
   """Creates and returns a dict with keyword arguments for creating
   fuzzy-slot dependency rule objects.

   Returns: a dict, possibly empty

   arguments:
   * model_obj -- FuzzySlotOptions model instance or None
   """
   if not model_obj:
      return {}

   return {
      'slot_mode'      : mto_slot_mode     ( model_obj.flags ),
      'slot_restrict'  : get_slot_restrict ( model_obj.accepted_values ),
      'slotparts'      : get_slot_parser   ( model_obj.slot_parts ),
      'subslotparts'   : get_slot_parser   ( model_obj.subslot_parts ),
      'slot_operator'  : (
         model_obj.SLOTOP_CHOICES [model_obj.slot_operator] or None
      ),
   }
# --- end of get_slot_option_kwargs (...) ---

def model_to_rule ( obj ):
   """Converts a dependency rule model instance to an object (instance).

   Note that irrelevant information is discarded (from the deprule object's
   perspective, e.g. resolving_package for "ignore"-type rules,
   slot options for non-fuzzy-slot rules and metadata like score and comments
   for all rule types).

   Returns: a 2-tuple<rule pool mask, dependency rule object>
            See RULE_CLS_TO_KEY_MAP for types/object classes.
            The rule pool mask is the pool's deptype _with_ the "is_selfdep"
            bit.

   arguments:
   * obj -- SimpleDependencyRule model instance
   """
   rule_cls       = RULE_KEY_TO_CLS_MAP [obj.rule_type]
   kwargs         = {}

   if obj.priority is not None:
      kwargs ['priority'] = obj.priority

   kwargs ['is_selfdep'] = 1 if obj.match_type & obj.MATCHTYPE_SELFDEP else 0

   if 0 == ( obj.rule_type & obj.RULETYPE__IGNORE ):
      kwargs ['resolving_package'] = dep_atom_to_resolving ( obj.dep_atom )

   if obj.rule_type & obj.RULETYPE__FUZZY_SLOT:
      kwargs.update ( get_slot_option_kwargs ( obj.slot_options ) )

   # collect dep strings
   dep_strings = [ s.value for s in obj.query_dep_strings() if s.value ]


   # create rule object
   deprule = rule_cls ( **kwargs )
   for dep_str in dep_strings:
      deprule.add_resolved ( dep_str )
   # -- end for
   deprule.done_reading()

   # store the database object's id
   assert getattr ( deprule, 'database_id', None ) is None
   deprule.database_id = obj.id


   return (
      matchtype_to_deptype ( obj.match_type & obj.MATCHTYPE__RULEPOOL_MASK ),
      deprule
   )
# --- end of model_to_rule (...) ---

def models_to_rules ( objects ):
   """Converts several dependency rule model instances into objects.

   Returns: a dict { rule pool mask => list<deprule object> }

   arguments:
   * objects -- iterable containing SimpleDependencyRule model instances
   """
   rules = dict()
   for obj in objects:
      rulepool_mask, deprule = model_to_rule ( obj )
      if rulepool_mask not in rules:
         rules [rulepool_mask] = [ deprule ]
      else:
         rules [rulepool_mask].append ( deprule )
   # -- end for

   return rules
# --- end of models_to_rules (...) ---

def models_to_rule_pools ( objects ):
   """Generator that creates rule pools containing dependency rule objects
   from model instances.

   Yields: SimpleDependencyRulePool objects

   arguments:
   * objects -- iterable containing models.SimpleDependencyRule instances
   """
   rules_dict = models_to_rules ( objects )

   for rule_pool_mask, rules in rules_dict.items():
      # * the rule pool name doesn't need to be unique
      # * rule pool priority is not defined, omit it
      # * the created rule pool needs to be sorted, which is done here
      #
      rule_pool = SimpleDependencyRulePool (
         name          = "db_{:#x}".format ( rule_pool_mask ),
         deptype_mask  = rule_pool_mask_to_deptype ( rule_pool_mask ),
         initial_rules = rules,
      )
      rule_pool.sort()

      yield rule_pool
   # -- end for
# --- end of models_to_rule_pools (...) ---

def rule_to_model ( pool_match_type, deprule ):
   """Creates a SimpleDependencyRule model instance for the given
   dependency rule.

   Returns: models.SimpleDependencyRule

   arguments:
   * pool_match_type -- converted deptype mask of the deprule's pool
   * deprule         -- dependency rule object
   """
   cls       = models.SimpleDependencyRule
   ds_cls    = models.DependencyString
   rule_type = RULE_CLS_TO_KEY_MAP [deprule.__class__]

   rule_model = get_or_create_model (
      cls,
      rating      = cls.RATING_NONE,
      is_enabled  = True,
      priority    = deprule.priority,
      rule_type   = rule_type,
      dep_atom    = (
         None if rule_type & cls.RULETYPE__IGNORE
            else resolving_to_dep_atom ( deprule.resolving_package )
      ),
      match_type  = (
         (pool_match_type|cls.MATCHTYPE_SELFDEP)
            if deprule.is_selfdep else pool_match_type
      ),
      slot_options = (
         slot_options_to_model ( deprule )
            if rule_type & cls.RULETYPE__FUZZY_SLOT else None
      ),
   )

   # add dep strings
   for dep_str in deprule.dep_alias:
      get_or_create_model ( ds_cls , value=dep_str ).rules.add ( rule_model )

   return rule_model
# --- end of rule_to_model (...) ---

def rule_pools_to_models_v ( rule_pools ):
   """Generator that creates SimpleDependencyRule model instances
   for all rules from the given rule pool(s).

   Yields: SimpleDependencyRule models

   arguments:
   * rule_pools -- an iterable of dependency rule pools, which are usually
                    derived from roverlay.depres.deprule.DependencyRulePoolBase
   """
   for rule_pool in rule_pools:
      pool_match_type = (
         deptype_to_matchtype ( rule_pool.deptype_mask ) & \
         models.SimpleDependencyRule.MATCHTYPE__RULEPOOL
      )

      for deprule in rule_pool.iter_rules():
         yield rule_to_model ( pool_match_type, deprule )
# --- end of rule_pools_to_models_v (...) ---

def rule_pools_to_models ( *rule_pools ):
   """var-arg variant of rule_pools_to_models_v().

   arguments:
   * *rule_pools --
   """
   return rule_pools_to_models_v ( rule_pools )
# --- end of rule_pools_to_models (...) ---


class DepruleInterface ( rvcommon.util.InterfaceProxy ):

   def __init__ ( self,
      is_installed=False, config=None, config_file=None, interface_kwargs={}
   ):
      super ( DepruleInterface, self ).__init__ (
         roverlay.interface.depres.DepresInterface.new_standalone (
            is_installed=is_installed, config=config,
            config_file=config_file, **interface_kwargs
         )
      )

   def convert_all_to_models ( self ):
      return rule_pools_to_models_v ( self.interface.poolstack )
