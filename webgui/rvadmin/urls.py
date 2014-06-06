# R overlay -- admin webgui, urls
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from django.conf.urls import patterns, url

from rvadmin import const
from rvadmin import views

def urlify ( s, *args, **kwargs ):
   return url(s.replace ( '/', '/+' ), *args, **kwargs)


urlpatterns = patterns (
   '',
   url(r'^$', views.home, name="home"),

   #urlify(const.CONFIG_SUBURL,   views.config_home,   name="config_home"),

   urlify(const.DEPRULES_SUBURL + r'(?:home/)?$', views.deprules_home, name="deprules_home"),
   #urlify(const.DEPRULES_SUBURL + "add/$", views.deprules_add, name="deprules_add"),
   #urlify(const.DEPRULES_SUBURL + "edit/$", views.deprules_edit, name="deprules_edit"),

   #urlify(const.PKGRULES_SUBURL, views.pkgrules_home, name="pkgrules_home"),


)
