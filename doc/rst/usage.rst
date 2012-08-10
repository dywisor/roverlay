.. _roverlay-9999.ebuild:
   http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=blob;f=roverlay-9999.ebuild;hb=refs/heads/master

.. _roverlay git repo:
   http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary

.. _omegahat's PACKAGES file:
   http://www.omegahat.org/R/src/contrib/PACKAGES

.. _ConfigParser:
   http://docs.python.org/library/configparser.html

.. sectnum::

.. contents::


==============
 Introduction
==============

*roverlay* is
Automatically Generated Overlay of R packages;;
GSoC Project;;
<>;;


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

* for generating documentation files: python docutils > 0.8.1

* hardware requirements (when the default configuration):

   disk
      * a filesystem that supports symbolic links
      * 50-55GB disk space for the R packages when using the default
        R package hosts (CRAN with archive, BIOC, R-Forge and Omegahat)
      * <a lot of inodes for PORTAGE_RO_DISTDIR/__tmp__ and the overlay>

   memory
      up to 600MB which depends on the amount of processed packages and the
      write mechanism in use. The amount can be halved (approximately) when
      using a slower one.

   other
      No other hardware requirements. <as a measurement for computing speed,
      i/o requirements:
      overlay creation takes 3-4h on modern desktop hardware with overlay
      writing to a tmpfs, most time is spent for Manifest creation>

---------------------
 via emerge (Gentoo)
---------------------

A live ebuild is available, `roverlay-9999.ebuild`_.
Add it to your local overlay and run ``emerge roverlay``, which will also
install all config files into */etc/roverlay*.

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

* *DESTDIR* defaults to ''

* *BINDIR*, defaults to *DESTDIR*/usr/local/bin

* *PYMOD_FILE_LIST*, which lists the installed python module files
  and defaults to './roverlay_files.list'

* *PYTHON*, name of path of the python interpreter that will run 'setup.py',
  defaults to 'python'


*roverlay* can later be uninstalled with ``make uninstall``.

.. Note::

   Make sure to include ``--record <somewhere>/roverlay_files.list``
   when running ``./setup.py install`` manually,
   which can later be used to safely remove the python module files with
   ``xargs rm -vrf < <somewhere>/roverlay_files.list``.
   The *make* targets take care of this.

.. Warning::

   Support for this installation type is limited - it won't install/create
   any config files!

---------------------------------------
 Using *roverlay* without installation
---------------------------------------

This is possible, too. Make sure to meet the dependencies as listed
in Prerequisites_.
Then, simply clone the git repository to a local directory that
will later be referenced as the *R Overlay src directory*.

.. Note::
   You'll have to cd into the *R Overlay src directory* before running
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
      This sets the log file.

      Example: LOG_FILE = ~/roverlay/log/roverlay.log

   LOG_LEVEL
      This sets the global log level, which is used for all log formats
      that don't override this option. Valid log levels are
      ``DEBUG``, ``INFO``, ``WARN``/``WARNING``, ``ERROR`` and ``CRITICAL``.

      Example: LOG_LEVEL = WARNING

   LOG_LEVEL_CONSOLE
      This sets the console log level.

      Example: LOG_LEVEL_CONSOLE = INFO

   LOG_LEVEL_FILE
      This sets the log level for file logging.

      Example: LOG_LEVEL_FILE = ERROR

The following options should also be set (most of them are required), but
have reasonable defaults if *roverlay* has been installed using *emerge*:

   SIMPLE_RULES_FILE
      This option lists the dependency rules files that should be used
      for dependency resolution (see
      `Dependency Rules / Resolving Dependencies`_).
      Although not required, this option is **recommended** since ebuild
      creation without dependency rules fails for most R packages.

      Example: SIMPLE_RULES_FILE = ~/roverlay/config/simple-deprules.d

   REPO_CONFIG
      A list with one or more files that list repositories
      (see `Repositories / Getting Packages`_).
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


For details and a full configuration reference, see `Configuration Reference`_.

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
fine.

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
   <while ebuild write time decreases by ???>.

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

----------------------------
 Providing a package mirror
----------------------------

<No recommendations at this time. The current ManifestCreation implementation
creates a directory *<distfiles root>/__tmp__* with symlinks to all packages,
which could be used for providing packages, but this may change
in near future since external Manifest creation is too slow
(takes >60% of overlay creation time).>


=========================
 Implementation Overview
=========================

This section gives a basic overview of how *roverlay* works.

<how *roverlay* basically works:>

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

---------------------------------
 Repositories / Getting Packages
---------------------------------

*roverlay* is capable of downloading R packages via rsync and http,
and is able to use any packages locally available. The concrete method used
to get and use the packages is determined by the concrete
**type of a repository** and that's what this section is about.

++++++++++++++++++++++++++++++++
 A word about repo config files
++++++++++++++++++++++++++++++++

Repo config files use ConfigParser_ syntax (known from ini files).

Each repo entry section is introduced with ``[<repo name>]`` and defines

* how *roverlay* can download the R packages from a repo
  and where they should be stored
* how ebuilds can download the packages (-> *SRC_URI*)
* repo type specific options, e.g. whether the repo supports package file
  verification

Such options are declared with ``<option> = <value>`` in the repo entry.

The common options for repository entries are:

* *type*, which declares the repository type. Available types are:

   * rsync_
   * websync_repo_
   * websync_pkglist_
   * local_

  Defaults to *rsync*

* *src_uri*, which declares how ebuilds can download the packages. Some repo
  types use this for downloading, too.

* *directory*, which explicitly sets the package directory to use.
  The default behavior is to use `DISTFILES_ROOT`_/<repo name>


.. Hint::
   Repo names are allowed contain slashes, which will be respected when
   creating the default directory.

.. _rsync:

+++++++++++++
 Rsync repos
+++++++++++++

Runs *rsync* to download packages. Automatic sync retries are supported if
*rsync*'s exit codes indicates chances of success.
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

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 Getting packages from a repository that supports http only
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

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

+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 Getting packages from several remotes using http and a package list
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

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

Comments are not supported. Assuming that such a package list exists as <at?>
*~/roverlay/config/http_packages.list*, an example entry in the repo config
file would be:

.. code-block:: ini

   [http-packages]
   type    = websync_pkglist
   pkglist = ~/roverlay/config/http_packages.list


This repo type extends the default options by:

* *pkglist*, which sets the package list file. This option is **required**.


.. _local:

+++++++++++++++++++++++++
 Using local directories
+++++++++++++++++++++++++

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

-------------------------------------------
 Dependency Rules / Resolving Dependencies
-------------------------------------------

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

*Mandatory* and *Option* are mutually exclusive.

The *dependency type* of a *dependency string* is determined by the its origin,
i.e. info field in the package's DESCRIPTION file.
The *Suggests* field, for example,
gets the *"package dependency and optional"* type,
whereas the *SystemRequirements* gets *"system dependency and mandatory"*.


+++++++++++++++++++++++++
 Simple Dependency Rules
+++++++++++++++++++++++++

*Simple dependency rules* use a dictionary and string transformations
to resolve dependencies. *Fuzzy simple dependency rules* extend these by
a set of regexes, which allows to resolve many dependency strings that
minimally differ (e.g. only in the required version and/or comments:
`R (>= 2.10)` and `R [2.14] from http://www.r-project.org/`) with a single
dictionary entry.

This is the only rule implementation currently available.

Rule Variants
-------------

default
   The expected behavior of a dictionary-based rule: It matches one or more
   *dependency strings* and resolves them as a *dependency*

ignore
   This variant will ignore *dependency strings*. Technically, it will
   resolve them as **nothing**.

Rule types
----------

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


Rule File Examples
------------------

This sections lists some rule file examples.
See `Rule File Syntax`_ for a formal<precise,..?> description.


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

Rule File Syntax
----------------

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
   *dependency string* per line, and ends with '}'.

   Syntax:
      .. code-block:: text

         [<keychar>]<dependency> {
            <dependency string>
            [<dependency string>]
            ...
         }

Rule Stubs
   There's a shorter syntax for dependencies that are resolved within the
   created overlay. For example, if your OVERLAY_CATEGORY is
   *sci-R*, *zoo* should be resolved as *sci-R/zoo*.
   This rule can be written as a single word, *zoo*. Such stubs are called
   **selfdeps**.

   Syntax:
      .. code:: text

         [<keychar>]<short dependency>

Comments
   start with **#**. There are a few exceptions to that, the *#deptype* and
   *#! NOPARSE* keywords. Comments inside rule blocks are not allowed and
   will be read as normal *dependency strings*.

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


=========================
 Configuration Reference
=========================

------------------
 Dependency Rules
------------------

<merge with basic..overview::deprules>


--------------
 Repositories
--------------

<merge with basic..overview::repo>

-------------
Main Config
-------------

.. _DISTFILES_ROOT:

DISTFILES_ROOT
   <>

The main config file uses shell syntax.

------------------
 Field Definition
------------------

The field definition file uses ConfigParser_ syntax. For an example, see
`default field definition file`_.

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
      Declares that a field's value is a list whose values are separated by
      by ',' or ';'.

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
      are ignored, too, the main difference is the log message.

.. Note::

   It won't be checked whether a flag is known or not.


==========
 Appendix
==========

-------------------------------
 Default Field Definition File
-------------------------------

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
