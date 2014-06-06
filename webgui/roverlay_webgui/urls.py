# R overlay -- webgui, urls
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import rvadmin.urls

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'roverlay_webgui.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^(?P<home_url>roverlay/admin/)', include(rvadmin.urls)),
)
