# R overlay -- roverlay package, util, portage regex - wildcard
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util.portage_regex.default as pre_default
#from . import default as pre_default


PAT_WILDCARD_PACKAGE_NAME = pre_default.FMT_PAT_A_PACKAGE_NAME.format (
   a=r'a-zA-Z+*?', b=r'0-9', c=r'-_'
)
PAT_WILDCARD_CATEGORY_NAME = pre_default.FMT_PAT_A_CATEGORY_NAME.format (
   r'a-zA-Z+0-9*?', r'\-_'
)

PAT_WILDCARD_DOT_DIGITS = pre_default.FMT_PAT_DOT_DIGITS.format ( '0-9*?', '.' )
PAT_WILDCARD_VERSION    = (
   # no wildcard support for the optional a-zA-Z at the end of the str
   r'(?P<version>{}[a-zA-Z]?)'.format ( PAT_WILDCARD_DOT_DIGITS )
)
##PAT_WILDCARD_VSUFFIX    = <version suffix not supported>
##                           (using PAT_A_DEP_ATOM_VERSION_SUFFIXES,
##                            which may or may not work)

PAT_WILDCARD_REVISION   = r'(?:r(?P<revision>[0-9*?]+))'


PAT_WILDCARD_PVR = pre_default.FMT_PAT_PVR.format (
   version          = PAT_WILDCARD_VERSION,
   version_suffixes = pre_default.PAT_A_DEP_ATOM_VERSION_SUFFIXES,
   revision         = PAT_WILDCARD_REVISION,
)

PAT_WILDCARD_PN = pre_default.FMT_PAT_PN.format (
   package_name = PAT_WILDCARD_PACKAGE_NAME,
)

PAT_WILDCARD_PF  = pre_default.FMT_PAT_PF.format (
   pn  = PAT_WILDCARD_PN,
   pvr = PAT_WILDCARD_PVR,
)

PAT_WILDCARD_CATEGORY = pre_default.FMT_PAT_CATEGORY.format (
   category_name = PAT_WILDCARD_CATEGORY_NAME
)

PAT_WILDCARD_PACKAGE = pre_default.FMT_PAT_PACKAGE.format (
   category = PAT_WILDCARD_CATEGORY,
   pf       = PAT_WILDCARD_PF
)

RE_WILDCARD_CATEGORY = pre_default.MultiRegexProxy.compile_exact (
      PAT_WILDCARD_CATEGORY
)
RE_WILDCARD_PACKAGE  = pre_default.MultiRegexProxy.compile_exact (
   PAT_WILDCARD_PACKAGE
)


if __name__ == '__main__':
   import sys
   pre_default.regex_main ( RE_WILDCARD_PACKAGE, sys.argv[1:] )
