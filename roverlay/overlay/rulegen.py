# R overlay -- overlay package, depres rule generator
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

class DepresRuleGenerator ( object ):

   def __init__ ( self, overlay ):
      super ( DepresRuleGenerator, self ).__init__()
      self.overlay_ref = overlay.get_ref()
      self.rule_class  = None
   # --- end of __init__ (...) ---

   def make_rule_args ( self ):
      overlay               = self.overlay_ref.deref_safe()
      default_category_name = overlay.default_category

      # COULDFIX: direct access to "private" attributes
      for cat_name, cat in overlay._categories.items():
         is_default_category = cat_name == default_category_name

         for pkgdir_name, pkgdir in cat._subdirs.items():
            if not pkgdir.empty():
               repo_ids      = set()
               package_names = set()
               for p_info in pkgdir.iter_package_info():
                  package_name = p_info.get (
                     'package_name', do_fallback=True
                  )
                  if package_name:
                     package_names.add ( package_name )

                  repo = p_info.get ( 'origin', do_fallback=True )
                  if repo is not None:
                     repo_ids.add ( repo.get_identifier() )
               # -- end for <get repo ids / package names>

               yield (
                  repo_ids,
                  dict (
                     dep_str               = pkgdir_name,
                     resolving_package     = ( cat_name + '/' + pkgdir_name ),
                     is_selfdep            = 2 if is_default_category else 1,
                     priority              = 90,
                     finalize              = True,
                     selfdep_package_names = package_names,
                  )
               )
         # -- end for pkgdir
      # -- end for category
   # --- end of make_rule_args (...) ---

   def make_rules ( self ):
      for repo_ids, rule_kwargs in self.make_rule_args():
         yield ( repo_ids, self.rule_class ( **rule_kwargs ) )
   # --- end of make_rules (...) ---

   def make_rule_dict ( self ):
      rule_dict = dict()
      for repo_ids, rule_kwargs in self.make_rule_args():
         rule = self.rule_class ( **rule_kwargs )
         for repo_id in repo_ids:
            if repo_id in rule_dict:
               rule_dict [repo_id].append ( rule )
            else:
               rule_dict [repo_id] = [ rule ]
      return rule_dict
   # --- end of make_rule_dict (...) ---

# --- end of DepresRuleGenerator ---
