*******************
Mopidy-Local-Whoosh
*******************

.. image:: https://img.shields.io/pypi/v/Mopidy-Local-Whoosh.svg
    :target: https://pypi.python.org/pypi/Mopidy-Local-Whoosh/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-Local-Whoosh.svg
    :target: https://pypi.python.org/pypi/Mopidy-Local-Whoosh/
    :alt: Number of PyPI downloads

.. image:: https://travis-ci.org/mopidy/mopidy-local-whoosh.png?branch=master
    :target: https://travis-ci.org/mopidy/mopidy-local-whoosh
    :alt: Travis CI build status

.. image:: https://coveralls.io/repos/mopidy/mopidy-local-whoosh/badge.png?branch=master
   :target: https://coveralls.io/r/mopidy/mopidy-local-whoosh?branch=master
   :alt: Test coverage

Whoosh local library extension.

Status
======

Whoosh support has been an experiment and a proof of concept to test out
the Mopidy APIs for alternate local library support more than anything else.

At this point in time I would not recommend using it as it is not being actively
worked on. If you are interested in fixing this please do get in touch or start
sending pull requests :-)

In the meantime take a look at https://github.com/tkem/mopidy-local-sqlite

Installation
============

Install by running::

    pip install Mopidy-Local-Whoosh

Or, if available, install the Debian/Ubuntu package from `apt.mopidy.com
<http://apt.mopidy.com/>`_.

.. warning::

    This plugin makes no attempts to handle whoosh version changes. We support
    whoosh 2.x, but we you will need to rescan due to internal changes in
    whoosh indexes etc when changing upgrading.


Configuration
=============

Before starting Mopidy, you must change your configuration to switch to using
Mopidy-Local-Whoosh as your preferred local library::

    [local]
    library = whoosh


Once this has been set you can re-scan your library to populate whoosh::

    mopidy local scan


Project resources
=================

- `Source code <https://github.com/adamcik/mopidy-local-whoosh>`_
- `Issue tracker <https://github.com/adamcik/mopidy-local-whoosh/issues>`_
- `Download development snapshot <https://github.com/adamcik/mopidy-local-whoosh/tarball/master#egg=Mopidy-Local-Whoosh-dev>`_


Changelog
=========

v0.1.0 (2014-02-25)
-------------------

- Initial release.
