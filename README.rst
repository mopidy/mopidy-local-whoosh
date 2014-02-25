****************************
Mopidy-Local-Whoosh
****************************

.. image:: https://pypip.in/v/Mopidy-Local-Whoosh/badge.png
    :target: https://pypi.python.org/pypi/Mopidy-Local-Whoosh/
    :alt: Latest PyPI version

.. image:: https://pypip.in/d/Mopidy-Local-Whoosh/badge.png
    :target: https://pypi.python.org/pypi/Mopidy-Local-Whoosh/
    :alt: Number of PyPI downloads

.. image:: https://travis-ci.org/mopidy/mopidy-local-whoosh.png?branch=master
    :target: https://travis-ci.org/mopidy/mopidy-local-whoosh
    :alt: Travis CI build status

.. image:: https://coveralls.io/repos/mopidy/mopidy-local-whoosh/badge.png?branch=master
   :target: https://coveralls.io/r/mopidy/mopidy-local-whoosh?branch=master
   :alt: Test coverage

Whoosh local library extension.


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
----------------------------------------

- Initial release.
