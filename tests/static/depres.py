# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# ready-to-use input for testing dependency resolution

EMPTY_STR = ""

RESOLVE_AS_IGNORED = lambda  s: ( s, EMPTY_STR )
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
      ( "p3 =2.1.0", "cat/pkg:1" ),
      ( "p4 =5.4.3.2.1", "cat/pkg:5=" ),
      ( "p5 =4", "cat/pkg:99/2" ),
   ),

   'selfdeps': (
   ),

   'and-split' : (
      ( "GDAL >= 1.3.1", ">=sci-libs/gdal-1.3.1" ),
      ( "PROJ.4 (>= 4.4.9)", ">=sci-libs/proj-4.4.9" ),

      (
         'for building from source: GDAL >= 1.3.1 && GDAL < 1.6.0 '
         '(until tested) library and PROJ.4 (proj >= 4.4.9)',
         None
      ),
      (
         'for building from source: GDAL >= 1.3.1 '
         'library and PROJ.4 (>= 4.4.9)',
         ( ">=sci-libs/gdal-1.3.1", ">=sci-libs/proj-4.4.9" ),
      ),
   ),


   'empty': DONT_RESOLVE_TUPLE ( "fftw", ),

   # examples from doc/rst/usage.rst
   'example1': (
      ( "r 2.12", ">=dev-lang/R-2.12" ),
      ( "R(>= 2.14)", ">=dev-lang/R-2.14" ),
      ( "R [<2.10]", "<dev-lang/R-2.10" ),
      ( "r{ !=2.12 }", "( !=dev-lang/R-2.12 dev-lang/R )" ),
      ( "R", "dev-lang/R" ),
      DONT_RESOLVE ( "R (!2)" ),
   ),
   'example2': (
      # depends on DEFAULT_CATEGORY
      ( 'zoo', 'sci-R/zoo' ),
      DONT_RESOLVE ( 'zoo 5' ),
   ),
   'example3': (
      ( 'BLAS/LAPACK libraries', '( virtual/blas virtual/lapack )' ),
   ),
   'example4': (
      RESOLVE_AS_IGNORED ( "see README" ),
      RESOLVE_AS_IGNORED ( "read INSTALL" ),
      RESOLVE_AS_IGNORED (
         "Will use djmrgl or rgl packages for rendering if present"
      ),
   ),
   'example5': (
      ( "fftw", "sci-libs/fftw" ),
      DONT_RESOLVE ( "fftw 2" ),
      ( "fftw 2.1", "sci-libs/fftw:2.1" ),
      ( "fftw 2.1.2", "sci-libs/fftw:2.1" ),
      ( "fftw 2.1.3", "sci-libs/fftw:2.1" ),
      ( "fftw [  <=2.2]", "sci-libs/fftw:2.2" ),
      ( "fftw (=3.0)", "sci-libs/fftw:3.0" ),
      # !!
      ( "fftw (=3.2)", "sci-libs/fftw:3.2" ),
      DONT_RESOLVE ( "fftw ( != 5 )" ),
   ),
   'example6': (
      ( "fftw", "sci-libs/fftw" ),
      DONT_RESOLVE ( "fftw 2" ),
      ( "fftw 2.1", "sci-libs/fftw:2.1" ),
      ( "fftw 2.1.2", "sci-libs/fftw:2.1" ),
      ( "fftw 2.1.3", "sci-libs/fftw:2.1" ),
      DONT_RESOLVE ( "fftw [  <=2.2]" ),
      ( "fftw (=3.0)", "sci-libs/fftw:3.0" ),
      # !!
      DONT_RESOLVE ( "fftw (=3.2)" ),
      DONT_RESOLVE ( "fftw ( != 5 )" ),
   ),
   'example5+6' : 'example5',
   'example7': (
      DONT_RESOLVE ( "fftw (=2.1)" ),
      ( "fftw (=3.0)", "sci-libs/fftw:3.0" ),
      ( "fftw (=3.1)", "sci-libs/fftw:3.0" ),
      ( "fftw (=3.2)", "sci-libs/fftw:3.0" ),
      ( "fftw (=3.3)", "sci-libs/fftw:3.0" ),
   ),

}

# dict <ruleset name>, <m-tuples>( <rule file line>^m )
DEPRES_RULES = {
   'fftw': (
      'sci-libs/fftw {', 'fftw', '}',
      '~sci-libs/fftw:wide_match:+v:s=..1 :: fftw',
      '~sci-libs/fftw :: fftw',
   ),

   'slot0': (
      '~cat/pkg:open:* :: p0',
      '~cat/pkg:open:  :: p1',
      '~cat/pkg:with_version:s=..1:/2 :: p2',
      '~cat/pkg:s=1 :: p3',
      '~cat/pkg:= :: p4',
      '~cat/pkg:s=i99:/i2 :: p5',
   ),

   'selfdeps': (
      '@selfdep', '~other-cat/pkg :: zoo',
   ),

   'and-split': (
      '~sci-libs/gdal :: gdal',
      '~sci-libs/proj {', 'proj', 'proj.4', '}',
   ),

   'empty': (),

   # examples from doc/rst/usage.rst
   'example1': (
      '~dev-lang/R :: R',
   ),
   'example2': (
      'zoo',
   ),
   'example3': (
      '( virtual/blas virtual/lapack ) {',
         'BLAS/LAPACK libraries',
      '}',
   ),
   'example4': (
      '! {',
         'see README',
         'read INSTALL',
         'Will use djmrgl or rgl packages for rendering if present',
      '}',
   ),
   'example5': (
      '~sci-libs/fftw:wide_match:s=0..1 :: fftw',
   ),
   'example6': (
      '~sci-libs/fftw:wide_match:s=0..1:restrict=2.1,3.0: :: fftw',
   ),
   'example7': (
      '~sci-libs/fftw:wide_match:s=i3.0:r=3.0,3.1,3.2,3.3 :: fftw',
   ),
}

# dict <dataset name>, <iterable|str <ruleset name(s)>>
#  datasets not listed here default to <dataset name> as <ruleset name>
DEPRES_INCLUDE = {
   'example5+6': ( "example5", "example6", ),
}

#DEPRES_FAULTY_RULES=...
