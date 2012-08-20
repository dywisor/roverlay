.. |date| date:: %b %d %Y

.. header:: Automatically Generated Overlay of R packages - Manual (|date|)


.. _roverlay-9999.ebuild:
   http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=blob;f=roverlay-9999.ebuild;hb=refs/heads/master

.. _roverlay git repo:
   http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary

.. _git repository: `roverlay git repo`_

.. _omegahat's PACKAGES file:
   http://www.omegahat.org/R/src/contrib/PACKAGES

.. _ConfigParser:
   http://docs.python.org/library/configparser.html

.. sectnum::

.. contents::
   :backlinks: top



==============
 Introduction
==============

*roverlay* is an application that aims to provide integration of R packages
in Gentoo by creating a portage overlay for them.
Naturally, this also requires proper dependency resolution, especially on the
system level which cannot be done by *install.packages()* in R.

The project associated with *roverlay* is called
*Automatically generated overlay of R packages*, the initial work has been
done during the *Google Summer of Code 2012*.

At its current state, *roverlay* is capable of creating a complete overlay
with metadata and Manifest files by reading R packages.
It's also able to work incrementally, i.e. update an existing *R Overlay*.
Most aspects of overlay creation are configurable with text files.

*roverlay* is written in python. There's no homepage available, only a
`git repository`_ that contains the source code.

This document is targeted at

   * overlay maintainers who **use roverlay** to create the R Overlay

     The most relevant chapters are `Installation`_ (2) and
     `Running Roverlay`_ (3). Additionally, have a look at
     `Basic Implementation Overview`_ (4) if you want to know what *roverlay*
     does and what to expect from the generated overlay.

   * *roverlay* maintainers who **control and test overlay creation**,
     e.g. configure which R packages will be part of the generated overlay

     Depending on what you want to configure, chapters 5-8 are relevant,
     namely `Repositories / Getting Packages`_, `Dependency Rules`_,
     `Configuration Reference`_ and `Field Definition Config`_.

     There's another chapter that is only interesting for testing, the
     `Dependency Resolution Console`_ (9), which can be used to interactively
     test dependency rules.

   * *roverlay* code maintainers who want to know **how roverlay works** for
     code improvements etc.

     The most important chapter is `Implementation Overview`_ (10) which has
     references to other chapters (4-8) where required.

It's expected that you already know about *R packages* (basically a tarball)
and some portage basics, e.g. *Depend Atoms* and what an overlay is.


==============
 Installation
==============

---------------
 Prerequisites
---------------

* python >= 2.7 (tested with python 2.7 and 3.2)

* argparse (http://code.google.com/p/argparse)

* rsync (for using rsync repositories)

* for Manifest creation:

  * *ebuild* from portage
  * *true* or *echo* from coreutils or busybox for preventing
    package downloads during Manifest creation (optional)

* for generating documentation files: python docutils >= 0.9

* hardware requirements (when using the default configuration):

   disk
      * 50-55GB disk space for the R packages
      * a filesystem that supports symbolic links
      * there will be many small-sized files (ebuilds),
        so a filesystem with lots of inodes and a small block size
        may be advantageous

   memory
      up to 600MB which depends on the amount of processed packages and the
      write mechanism in use. The amount can be halved (approximately) when
      using a slower one.

   time
      Expect 3-6h execution time, depending on computing and I/O speed.

---------------------
 via emerge (Gentoo)
---------------------

A live ebuild is available, `roverlay-9999.ebuild`_.
Add it to your local overlay and run ``emerge roverlay``, which also installs
all necessary config files into */etc/roverlay*.

---------------------
 Manual Installation
---------------------

After installing the dependencies as listed in `Prerequisites`_,
clone the `roverlay git repo`_ and then
install *roverlay* and its python modules:

.. code-block:: sh

   git clone git://git.overlays.gentoo.org/proj/R_overlay.git

   cd R_overlay && make install

``make install`` also accepts some variables, namely:

* *DESTDIR*

* *BINDIR*, defaults to *DESTDIR*/usr/local/bin

* *PYMOD_FILE_LIST*, which lists the installed python module files
  and defaults to './roverlay_files.list'

* *PYTHON*, name or path of the python interpreter that is used to run
  'setup.py', defaults to 'python'


*roverlay* can later be uninstalled with ``make uninstall``.

.. Note::

   Make sure to include ``--record <somewhere>/roverlay_files.list``
   when running ``./setup.py install`` manually,
   which can later be used to safely remove the python module files with
   ``xargs rm -vrf < <somewhere>/roverlay_files.list``.
   The *make* targets take care of this.

.. Warning::

   Support for this installation type is limited - it doesn't create/install
   any config files!

---------------------------------------
 Using *roverlay* without installation
---------------------------------------

This is possible, too.
Make sure to meet the dependencies as listed in Prerequisites_.
Then, simply clone the git repository to a local directory that is referenced
as the *R Overlay src directory* from now on.

.. Note::
   You have to *cd* into the *R Overlay src directory* before running
   *roverlay* to ensure that the python modules can be imported correctly.

   You can work around this by setting up a wrapper script:

   .. code-block:: sh

      #!/bin/sh
      # /usr/local/bin/roverlay.sh
      # example wrapper script for roverlay
      cd ${ROVERLAY_SRC:-~/roverlay/src} && ./roverlay.py $*


==================
 Running Roverlay
==================

------------------------------
 Required configuration steps
------------------------------

*roverlay* needs a configuration file to run.
If you've installed *roverlay* with *emerge*, it will look for the config
file in that order:

1. *<current directory>/R-overlay.conf*
2. *~/.R-overlay.conf*
3. */etc/roverlay/R-overlay.conf*,
   which is part of the installation but has to be modified.

Otherwise, an example config file is available in the *R Overlay src directory*
and *roverlay* will only look for *R-overlay.conf* in the current directory.

The config file is a text file with '<option> = <value>' syntax.
Some options accept multiple values (e.g. <option> = file1, file2), in which
case the values have to be enclosed
with quotes (-> ``<option> = "file1 file2"``).


The following options should be set before running *roverlay*:

   OVERLAY_DIR
      This sets the directory of the overlay that will be created.
      This option is **required** and can be overridden on the command line
      via ``--overlay <directory>``.

      Example: OVERLAY_DIR = ~/roverlay/overlay

   DISTFILES
      This sets the root directory of all per-repo package directories.
      This option is **required** and can be overridden on the command line
      via ``--distroot <directory>``.

      .. Note::

         This directory will also contain a directory *__tmp__*
         with symlinks to all packages which can be used as package mirror,
         see `Providing a package mirror`_.

      Example: DISTFILES = ~/roverlay/distfiles

   LOG_FILE
      This sets the log file. An empty value disables file logging.

      Example: LOG_FILE = ~/roverlay/log/roverlay.log

   LOG_LEVEL
      This sets the global log level, which is used for all log formats
      that don't override this option. Valid log levels are
      ``DEBUG``, ``INFO``, ``WARN``/``WARNING``, ``ERROR`` and ``CRITICAL``.

      Example: LOG_LEVEL = WARNING

      .. Note::

         Be careful with low log levels, especially *DEBUG*.
         They produce a lot of messages that you probably don't want to see
         and increase the size of log files dramatically.

   LOG_LEVEL_CONSOLE
      This sets the console log level.

      Example: LOG_LEVEL_CONSOLE = INFO

   LOG_LEVEL_FILE
      This sets the log level for file logging.

      Example: LOG_LEVEL_FILE = ERROR

The following options should also be set (most of them are required), but
have reasonable defaults if *roverlay* has been installed using *emerge*:

   SIMPLE_RULES_FILE
      This option lists dependency rule files and/or directories with
      such files that should be used for dependency resolution.
      Although not required, this option is **recommended** since ebuild
      creation without dependency rules fails for most R packages.

      Example: SIMPLE_RULES_FILE = ~/roverlay/config/simple-deprules.d

   REPO_CONFIG
      A list with one or more files that list repositories.
      This option is **required** and can be overridden on the command line
      via one or more ``repo-config <file>`` statements.

      Example: REPO_CONFIG = ~/roverlay/config/repo.list

   FIELD_DEFINITION
      The value of this option should point to a field definition file which
      controls how an R package's DESCRIPTION file is read.
      The file supplied by default should be fine.
      This option is **required** and can be overridden on the command line
      via ``--field-definition <file>``.

      Example: FIELD_DEFINITION = ~/roverlay/config/description_fields.conf

   OVERLAY_ECLASS
      This option lists eclass files that should be imported into the overlay
      (into *OVERLAY_DIR*/eclass/) and inherited in all ebuilds.
      Specifying an eclass file that implements the ebuild phase functions
      (e.g. *src_install()*) is highly **recommended**. A default file
      named *R-packages.eclass* should be part of your installation.

      Example: OVERLAY_ECLASS = ~/roverlay/eclass/R-packages.eclass

There's another option that is useful if you want to create new dependency
rules, LOG_FILE_UNRESOLVABLE_, which will write all unresolvable dependencies
to the specified file (one dependency string per line).

+++++++++++++++++++++++++++++++++++++++++++++++++
 Extended Configuration / Where to go from here?
+++++++++++++++++++++++++++++++++++++++++++++++++

Proceed with `Running it`_ if you're fine with the default configuration
and the changes you've already made, otherwise the following chapters are
relevant and should provide you with the knowledge to determine the ideal
configuration.

Repositories
   See `Repositories / Getting Packages`_, which describes how repositories
   can be configured.

Dependency Rules
   See `Dependency Rules`_, which explains how dependency rules work and
   how they're written.

Main Config
   See `Configuration Reference`_ for all main config options like log file
   rotation and assistance for writing new *dependency rules*.

Field Definition
   Refer to `Field Definition`_ in case you want to change *how* R packages
   are being read, e.g. if you want the 'Depents' information field (obviously
   a typo) to be understood as 'Depends'.

------------
 Running it
------------

If you've installed *roverlay*, you can run it with ``roverlay``, otherwise
you'll have to cd into the *R overlay src directory* and run ``./roverlay.py``.

In any case, the basic *roverlay* script usage is

.. code::

   roverlay --config <config file> [<options>] [<commands>]

or

.. code::

   roverlay [<options>] [<commands>]

which will search for the config file
as described in `Required configuration steps`_.
The default command is *create*, which downloads the R packages (unless
explicitly forbidden to do so) and generates the overlay. This is the
desired behavior in most cases, so simply running ``roverlay`` should be
fine. See `Basic Implementation Overview`_ if you'd rather like to know
in detail what *roverlay* does before running it.

*roverlay* also accepts some **options**, most notably:

--nosync, --no-sync
   Don't download R packages.

--no-incremental
   Force recreation of existing ebuilds

--immediate-ebuild-writes
   Immediately write ebuilds when they're ready.

   The default behavior is
   to wait for all ebuilds and then write them using ebuild write threads.
   The latter one is faster, but consumes more memory since ebuilds must be
   kept until all packages have been processed.
   Test results show that memory consumption increases by factor 2 when using
   the faster write mechanism (at ca. 95% ebuild creation success rate),
   <<while ebuild write time decreases by ???>>.

   Summary: Expect 300 (slow) or 600MB (fast) memory consumption when using
   the default package repositories.

--config file, -c file
	Path to the config file

--help, -h
   Show all options


.. Note::
   *--no-incremental* doesn't delete an existing overlay, it will merely
   ignores and, potentially, overwrites existing ebuilds.
   Use *rm -rf <overlay>* to do that.


For **testing** *roverlay*, these **options** may be convenient:

--no-manifest
	Skip Manifest file creation.

	This saves a considerable amount of time
	(>100min when using the default package repositories) at the expense of
	an overlay that is not suitable for production usage.

--no-write
	Don't write the overlay

--show
	Print all ebuilds and metadata to console

--repo-config file, -R file
	Repo config file to use. Can be specified more than once.
	This disables all repo files configured in the main config file.

--distdir directory, --from directory
	Create an overlay using the packages found in *directory*. This disables
	all other repositories. The *SRC_URI* ebuild variable will be invalid!

--overlay directory, -O directory
	Create the overlay at the given position.

For reference, these **commands** are accepted by *roverlay*:

create
	As described above, this will run ebuild, metadata creation, including
	overlay and Manifest file writing.
	This command implies the **sync** command unless the *--nosync* option
	is specified.

sync
	This will download all packages from the configured remotes.

depres_console, depres
   Starts an interactive dependency resolution console that supports rule
   creation/deletion, loading rules from files, writing rules to files
   and resolving dependencies.

   Meant for **testing only**.

   More information can be found in the `DepRes Console`_ section.

----------------------------
 Providing a package mirror
----------------------------

No recommendations available at this time.
The current ManifestCreation implementation creates a directory
*<distfiles root>/__tmp__* with symlinks to all packages, which could be used
for providing packages, but this may change in near future since external
Manifest creation is too slow (takes >60% of overlay creation time).

===============================
 Basic Implementation Overview
===============================

----------------------
 How *roverlay* works
----------------------

These are the steps that *roverlay* performs:

1. **sync** - get R packages using various methods
   (rsync, http, local directory)

2. scan the R Overlay directory (if it exists) for valid ebuilds

3. queue all R packages for ebuild creation

   * all repositories are asked to list their packages which are then added
     to a queue

   * packages may be declined by the overlay creator if they already have
     an ebuild

4. **create** - process each package *p* from the package queue
   (thread-able on a per package basis)

  * read *p*'s DESCRIPTION file that contains information fields
    like 'Depends', 'Description' and 'Suggests'

  * resolve *p*'s dependencies

    * differentiate between *required* and *optional* dependencies
      (for example, dependencies from the 'Depends' field are required,
      while those from 'Suggests' are optional)

    * **immediately stop** processing *p* if a *required* dependency
      cannot be resolved in which case a valid ebuild cannot be created

      See also: `Dependency Resolution`_

  * create an ebuild for *p* by using the dependency resolution results
    and a few information fields like 'Description'

  * **done** with *p* - the overlay creator takes control over *p*
    and may decide to write *p*'s ebuild now (or later)

5. write the overlay

   * write all ebuilds
     (thread-able on a per package basis)

   * write the *metadata.xml* files
     (thread-able on a per package basis)

     * this uses the latest created ebuild available for a package

   * write the *Manifest* files
     (not thread-able)

     * this uses all ebuilds availabe for a package


--------------------------------------------------------------
 Expected Overlay Result / Structure of the generated overlay
--------------------------------------------------------------

Assuming that you're using the default configuration (where possible) and
the *R-packages* eclass file, the result should look like:

.. code-block:: text

   <overlay root>/
   <overlay root>/eclass
   <overlay root>/eclass/R-packages.eclass
   <overlay root>/profiles
   <overlay root>/profiles/categories
   <overlay root>/profiles/repo_name
   <overlay root>/profiles/use.desc
   <overlay root>/sci-R/<many directories per R package>
   <overlay root>/sci-R/seewave/
   <overlay root>/sci-R/seewave/Manifest
   <overlay root>/sci-R/seewave/metadata.xml
   <overlay root>/sci-R/seewave/seewave-1.5.9.ebuild
   <overlay root>/sci-R/seewave/seewave-1.6.4.ebuild


++++++++++++++++++++++++
 Expected Ebuild Result
++++++++++++++++++++++++

Ebuild Template
   .. code-block:: text

      <ebuild header>
      inherit <eclass(es)>

      DESCRIPTION="<the R package's description>"
      SRC_URI="<src uri for the R package>"

      IUSE="${IUSE:-}
         R_suggests
      "
      R_SUGGESTS="<R package suggestions>"
      DEPEND="<build time dependencies for the R package>"
      RDEPEND="${DEPEND:-}
         <runtime dependencies>
         R_suggests? ( ${R_SUGGESTS} )
      "

      _UNRESOLVED_PACKAGES=(<unresolvable, but optional dependencies>)

   Some of the variables may be missing if they're not needed.

   A really minimal ebuild would look like:

   .. code-block:: text

      <ebuild header>
      inherit <eclass(es)>

      SRC_URI="<src uri for the R package>"

Example: seewave 1.6.4 from CRAN:
   The default ebuild header (which cannot be changed) automatically sets
   the ebuild's copyright year to 1999-*<current year>*.

   .. code-block:: sh

      # Copyright 1999-2012 Gentoo Foundation
      # Distributed under the terms of the GNU General Public License v2
      # $Header: $

      EAPI=4
      inherit R-packages

      DESCRIPTION="Time wave analysis and graphical representation"
      SRC_URI="http://cran.r-project.org/src/contrib/seewave_1.6.4.tar.gz"

      IUSE="${IUSE:-}
         R_suggests
      "
      R_SUGGESTS="sci-R/sound
         sci-R/audio
      "
      DEPEND="sci-R/fftw
         sci-R/tuneR
         >=dev-lang/R-2.15.0
         sci-R/rpanel
         sci-R/rgl
      "
      RDEPEND="${DEPEND:-}
         media-libs/flac
         sci-libs/fftw
         media-libs/libsndfile
         R_suggests? ( ${R_SUGGESTS} )
      "

Example: MetaPCA 0.1.3 from CRAN's archive:
   Note the shortened *DESCRIPTION* variable that points to the *metadata.xml*
   file. This happens if the description is too long.

   .. code-block:: sh

      # Copyright 1999-2012 Gentoo Foundation
      # Distributed under the terms of the GNU General Public License v2
      # $Header: $

      EAPI=4
      inherit R-packages

      DESCRIPTION="MetaPCA: Meta-analysis in the Di... (see metadata)"
      SRC_URI="http://cran.r-project.org/src/contrib/Archive/MetaPCA/MetaPCA_0.1.3.tar.gz"

      IUSE="${IUSE:-}
         R_suggests
      "
      R_SUGGESTS="sci-R/doMC
         sci-R/affy
         sci-R/ellipse
         sci-R/pcaPP
         sci-R/MASS
         sci-R/impute
         sci-R/doSMP
         sci-R/GEOquery
      "
      DEPEND="sci-R/foreach"
      RDEPEND="${DEPEND:-}
         R_suggests? ( ${R_SUGGESTS} )
      "

      _UNRESOLVED_PACKAGES=('hgu133plus2.db')


++++++++++++++++++++++++++++++++
 Expected *metadata.xml* Result
++++++++++++++++++++++++++++++++

The *metadata.xml* will contain the full description for the latest version
of a package.

Example: seewave from CRAN
   Note the ' // ' delimiter. It will be used to separate description strings
   if a package has more than one, e.g. one in its *Title* and one in its
   *Description* information field.

   .. code-block:: xml

      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE pkgmetadata SYSTEM "http://www.gentoo.org/dtd/metadata.dtd">
      <pkgmetadata>
         <longdescription>
            Time wave analysis and graphical representation // seewave
            provides functions for analysing, manipulating, displaying,
            editing and synthesizing time waves (particularly sound).  This
            package processes time analysis (oscillograms and envelopes),
            spectral content, resonance quality factor, entropy, cross
            correlation and autocorrelation, zero-crossing, dominant
            frequency, analytic signal, frequency coherence, 2D and 3D
            spectrograms and many other analyses.
         </longdescription>
      </pkgmetadata>


.. _repositories:

=================================
 Repositories / Getting Packages
=================================

*roverlay* is capable of downloading R packages via rsync and http,
and is able to use any packages locally available. The method used to get and
use the packages is determined by the concrete **type of a repository** and
that's what this section is about. It also covers repository configuration.

.. _repo config:

--------------------------------
 A word about repo config files
--------------------------------

Repo config files use ConfigParser_ syntax (known from ini files).

Each repo entry section is introduced with ``[<repo name>]`` and defines

* how *roverlay* can download the R packages from a repo
  and where they should be stored
* how ebuilds can download the packages (-> *SRC_URI*)
* repo type specific options, e.g. whether the repo supports package file
  verification

Such options are declared with ``<option> = <value>`` in the repo entry.

.. _repo config options:

The common options for repository entries are:

* *type* (optional), which declares the repository type.
  Available types are:

  * rsync_
  * websync_repo_
  * websync_pkglist_
  * local_

  Defaults to *rsync*.

* *src_uri* (**required**),
  which declares how ebuilds can download the packages.
  Some repo types use this for downloading, too.

* *directory* (optional),
  which explicitly sets the package directory to use.
  The default behavior is to use `DISTFILES_ROOT`_/<repo name>


.. Hint::
   Repo names are allowed contain slashes, which will be respected when
   creating the default directory.

.. _rsync:

-------------
 Rsync repos
-------------

Runs *rsync* to download packages. Automatic sync retries are supported if
*rsync*'s exit code indicates chances of success.
For example, up to 3 retries are granted if *rsync* returns
*Partial transfer due to vanished source files* which likely happens when
syncing big repositories like CRAN.

This repo type extends the default options by:

* *rsync_uri* (**required**), which specifies the uri used for syncing

* *recursive* (optional), which passes ``--recursive`` to *rsync* if set to
  'yes'

* *extra_rsync_opts* (optional), which passes arbitrary options to *rsync*.
  This can be used include/exclude files or to show progress during transfer.
  Options with whitespace are not supported.

Examples:

* CRAN

   .. code-block:: ini

      [CRAN]
      type             = rsync
      rsync_uri        = cran.r-project.org::CRAN/src/contrib
      src_uri          = http://cran.r-project.org/src/contrib
      extra_rsync_opts = --progress --exclude=PACKAGES --exclude=PACKAGES.gz


* CRAN's archive:

   .. code-block:: ini

      [CRAN-Archive]
      type             = rsync
      rsync_uri        = cran.r-project.org::CRAN/src/contrib/Archive
      src_uri          = http://cran.r-project.org/src/contrib/Archive
      extra_rsync_opts = --progress
      recursive        = yes


.. _websync_repo:

------------------------------------------------------------
 Getting packages from a repository that supports http only
------------------------------------------------------------

This is your best bet if the remote is a repository but doesn't offer
rsync access. Basic digest verification is supported (MD5).
The remote has to have a package list file, typically named
*PACKAGES*, with a special syntax (debian control file syntax).

A package list example,
excerpt from `omegahat's PACKAGES file`_ (as of Aug 2012):

.. code-block:: control

   ...
   Package: CGIwithR
   Version: 0.73-0
   Suggests: GDD
   License: GPL (>= 2)
   MD5sum: 50b1f48209c9e66909c7afb3a4b8af5e

   Package: CodeDepends
   Version: 0.2-1
   Depends: methods
   Imports: codetools, XML
   Suggests: graph, Rgraphviz
   License: GPL
   MD5sum: e2ec3505f9db1a96919a72f07673a2d8
   ...

An example repo config entry for omegahat:

.. code-block:: ini

   [omegahat]
   type    = websync_repo
   src_uri = http://www.omegahat.org/R/src/contrib
   digest  = md5
   #digest = none


This repo type extends the default options by:

* *digest*, which declares that the remote supports digest based package file
  verification. Accepted values are 'md5' and 'none'. Defaults to 'none',
  which disables verification.

* *pkglist_file*, which sets the name of the package list file and defaults
  to PACKAGES

* *pkglist_uri*, which explicitly sets the uri of the package list file.
  Defaults to *src_uri*/*pkglist_file*

None of these options are required.


.. Note::

   The content type of the remote's package list file has to be exactly
   *text/plain*, compressed files are not supported.

.. _websync_pkglist:

---------------------------------------------------------------------
 Getting packages from several remotes using http and a package list
---------------------------------------------------------------------

This is not a real repository type, instead it creates a *local* repository
by downloading single R packages from different remotes.
Its only requirement is that a package is downloadable via http.
Apart from an entry in the repo config file, it also needs a file that lists
one package uri per line:

.. code-block:: text

   ...
   http://cran.r-project.org/src/contrib/seewave_1.6.4.tar.gz
   http://download.r-forge.r-project.org/src/contrib/zoo_1.7-7.tar.gz
   http://www.omegahat.org/R/src/contrib/Aspell_0.2-0.tar.gz
   ...

Comments are not supported. Assuming that such a package list exists at
*~/roverlay/config/http_packages.list*, an example entry in the repo config
file would be:

.. code-block:: ini

   [http-packages]
   type    = websync_pkglist
   pkglist = ~/roverlay/config/http_packages.list


This repo type extends the default options by:

* *pkglist*, which sets the package list file. This option is **required**.


.. _local:

-------------------------
 Using local directories
-------------------------

Using local package directories is possible, too.

Example:

.. code-block:: ini

   [local-packages]
   type      = local
   directory = /var/local/R-packages
   src_uri   = http://localhost/R-packages

This will use all packages from */var/local/R-packages* and assumes
that they're available via *http://localhost/R-packages*.

A local directory will never be modified.

.. Important::

   Using this repo type is **not recommended for production usage** because
   the *SRC_URI* variable in created ebuilds will be invalid unless you've
   downloaded all packages from the same remote in which case
   you should consider using one of the **websync** repo types,
   websync_repo_ and websync_pkglist_.


==================
 Dependency Rules
==================

-------------------------
 Simple Dependency Rules
-------------------------

*Simple dependency rules* use a dictionary and string transformations
to resolve dependencies. *Fuzzy simple dependency rules* extend these by
a set of regular expressions, which allows to resolve many dependency strings
that minimally differ (e.g. only in the required version and/or comments:
`R (>= 2.10)` and `R [2.14] from http://www.r-project.org/`) with a single
dictionary entry.

This is the only rule implementation currently available.

+++++++++++++++
 Rule Variants
+++++++++++++++

default
   The expected behavior of a dictionary-based rule: It matches one or more
   *dependency strings* and resolves them as a *dependency*

ignore
   This variant will ignore *dependency strings*. Technically, it will
   resolve them as **nothing**.

++++++++++++
 Rule types
++++++++++++

Simple Rules
   A simple rule resolves **exact string matches** (case-insensitive).

   Example:
   Given a rule *R* that says "resolve 'R' and 'the R programming language'
   as 'dev-lang/R'", any of these *dependency strings* will be resolved
   as dev-lang/R:

   * r
   * THE R PROGRAMMING LanGuAgE
   * R

Fuzzy Rules
   Fuzzy Rules are **extended Simple Rules**. If the basic lookup
   as described above fails for a *dependency string*,
   they will *try* to resolve it as a **version-relative match**.

   To do this, the *dependency string* will be split into components like
   *dependency name*, *dependency version* and useless comments, which are
   discarded.
   Then, if the *dependency name* matches a dictionary entry, a resolving
   *dependency* will be created.

   Example:
      Given the same rule as in the Simple Rules example, but as fuzzy rule
      "fuzzy-resolve 'R' and 'the R programming language' as 'dev-lang/R'",
      it will resolve any of these *dependency strings*:

      * "r" as "dev-lang/R"
      * "R 2.12" as ">=dev-lang/R-2.12"
      * "The R PROGRAMMING LANGUAGE [<2.14] from http://www.r-project.org/"
        as "<dev-lang/R-2.14"
      * "R ( !2.10 )" as "( dev-lang/R !=dev-lang/R-2.10 )"


++++++++++++++++++++
 Rule File Examples
++++++++++++++++++++

This sections lists some rule file examples.
See `Rule File Syntax`_ for a formal description.


Example 1 - *default* fuzzy rule
   A rule that matches many dependencies on dev-lang/R, for example
   "r 2.12", "R(>= 2.14)", "R [<2.10]", "r{  !2.12 }", and "R", and
   resolves them as '>=dev-lang/R-2.12', '>=dev-lang/R-2.14',
   '<dev-lang/R-2.10', etc.:

   .. code:: text

      ~dev-lang/R :: R


Example 2 - *default* simple rule stub
   A rule that case-insensitively matches 'zoo' and resolves it as 'sci-R/zoo',
   assuming the OVERLAY_CATEGORY is set to 'sci-R':

   .. code:: text

      zoo

   .. Note::

		R Package rules are dynamically created at runtime and therefore not
		needed. Write them only if certain R package dependencies cannot
		be resolved. See *Selfdep* in `Rule File Syntax`_ for details.

Example 3 - *default* simple rule
   A rule that matches several *dependency strings* and resolves them
   as "sci-libs/gdal and sci-libs/proj":

   .. code-block:: text

      ( sci-libs/gdal sci-libs/proj ) {
         for building from source: GDAL >= 1.3.1 && GDAL < 1.6.0 (until tested) library and PROJ.4 (proj >= 4.4.9)
         for building from source: GDAL >= 1.3.1 library and PROJ.4 (proj >= 4.4.9)
         for building from source: GDAL >= 1.3.1 library and PROJ.4(proj >= 4.4.9)
         for building from source: GDAL >= 1.6.0 library and PROJ.4(proj >= 4.4.9)
      }

Example 4 - *ignore* simple rule
   A rule that matches text that should be ignored.
   This is a good way to deal with free-style text found
   in some R package DESCRIPTION files.

   .. code-block:: text

      ! {
         see README
         read INSTALL
         Will use djmrgl or rgl packages for rendering if present
      }


Please see the default rule files for more extensive examples that cover
other aspects like limiting a rule to certain dependency types.
They're found in */etc/roverlay/simple-deprules.d*
if you've installed *roverlay* with *emerge*,
else in *<R Overlay src directory>/simple-deprules.d*.


.. _Dependency Rule File Syntax:

++++++++++++++++++
 Rule File Syntax
++++++++++++++++++

Simple dependency rule files have a special syntax. Each rule is introduced
with the resolving *dependency* prefixed by a *keychar* that sets the rule
type if required. The *dependency strings* resolved by this rule are listed
after a rule separator or within a rule block. Leading/trailing whitespace
is ignored.

Ignore rules
   have only a keychar but no *dependency*.

Keychars
   set the rule type.

   * **!** introduces a *ignore* simple rule
   * **~** introduces a *default* fuzzy rule
   * **%** introduces a *ignore* fuzzy rule

   Anything else is not treated as keychar and thus introduces a *default*
   simple rule.

Keywords
   There are two keywords that control how a rule file is read.

   The important one is the *#deptype <dependency type>* directive that
   defines that all rules until the next *deptype* directory or end of file,
   whatever comes first, will only match *dependency strings*
   with the specified *dependency type*.

   Available dependency types choices are

   * *all* (no type restrictions)
   * *pkg* (resolve only R package dependencies)
   * *sys* (resolve only system dependencies)

   The other keyword is *#! NOPARSE* which stops parsing of a rule file.

Dependencies
   are strings that are recognized by portage as **Dynamic DEPENDs**
   (see the ebuild(5) man page).

   Examples:

      * dev-lang/R
      * ( media-libs/tiff >=sci-libs/fftw-3 )
      * >=x11-drivers/nvidia-drivers-270


   .. Note::

      The fuzzy rule types support **DEPEND Atom Bases** only.

   .. Warning::

      Dependency strings cannot start with *~* as it is a keychar.
      Use braces *( ~... )* to work around that.


Single line rules
   resolve exactly one *dependency string*. Their rule separator is ' :: '.

   Syntax:
      .. code:: text

         [<keychar>]<dependency> :: <dependency string>

Multi line rules
   resolve several *dependency strings*.
   Their rule block begins with '{' + newline, followed by one
   *dependency string* per line, and ends with '}' in a separate line.

   Syntax:
      .. code-block:: text

         [<keychar>]<dependency> {
            <dependency string>
            [<dependency string>]
            ...
         }

   .. Note::

      Technically, this rule syntax can be used to specify rules with
      zero or more *dependency strings*. An empty rule doesn't make much sense,
      though.

Comments
   start with **#**. There are a few exceptions to that, the *#deptype* and
   *#! NOPARSE* keywords. Comments inside rule blocks are not allowed and
   will be read as normal *dependency strings*.

Selfdep
   This is another name for *dependency strings* that are resolved by an
   R package with the same name, which is also part of the overlay being
   created.

   Example: *zoo* is resolved as *sci-R/zoo*, assuming that `OVERLAY_CATEGORY`_
   is set to *sci-R*

   Writing selfdep rules is not necessary since *roverlay* automatically
   creates rules for all known R packages (see `Dynamic Selfdep Rule Pool`_
   for details).

   There are a few exceptions to that in which case selfdep rules have to
   be written:

   * The *dependency string* is assumed to be a system dependency (not an
     R package). This is likely a "bug" in the DESCRIPTION file of the
     R package being processed.

   * The R package name is not ebuild-name compliant (e.g. contains the '.'
     char, which is remapped to '_'.).
     Most *char remap* cases are handled properly, but there may be a few
     exceptions.

   .. Caution::

      Writing unnecessary selfdep rules slows dependency resolution down!
      Each rule will exist twice, once as *dynamic* rule and once as
      the written one.


Rule Stubs
   There's a shorter syntax for selfdeps.
   For example, if your OVERLAY_CATEGORY is *sci-R*,
   *zoo* should be resolved as *sci-R/zoo*.
   This rule can be written as a single word, *zoo*.

   Syntax:
      .. code:: text

         [<keychar>]<short dependency>


=========================
 Configuration Reference
=========================

The main config file uses '<option> = <value>' syntax, comment lines start
with **#**. Variable substitution ("${X}") is not supported. Quotes around
the value are optional and allow to span long values over multiple lines.
Whitespace is ignored, file **paths must not contain whitespace**.

Some options have value type restrictions. These *value types* are used:

log_level
   Value has to be a log level. Available choise are *DEBUG*, *INFO*, *WARN*,
   *WARNING*, *ERROR* and *CRITICAL*.

bool
   Value is a string that represents a boolean value.

   This table illustrates which value strings are accepted:

   +--------------------------------+----------------------+
   | string value                   | boolean value        |
   +================================+======================+
   | y, yes, on, 1, true, enabled   | *True*               |
   +--------------------------------+----------------------+
   | n, no, off, 0, false, disabled | *False*              |
   +--------------------------------+----------------------+
   | *<any other value>*            | **not allowed**      |
   +--------------------------------+----------------------+


There are also some implicit *value types*:

list
   This means that a option has several values that are separated by
   whitespace. Quotation marks have to be used to specify more than one
   value.

file, dir
   A value that represents a file system location will be expanded ('~' will
   be replaced by the user's home etc.).
   Additionaly the value has to be a file (or directory) if it exists.

<empty>
   Specifying empty values often leads to errors if an option has value type
   restrictions. It's better to comment out options.


The following sections will list all config entries.

--------------
 misc options
--------------

.. _DISTFILES:

DISTFILES
   Alias for DISTFILES_ROOT_.

.. _DISTFILES_ROOT:

DISTFILES_ROOT
   The root directory of per-repository package directories. Repos will create
   their package directories in this directory unless they specify another
   location (see `repo config options`_).

   This option is **required**.

.. _DISTROOT:

DISTROOT
   Alias for DISTFILES_ROOT_.


-----------------
 overlay options
-----------------

.. _ECLASS:

ECLASS
   Alias to OVERLAY_ECLASS_.

.. _OVERLAY_CATEGORY:

OVERLAY_CATEGORY
   Sets the category of created ebuilds. There are no value type restrictions
   for this option, but values with a slash */* lead to errors.

   Defaults to *sci-R*.

.. _OVERLAY_DIR:

OVERLAY_DIR
   Sets the directory of the overlay that will be created.

   This option is **required**.

.. _OVERLAY_ECLASS:

OVERLAY_ECLASS
   A list of eclass files that will be imported into the overlay and inherited
   in all created ebuilds.
   Note that overlay creation fails if any of the specified eclass files
   cannot be imported.
   Eclass files must end with '.eclass' or have no file extension.

   Defaults to <not set>, which means that no eclass files will be used.
   This is **not useful**, since created ebuilds rely on an eclass for phase
   functions like *src_install()*.

.. _OVERLAY_KEEP_NTH_LATEST:

OVERLAY_KEEP_NTH_LATEST
   Setting this option to a value > 0 enables keeping of max. *value* ebuilds
   per R package. All others will be removed.

   Defaults to <not set>, which disables this feature and keeps all ebuilds.

.. _OVERLAY_NAME:

OVERLAY_NAME
   Sets the name of the created overlay that will be written into
   *OVERLAY_DIR/profiles/repo_name*. This file will be rewritten on every
   *roverlay* run that includes the *create* command.

   Defaults to *R_Overlay*.

--------------------
 other config files
--------------------

Some config config options are split from the main config file for various
reasons:

* no need for modification in most cases, e.g. the `field definition`_ file
* special syntax that is not compatible with the main config file,
  e.g. the `dependency rule file syntax`_

The paths to these files have to be listed in the main config file and
can be overridden with the appropriate command line options.

.. _FIELD_DEFINITION:

FIELD_DEFINITION
   Path to the field definition file that controls how the *DESCRIPTION* file
   of R packages is read.

   This option is **required**.

.. _FIELD_DEFINITION_FILE:

FIELD_DEFINITION_FILE
   Alias to FIELD_DEFINITION_.

.. _REPO_CONFIG:

REPO_CONFIG
   A list of one or more repo config files.

   This option is **required**.

.. _REPO_CONFIG_FILE:

REPO_CONFIG_FILE
   Alias to REPO_CONFIG_.

.. _REPO_CONFIG_FILES:

REPO_CONFIG_FILES
   Alias to REPO_CONFIG_.

.. _SIMPLE_RULES_FILE:

SIMPLE_RULES_FILE
   A list of files and directories with dependency rules.
   Directories will be non-recursively scanned for rule files.

   This option is **not required, but recommended** since *roverlay* cannot do
   much without dependency resolution.

.. _SIMPLE_RULES_FILES:

SIMPLE_RULES_FILES
   Alias to SIMPLE_RULES_FILE_.

---------
 logging
---------

.. _LOG_DATE_FORMAT:

LOG_DATE_FORMAT
   The date format (ISO8601) used in log messages.

   Defaults to *%F %H:%M:%S*.

.. _LOG_ENABLED:

LOG_ENABLED
   Globally enable or disable logging. The value has to be a *bool*.
   Setting this option to *True* allows logging to occur, while *False*
   disables logging entirely.
   Log target such as *console* or *file* have to be enabled
   to actually get any log messages.

   Defaults to *True*.

.. _LOG_LEVEL:

LOG_LEVEL
   Sets the default log level. Log targets that don't have their own log
   level set will use this value.

   Defaults to <not set> - all log targets will use their own defaults

+++++++++++++++++
 console logging
+++++++++++++++++

.. _LOG_CONSOLE:

LOG_CONSOLE
   Enables/Disables logging to console. The value has to be a *bool*.

   Defaults to *True*.

.. _LOG_FORMAT_CONSOLE:

LOG_FORMAT_CONSOLE
   Sets the format for console log messages.

   Defaults to *%(levelname)-8s %(name)-14s: %(message)s*.

.. _LOG_LEVEL_CONSOLE:

LOG_LEVEL_CONSOLE
   Sets the log level for console logging.

   Defaults to *INFO*.

++++++++++++++
 file logging
++++++++++++++

.. _LOG_FILE:

LOG_FILE
   Sets the log file. File logging will be disabled if this option does not
   exist or is commented out even if LOG_FILE_ENABLED_ is set to *True*.

   Defaults to <not set>.

.. _LOG_FILE_BUFFERED:

LOG_FILE_BUFFERED
   Enable/Disable buffering of log entries in memory before they're written
   to the log file. Enabling this reduces I/O blocking, especially when using
   low log levels. The value must be a *bool*.

   Defaults to enabled.

.. _LOG_FILE_BUFFER_COUNT:

LOG_FILE_BUFFER_COUNT
   Sets the number of log entries to buffer at most. Can be decreased to
   lower memory consumption when using log entry buffering.

   Defaults to *250*.

.. _LOG_FILE_ENABLED:

LOG_FILE_ENABLED
   Enables/Disable file logging. The value has to be a bool.

   Defaults to enabled, in which case file logging is enabled if LOG_FILE_
   is set, else disabled.

.. _LOG_FILE_FORMAT:

LOG_FILE_FORMAT
   Sets the format used for log messages written to a file.

   Defaults to *%(asctime)s %(levelname)-8s %(name)-10s: %(message)s*.

.. _LOG_FILE_LEVEL:

LOG_FILE_LEVEL
   Sets the log level for file logging.

   Defaults to *WARNING*.

.. _LOG_FILE_ROTATE:

LOG_FILE_ROTATE
   A *bool* that enables/disables log file rotation. If enabled, the log file
   will be rotated on every script run and max. LOG_FILE_ROTATE_COUNT_ log
   files will be kept.

   Defaults to disabled.

.. _LOG_FILE_ROTATE_COUNT:

LOG_FILE_ROTATE_COUNT
   Sets the number of log files to keep at most.

   Defaults to *3* and has no effect if LOG_FILE_ROTATE_ is disabled.

--------------------------------------------------------------------
 options for debugging, manual dependency rule creation and testing
--------------------------------------------------------------------

.. _DESCRIPTION_DIR:

DESCRIPTION_DIR
   A directory where all description data read from an R package will be
   written into. This can be used to analyze/backtrack overlay creation
   results.

   Defaults to <not set>, which disables writing of description data files.

.. _EBUILD_PROG:

EBUILD_PROG
   Name or path of the ebuild executables that is required for (external)
   Manifest file creation. A wrong value will cause ebuild creation late,
   which is a huge time loss, so make sure that this option is properly set.

   Defaults to *ebuild*, which should be fine in most cases.

.. _LOG_FILE_UNRESOLVABLE:

LOG_FILE_UNRESOLVABLE
   A file where all unresolved dependency strings will be written into
   on *roverlay* exit. Primarily useful for creating new rules.

   Defaults to <not set>, which disables this feature.

.. _RSYNC_BWLIMIT:

RSYNC_BWLIMIT
   Set a max. average bandwidth usage in kilobytes per second.
   This will pass '--bwlimit=<value>' to all rsync commands.

   Defaults to <not set>, which disables bandwidth limitation.


.. _Field Definition:

=========================
 Field Definition Config
=========================

The field definition file uses ConfigParser_ syntax and defines
how an R package's DESCRIPTION file is read.
See the next section, `default field definition file`_,  for an example.

Each information field has its own section which declares a set of options
and flags. Flags are case-insensivitve options
without a value - they're enabled by listing them.

.. _field option:
.. _field options:

Known field options:

   .. _field option\: default_value:

   default_value
      Sets the default value for a field, which implies that any read
      DESCRIPTION file will contain this field, either with the value read
      from the file or (as fallback) the default value.
      Disables the `'mandatory' field flag`_.

   .. _field option\: allowed_value:

   allowed_value
      Declares that a field has a value whitelist and adds the value to that
      list (preserves whitespace).

   .. _field option\: allowed_values:

   allowed_values
      Declares that a field has a value whitelist and adds the values to
      that list (values are separated by whitespace).

   .. _field option\: alias_withcase:
   .. _field option\: alias:

   alias_withcase, alias
      Declares case-sensitive field name aliases. This can be used to fix
      'typos', e.g. *Suggest* and *Suggests* both mean *Suggests*.

   .. _field option\: alias_nocase:

   alias_nocase
      Same as `field option: alias`_, but aliases are case-insensitive.

   .. _field option\: flags:

   flags
      List of `field flags`_. Note that any option without a value is treated
      as flag.

.. _field flags:
.. _field flag:

Known field flags:

   .. _field flag\: joinValues:

   joinValues
      Declares that a field's value is one string even if it spans over
      multiple lines.
      The lines will be joined with a single space character ' '.
      The default behavior is to merge lines.

   .. _field flag\: isList:

   isList
      Declares that a field's value is a list whose values are separated
      by ',' and/or ';'.

   .. _field flag\: isWhitespaceList:

   isWhitespaceList
      Declares that a field's value is a list whose values are separated by
      whitespace. Has no effect if `field flag: isList` is set.

   .. _field flag\: mandatory:
   .. _'mandatory' field flag:

   mandatory
      Declares that a field is required in *all* DESCRIPTION files.
      This means that R packages without that field are considered as unusable,
      i.e. ebuild creation fails early.
      This flag is (effectively) useless in conjunction with
      `field option: default_value`_ unless the default value evaluates to
      False (e.g. is an empty string).


   .. _field flag\: ignore:

   ignore
      Declares that a field is known but entirely ignored. Unknown fields
      are ignored, too, the main difference is the emitted log message if
      such a field is found.

.. Note::

   It won't be checked whether a flag is known or not.


.. _default field definition file:

--------------------------------------------
 Example: The default field definition file
--------------------------------------------

This is the default field definition file (without any ignored fields):

.. code-block:: ini

   [Description]
   joinValues

   [Title]
   joinValues

   [Suggests]
   alias_nocase = Suggests, Suggest, %Suggests, Suggets, Recommends
   isList

   [Depends]
   alias_nocase = Depends, Dependencies, Dependes, %Depends, Depents, Require, Requires
   isList

   [Imports]
   alias_nocase = Imports, Import
   isList

   [LinkingTo]
   alias_nocase = LinkingTo, LinkingdTo, LinkinTo
   isList

   [SystemRequirements]
   alias_nocase = SystemRequirements, SystemRequirement
   isList

   [OS_Type]
   alias_nocase   = OS_TYPE
   allowed_values = unix



.. _DepRes Console:

===============================
 Dependency Resolution Console
===============================

As previously stated, the *DepRes Console* is only meant for **testing**.
It's an interactive console with the following features:

* resolve dependencies
* create new dependency rules (**only single line rules**)
* create dependency rules for each R package found in a directory
* load rules from files
* save rules to a file

Rules are managed in a set. These so-called *rule pools* are organized in
a *first-in-first-out* data structure that allows
to create or remove them easily at runtime.

Running ``roverlay depres_console`` will print a welcome message that
lists all available commands and a few usage hints.

For reference, these commands are currently available:

+---------------------+----------------------------------------------------+
| command             | description                                        |
+=====================+====================================================+
| help,               | lists all commands                                 |
| h                   |                                                    |
+---------------------+----------------------------------------------------+
| help --list,        | lists all help topics for which help is available  |
| h --list            |                                                    |
+---------------------+----------------------------------------------------+
| help *<cmd>*,       | prints a command-specific help message             |
| h *<cmd>*           |                                                    |
+---------------------+----------------------------------------------------+
| load *<file|dir>*,  | loads a rule file or a directory with rule files   |
| l *<file|dir>*      | into a new *rule pool*                             |
+---------------------+----------------------------------------------------+
| load_conf,          | loads the rule files listed in the config file     |
| lc                  | into a new *rule pool*                             |
+---------------------+----------------------------------------------------+
| addrule *<rule>*    | creates a new rule and adds it to the topmost,     |
| + *<rule>*          | i.e. latest *rule pool*. This command uses         |
|                     | `Rule File Syntax`_, but multi line rules are      |
|                     | not supported.                                     |
+---------------------+----------------------------------------------------+
| add_pool,           | creates a new *rule pool*                          |
| <<                  |                                                    |
+---------------------+----------------------------------------------------+
| unwind,             | removes the topmost *rule pool* and all of its     |
| >>                  | rules                                              |
+---------------------+----------------------------------------------------+
| resolve *<dep>*,    | tries to resolve the given dependency string and   |
| ? *<dep>*           | prints the result                                  |
+---------------------+----------------------------------------------------+
| print, p            | prints the rules of the topmost *rule pool*        |
+---------------------+----------------------------------------------------+
| print all, p all    | prints the rules of all *rule pools*               |
+---------------------+----------------------------------------------------+
| write *<file>*,     | writes the rules of the topmost *rule pool* into   |
| w *<file>*          | *<file>*                                           |
+---------------------+----------------------------------------------------+
| cd *<dir>*          | changes the working directory, also creates it if  |
|                     | necessary                                          |
+---------------------+----------------------------------------------------+
| scandir *<dir>*,    | creates dependency rules for each R package found  |
| sd *<dir>*          | in *<dir>*                                         |
+---------------------+----------------------------------------------------+
| set, unset          | prints the status of currently (in)active modes    |
+---------------------+----------------------------------------------------+
| set *<mode>*,       | sets or unsets *<mode>*. There's only one mode to  |
| unset *<mode>*      | control, the *shlex mode* which controls how       |
|                     | command arguments are parsed                       |
+---------------------+----------------------------------------------------+
| mkhelp              | verifies that each accessible command has a help   |
|                     | message                                            |
+---------------------+----------------------------------------------------+
| exit, qq, q         | exits the *DepRes Console*                         |
+---------------------+----------------------------------------------------+



Example Session:
   .. code-block::

      == depres console ==
      Run 'help' to list all known commands
      More specifically, 'help <cmd>' prints a help message for the given
      command, and 'help --list' lists all help topics available
      Use 'load_conf' or 'lc' to load the configured rule files

      commands: load, unwind, set, help, >>, load_conf, <<, cd, mkhelp,
      resolve, lc, add_pool, addrule, h, +, l, li, write, p, r, ?, w, print,
      sd, unset, scandir
      exit-commands: q, qq, exit

      cmd % + ~dev-lang/R :: R language
      new rules:
      ~dev-lang/R :: R language
      --- ---
      command succeeded.

      cmd % ? R language
      Trying to resolve ('R language',).
      Resolved as: ('dev-lang/R',)

      cmd % ? R language [ 2.15 ]
      Trying to resolve ('R language [ 2.15 ]',).
      Resolved as: ('>=dev-lang/R-2.15',)

      cmd % ? R
      Trying to resolve ('R',).
      Channel returned None. At least one dep couldn't be resolved.

      cmd % p
      ~dev-lang/R :: R language

      cmd % >>
      Pool removed from resolver.

      cmd % p

      cmd % ? R language
      Trying to resolve ('R language',).
      Channel returned None. At least one dep couldn't be resolved.

      cmd % exit


=========================
 Implementation Overview
=========================

<< there's also in-code documentation for which html files can be generated
using pydoc >>

-------------
 PackageInfo
-------------

*PackageInfo* is the data object that contains all information about an
R package and is created by the owning repository.

After initialization it contains data like

* the path to the R package file
* the origin (repository)
* the SRC_URI
* the package name, version

Not all of these data are really existent, some are calculated. *SRC_URI*,
for example, can often be calculated by combining the origin's "root" src uri
with the package file.

Initialization may fail if the package's name cannot be understood, which is
most likely due to unsupported versioning schemes.

It is then checked whether the newly created *PackageInfo p* can be part of
the overlay. The overlay may refuse to accept *p* if there's already an ebuild
for it. Otherwise, *p* is now part of the overlay and has to pass
*ebuild creation*.

-----------------
 Ebuild Creation
-----------------

Ebuild creation is the process centered around one *PackageInfo* instance *p*
that tries to create an ebuild for it.

#. Read the DESCRIPTION file of *p* R package tarball and stores the
   data in an associative array ('DESCRIPTION field' -> 'data')

#. Call `dependency resolution`_

#. If dependency resolution was successful, dependency ebuild variables are
   created (*DEPEND*, *RDEPEND* and *R_SUGGESTS*, also *IUSE*, *MISSINGDEPS*).
   Otherwise **ebuild creation stops** and *p* is marked as
   *ebuild uncreatable*. The overlay creation may decide to remove *p* in
   order to save memory etc.

#. The *DESCRIPTION* and *SRC_URI* variables are created

#. **done** - Generate the ebuild as text, add it to *p* and mark *p*
   as *ebuild successfully created*


++++++++++++++++++
 Ebuild Variables
++++++++++++++++++

Each ebuild variable is an object whose class is derived from the *EbuildVar*
class. An *EbuildVar* defines its position in the ebuild and  how its text
output should look like. Ebuild text is created by adding ebuild variables
to an *Ebuilder* that automatically sorts them and creates the ebuild.

-----------------------
 Dependency Resolution
-----------------------

Each ebuild creation process has access to the *dependency resolver* that
accepts *dependency strings*, tries to resolve them and returns the result,
either "unresolvable" or the resolving *dependency* as
*Dynamic DEPEND*/*DEPEND Atom*.

The ebuild creation uses *channels* for communication with the *dependency
resolver*, so-called *EbuildJobChannels* that handle the 'high-level'
string-to-string dependency resolution for a set of *dependency strings*.
Typically, one *channel* is used per ebuild variable (DEPEND, RDEPEND and
R_SUGGESTS).

From the ebuild creation perspective, dependency resolution works like this:

#. Collect the *dependency strings* from the DESCRIPTION data and add them
   to the communication *channels* (up to 3 will be used)

#. Wait until all channels are *done*

#. **Stop ebuild creation** if a channel reports that it couldn't resolve
   all *required dependencies*. No ebuild can be created in that case.

#. **Successfully done** - transfer the channel results to ebuild variables


Details about dependency resolution like how *channels* work can be found
in the following sections.

++++++++++++++++++
 Dependency types
++++++++++++++++++

Every *dependency string* has a *dependency type* that declares how a
dependency should be resolved. It has one or more of these properties:

Mandatory
   Ebuild creation fails if the *dependency string* in question cannot
   be resolved.

Optional
   The opposite of *Mandatory*, ebuild creation keeps going even if the
   *dependency string* is unresolvable.

Package Dependency
   This declares that the *dependency string* could be another R package.

System Dependency
   This declares that the *dependency string* could be a system dependency,
   e.g. a scientific library or a video encoder.

Try other dependency types
   This declares that the *dependency string* can be resolved by ignoring its
   dependency type partially. This property allows to resolve
   package dependencies as system dependencies and vice versa.
   Throughout this guide, such property is indicated by *<preferred dependency
   type> first*, e.g. *package first*.

*Mandatory* and *Option* are mutually exclusive.

The *dependency type* of a *dependency string* is determined by its origin,
i.e. info field in the package's DESCRIPTION file.
The *Suggests* field, for example, gets the
*"package dependency only and optional"* type, whereas the *SystemRequirements*
gets *"system dependency, but try others, and mandatory"*.


DESCRIPTION file dependency fields
----------------------------------

The DESCRIPTION file of an R package contains several fields that list
dependencies on R packages or other software like scientific libraries.
This section describes which *dependency fields* are used and how.

.. table:: R package dependency fields

   +--------------------+----------------------+------------------+-----------+
   | dependency field   | ebuild variable      | dependency type  | required  |
   +====================+======================+==================+===========+
   | Depends            | DEPEND               | package first    | *yes*     |
   +--------------------+                      +                  +           +
   | Imports            |                      |                  |           |
   +--------------------+----------------------+------------------+           +
   | LinkingTo          | RDEPEND              | package first    |           |
   +--------------------+                      +------------------+           +
   | SystemRequirements |                      | system first     |           |
   +--------------------+----------------------+------------------+-----------+
   | Suggests           | R_SUGGESTS           | package **only** | **no**    |
   +                    +----------------------+------------------+-----------+
   |                    | _UNRESOLVED_PACKAGES | *unresolvable*   | *n/a*     |
   +--------------------+----------------------+------------------+-----------+

A non-empty *R_SUGGESTS* ebuild variable will enable the *R_suggests* USE
flag. *R_SUGGESTS* is a runtime dependency (a *Dynamic DEPEND* in *RDEPEND*).

Ebuild creation keeps going if an optional dependency cannot be resolved.
This isn't desirable for most *dependency fields*, but extremely
useful for R package suggestions that often link to other repositories or
private homepages.
Such unresolvable dependencies go into the *_UNRESOLVED_PACKAGES* ebuild
variable.
Whether and how this variable is used is up to the eclass file(s).
The default *R-packages eclass* reports unresolvable,
but optional dependencies during the *pkg_postinst()* ebuild phase.

+++++++++++++++++++++++++
 Dependency Environments
+++++++++++++++++++++++++

A *dependency environment* is an object that reflects the whole dependency
resolution process of a single *dependency string*. It usually contains
the *dependency string*, its *dependency type*, information about its
resolution state (*resolved*, *unresolvable*, *to be processed*) and the
resolving resolving *dependency*, if any.

It is initialized by the communication *channel* and processed by the
*dependency resolver*.

+++++++++++++++++++
 EbuildJob Channel
+++++++++++++++++++

The *EbuildJob Channel* is used by the ebuild creation to communicate with
the *dependency resolver*. It is initialized by an ebuild creation process and
realizes a greedy *string to string* dependency resolution.

Its mode of operation is

#. Accept *dependency strings*, create *dependency environments* for them
   and add them to the registered *dependency resolver*.
   The *dependency resolver* may already be resolving the added dependencies.

   Leave this state if the ebuild creation signalizes that all *dependency
   strings* have been added.

#. Tell the *dependency resolver* that this channel is waiting for results.

   The channel using a *blocking queue* for waiting. It expects that the
   *dependency resolver* sends processed *dependency environments* though this
   channel, whether successful or not.

#. Process each received *dependency environment* until all dependencies have
   been resolved or waiting doesn't make sense anymore, i.e. at least one
   *required* dependency could not be resolved.

   * add successful resolved dependencies to the "resolved" list
   * add unresolved, but optional dependencies to the "unresolvable" list
   * any other unresolved dependency is interpreted as "channel cannot satisfy
     the request", the **channel stops waiting** for remaining results.

#. The *channel* returns the result to the ebuild creation.

   It's either a 2-tuple of resolved and unresolvable dependencies or
   "nothing" if the request is not satisfiable, i.e. one or more required
   dependencies are unresolvable.


+++++++++++++++++++++++
 Dependency Rule Pools
+++++++++++++++++++++++

The *dependency resolver* doesn't know *how* to resolve a *dependency string*.
Instead, it searches through a list of *dependency rule pools* that may be
able to do this.

A *dependency rule pool* combines a list of *dependency rules* with a
*dependency type* and is able to determine whether it accepts the type
of a *dependency string* or not.

*Dependency rules* are objects with a "matches" function that returns the
*resolving dependency* if it matches the given *dependency string*, else
it returns "cannot resolve". Note the difference between
"a rule cannot resolve a dep string" and "dep string is unresolvable",
which means that no rule can resolve a particular *dependency string*.

See `Dependency Rules`_ for the concrete rules available.

Rule pools are normally created by reading rule files, but some rule pools
consist of rules that exist in memory only.
These are called **Dynamic Rule Pools** and use runtime data like "all known
R packages" to create rules.


.. _Dynamic Selfdep Rule Pool:

*roverlay* uses one dynamic rule pool, the **Dynamic Selfdep Rule Pool**.
This pool contains rules for all known R packages and is able to resolve
R package dependencies.
By convention, it will never resolve any system dependencies.

+++++++++++++++++++++++++++++
 Dependency Resolver Modules
+++++++++++++++++++++++++++++

The dependency resolver can be extended by modules. Two base types are
available, *channels* and *listeners*.

Listener modules
   Listener modules are used to react on certain dependency resolution
   *events*, e.g. if a *dependency environment* has been found unresolvable <<lang!!>>.
   They usually have access to the *event* and the *dependency environment*.
   However, they cannot begin communication with the *dependency resolver*.

   In the current *roverlay* implementation, a listener module is used to
   report all unresolvable dependencies to a separate file.

Channel modules
   Channel modules interact with the resolver, e.g. queue dependencies for
   resolution, wait for results, and send them to the other end.

   The previously described `EbuildJob Channel`_ is such a channel.

+++++++++++++++++++++
 Dependency Resolver
+++++++++++++++++++++

The dependency resolver puts all parts of dependency resolution together,
*rule pools*, *listeners* and *channels*. It's main task is a loop that
processes all queued *dependency environments* and sends the result back to
their origin (an *EbuildJob channel*).

Besides that, it also offers functionality to register new channels, add
listeners, load rule pools from one or more files etc..
A dependency resolver has to be explicitly closed in which case it will stop
working and notify all listeners about that.

Its mode of operation of operation is best described in pseudo-code:

.. code-block:: text

   while <dependencies queued for resolution>

      depenv   <= get the next dependency environment
      resolved <= False

      # try to resolve depenv

      if <depenv's type contains PACKAGE> and
      <the dynamic selfdep rule pool resolves depenv>

         resolved <= True

      else
         if <a rule pool accepts depenv's type and resolves depenv>
            resolved <= True

         else if <depenv's type contains TRY_OTHER>

            if <a rule pool supports TRY_OTHER and doesn't accept depenv's type
            and resolves depenv>

               resolved <= True
         end if
      end if


      # send the result to depenv's channel

      if resolved
         mark depenv as resolved, add the resolving dependency to it

      else
         mark depenv as unresolvable

      end if

      send depenv to its channel

   end while

The dependency resolver can be **run as thread**, in which case the while loop
becomes "loop until resolver closes".


-----------------------
 Repository Management
-----------------------

Repositories are managed in a list-like object, *RepoList*. Its task is to
provide R package input for overlay creation and implements the following
functionality:

* load repository config from file(s)
* directly add a directory as *local repository*
* *sync* all repos and *nosync* all repos (offline mode)
* create *PackageInfo* instances for R packages from all repositories

++++++++++++++
 Repositories
++++++++++++++

The functionality described above is an abstraction layer that calls the
respective function for each repository and collects the result.
So, while the *RepoList* object knows *what* to do for all repositories,
a repository object *repo* extends this by:

* data

   * repository *type*

   * filesystem directory *distdir* where *repo*'s R packages are stored

   * the *root src_uri*, which is used to determine the *SRC_URI* ebuild
     variable for all packages from *repo*:

     *SRC_URI* = *root src_uri* + '/' + <path of R package relative to *distdir*>

   * other data like the sync status, repository name

* functionality

   * sync/nosync
   * create *PackageInfo* instances for all packages from *repo*
   * status indicators, e.g. if sync was successful

The actual functionality depends on the *repository type*, i.e. the
implementing class. The most basic implementation that provides all common
data, status indicator functions and *PackageInfo* creation is called
*BasicRepo*. It also implements a rather abstract sync function that calls
subclass-specifc *_sync()*/*_nosync()* functions if available.
*BasicRepo*s are used to realize *local repositories*. The other available
repository types, *rsync*, *websync_repo* and *websync_pkglist* derive from
*BasicRepo*.


Adding new repository types
---------------------------

This is best done by creating a new repo class that inherits *BasicRepo*.
The table below shows *BasicRepo*'s subclass awareness (concerning sync)
and what may be changed if required. Most repository types want to define
their own sync functionality and can do so by implementing *_dosync()*:

.. table:: deriving repository types from BasicRepo

   +-------------------+--------------------------------------------------------+
   | function/method   | description                                            |
   +===================+========================================================+
   | _dosync()         | sync packages using a remote, has to return True/False |
   +-------------------+--------------------------------------------------------+
   | _nosync()         | sync packages in offline mode (returns True/False)     |
   +-------------------+--------------------------------------------------------+
   | sync (*online?*)  | implemented by *BasicRepo*, calls _dosync()/_nosync()  |
   |                   | if available, else checks whether *distdir* exists     |
   +-------------------+--------------------------------------------------------+
   | scan_distdir(...) | *BasicRepo*: creates *PackageInfo* instances for all   |
   |                   | R packages in *distdir*. Derived classes can override  |
   |                   | this e.g. if they want to expose only synced packages  |
   +-------------------+--------------------------------------------------------+
   | ready()           | tells whether _dosync()/_nosync() was successful,      |
   |                   | used by *RepoList* to decide whether to call           |
   |                   | scan_distdir() or not. Properly implemented by         |
   |                   | *BasicRepo* when using its sync() method, else needs   |
   |                   | to be overridden.                                      |
   +-------------------+--------------------------------------------------------+
   | __init__()        | has to be implemented if the new class has additional  |
   |                   | data. Refer to in-code documentation and examples.     |
   +-------------------+--------------------------------------------------------+


The *RsyncRepo*, for example, extends *BasicRepo* by rsync-specific data, e.g.
the uri used for rsync, and has its own *__init__()* method. It also
implements *_dosync()*, which calls the *rsync* executable in a filtered
environment that contains only variables like USER, PATH and RSYNC_PROXY.
The other available repository types have an internal-only implementation:

.. table::

   +-----------------+--------------------+----------------------------------+
   | repository type | repository class   | _dosync() implementation         |
   +=================+====================+==================================+
   | local           | BasicRepo          | *not applicable*                 |
   +-----------------+--------------------+----------------------------------+
   | rsync           | RsyncRepo          | **external**, using *rsync* in   |
   |                 |                    | a filtered environment           |
   +-----------------+--------------------+----------------------------------+
   | websync_repo    | WebsyncRepo        | internal, using *urllib*         |
   | websync_pkglist | WebsyncPackageList |                                  |
   +-----------------+--------------------+----------------------------------+

Repository types also need an entry in the repository config loader in order
to be accessible.

---------
 Overlay
---------

*overlay* is roverlay's central data structure that represents a *portage
overlay*. It's organized in a tree structure (overlay root, categories,
package directories) and implements all overlay-related functionality:

* Scan the *portage overlay* for existing ebuilds

* Add *PackageInfo* objects to the overlay. Packages can be declined if
  they already exist as ebuild (incremental overlay).
  Adding multiple packages at once is **thread-safe**.

* List all known packages (filesystem and runtime/memory)

* Write the overlay to its filesystem location

   * initialize the overlay (write the *profiles/* directory,
     import eclass files)
   * Write ebuilds; all *PackageInfo* instances with an ebuild will be written
   * Generate and write metadata
   * Write Manifest files

* Features like `OVERLAY_KEEP_NTH_LATEST`_ make use of ebuild deletion,
  but unconditional ebuild deletion is only available on the package directory
  level

+++++++++++++++++++
 Metadata Creation
+++++++++++++++++++

*metadata.xml* files are created with a tree structure that contains *metadata
nodes*, e.g. '<pkgmetadata>...</pkgmetadata>' and '<use>...</use>' are *nodes*.
The current implementation writes the R package's full description
('Title' and 'Description') into the metadata file.
Metadata creation uses the latest package, i.e. highest version,
for which an ebuild has been created.

+++++++++++++++++++
 Manifest Creation
+++++++++++++++++++

Manifest files are created by calling the *ebuild* executable for each
package directory in a filtered environment where FETCHCOMMAND and
RESUMECOMMAND are set to no-operation. The directories that contain the R
package files are passed in the PORTAGE_RO_DISTDIRS variable and DISTDIR
is set to `DISTFILES_ROOT`_/__tmp__.

------------------
 Overlay Creation
------------------

Overlay creation is the process of creating an overlay for many R packages
and *roverlay*'s main task. More specifically, *OverlayCreation* is an
*R packages -> Overlay (-> overlay in filesystem)* interface.
It accepts *PackageInfo* objects as input, tries to reserve a slot in the
overlay for them, and, if successful, adds them to the work queue.

The work queue is processed by *OverlayWorkers* that run ebuild creation
for a *PackageInfo* object and inform the *OverlayCreation* about the result
afterwards. Overlay creation doesn't stop if an ebuild cannot be created,
instead the event is logged. Running more than one *OverlayWorker* in parallel
is possible.


