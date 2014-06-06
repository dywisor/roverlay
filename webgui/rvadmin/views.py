# R overlay -- admin webgui, views
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from django.shortcuts import render, RequestContext, render_to_response

import rvadmin.const


# Create your views here.

GET_TEMPLATE_RELPATH = lambda name: (
   rvadmin.const.TEMPLATE_SUB_PATH + name + '.html'
)


VIEW_DEFAULTS_DICT = {
   'home_name'                : 'rvadmin',
   'active_navbar_item'       : None,
   'active_navbar_tab'        : 0,
   'navbar_items'             : rvadmin.const.NAVBAR_ITEMS,
   'navbar_tab_items'         : None,
   'navbar_dropdown_items'    : rvadmin.const.NAVBAR_DROPDOWN_ITEMS,
}


def add_defaults_to_dict ( d, request, home_url ):
   if d is None:
      d = VIEW_DEFAULTS_DICT.copy()
   else:
      d.update ( VIEW_DEFAULTS_DICT )

   d.update ({
      'page_url' : request.get_full_path(),
      'home_url' : home_url,
   })

   # FIXME: better url handling/creation, geturl()/{% url %} ?
   for key, navbar_item in d['navbar_items'].items():
      d [key + '_url'] = home_url + navbar_item.url
   # -- end for

   return d
# --- end of add_defaults_to_dict (...) ---

def set_active_navbar_item ( d, key ):
   d ['active_navbar_item'] = rvadmin.const.NAVBAR_ITEMS [key].key


def request_wrapper ( func ):
   def wrapped ( request, home_url, *args, **kwargs ):
      context      = RequestContext ( request )
      my_home_url  = "/" + home_url.rstrip("/") + "/"
      context_dict = add_defaults_to_dict ( None, request, my_home_url )

      # *not* passing home_url to func
      template_path, render_args = func (
         request, context, context_dict, *args, **kwargs
      )

      if context_dict.get ( 'active_navbar_item', None ) is None:
         purl = context_dict.get ( 'page_url' )
         if purl:
            for item in rvadmin.const.NAVBAR_ITEMS.values():
               if purl.startswith ( my_home_url + item.url ):
                  context_dict ['active_navbar_item'] = item.key
                  break
            # -- end for
      # -- end if <set active_navbar_item>

      if context_dict.get ( 'navbar_tab_items', None ) is None:
         context_dict ['navbar_tab_items'] = (
            rvadmin.const.NAVBAR_TAB_ITEMS.get (
               context_dict.get('active_navbar_item',None), None
            )
         )


      # FIXME: if template_path: ... else: ...
      assert template_path

      return render_to_response (
         template_path, context_dict, context, *( render_args or () )
      )
   # --- end of wrapped (...) ---

   wrapped.__name__ = func.__name__.lstrip ( '_' )
   wrapped.__doc__  = func.__doc__
   wrapped.__dict__.update ( func.__dict__ )

   return wrapped
# --- end of request_wrapper (...) ---

def _home ( request, context, cdict ):
   # virtual navbar item
   cdict ['active_navbar_item'] = "home"
   return ( GET_TEMPLATE_RELPATH("home"), () )
# --- end of _index (...) ---

def _config_home ( request, context, cdict ):
   set_active_navbar_item ( cdict, "config" )
   return ( GET_TEMPLATE_RELPATH("config/home"), () )

def _pkgrules_home ( request, context, cdict ):
   set_active_navbar_item ( cdict, "pkgrules" )
   return ( GET_TEMPLATE_RELPATH("pkgrules/home"), () )

def _deprules_home ( request, context, cdict ):
   set_active_navbar_item ( cdict, "deprules" )
   return ( GET_TEMPLATE_RELPATH("deprules/home"), () )

def _deprules_add ( request, context, cdict ):
   return ( GET_TEMPLATE_RELPATH("deprules/home"), () )

def _deprules_edit ( request, context, cdict ):
   return ( GET_TEMPLATE_RELPATH("deprules/home"), () )



home = request_wrapper ( _home )

config_home = request_wrapper ( _config_home )

pkgrules_home = request_wrapper ( _pkgrules_home )

deprules_home = request_wrapper ( _deprules_home )
deprules_add  = request_wrapper ( _deprules_add )
deprules_edit = request_wrapper ( _deprules_edit )
