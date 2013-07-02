# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# ready-to-use input for testing dependency resolution

DONT_RESOLVE       = lambda  s: ( s, None )
DONT_RESOLVE_TUPLE = lambda *S: tuple ( map ( DONT_RESOLVE, S ) )

# dict <dataset name>, <tuple ( <dependency string>, <expected result> )>
#
DEPRES_DATA = {
   'fftw': (
      ( "fftw", "sci-libs/fftw" ),
      ( "fftw 2", ">=sci-libs/fftw-2" ),
      ( "fftw 2.1.5", ">=sci-libs/fftw-2.1.5:2.1" ),
   ),
   'slot0': (
      ( "p0", "cat/pkg:*" ),
      DONT_RESOLVE ( "p0 !=2" ),
      ( "p1", "cat/pkg:=" ),
      ( "p2", "cat/pkg" ),
      DONT_RESOLVE ( "p2 <3" ),
      ( "p2 =2.2.49", "=cat/pkg-2.2.49:2.2/49" ),
      DONT_RESOLVE ( "p2 5" ),
      DONT_RESOLVE ( "p2 5.4" ),
      DONT_RESOLVE ( "p2 !5" ),
      DONT_RESOLVE ( "p2 !=5" ),
      DONT_RESOLVE ( "p3 1." ),
      ( "p3 2.1.0", "cat/pkg:1" ),
      ( "p4 5.4.3.2.1", "cat/pkg:5=" ),
   ),
   'empty': DONT_RESOLVE_TUPLE ( "fftw", ),
}

# dict <ruleset name>, <m-tuples>( <rule file line>^m )
DEPRES_RULES = {
   'fftw': (
      'sci-libs/fftw {', 'fftw', '}',
      '~sci-libs/fftw:+v:s=..1 :: fftw',
      '~sci-libs/fftw :: fftw',
   ),
   'slot0': (
      '~cat/pkg:open:* :: p0',
      '~cat/pkg:open:  :: p1',
      '~cat/pkg:with_version:s=..1:/2 :: p2',
      '~cat/pkg:s=1 :: p3',
      '~cat/pkg:= :: p4',
   ),
   'empty': (),
}

# dict <dataset name>, <iterable|str <ruleset name(s)>>
#  datasets not listed here default to <dataset name> as <ruleset name>
DEPRES_INCLUDE = {
   #"fftw": "fftw",
}

#DEPRES_FAULTY_RULES=...
