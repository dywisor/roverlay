# R overlay -- remote, status codes
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

SYNC_SUCCESS = 1
SYNC_FAIL    = 2
SYNC_DONE    = SYNC_SUCCESS | SYNC_FAIL
REPO_READY   = 4
