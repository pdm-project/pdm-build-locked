:fa:`code-fork` Which plugin should I use?
******************************************


PDM CLI Plugin
==============

If you only care about reproducible installs after publishing your package, you may use the

:fa:`terminal` :doc:`cli`.

Compatible package managers:

- **pdm** only

Compatible build backends:

- **any PEP 517 compatible** build backend (``setuptools``, ``flit-core``, ``pdm-backend``, ```hatchling`` etc.)

.. code-block::

    pipx install mypkg[locked]


Backend Plugin
==============


If you want to be able to install your package from a local directory or a git repository, you need to use the

:fa:`server` :doc:`backend`.

Compatible package managers:

- **any PEP 621 compatible** package manager (``poetry``, ``flit``, ``pdm``, ``hatch`` etc.)

Compatible build backends:

- **pdm-backend** and **hatchling**

.. code-block::

    pipx install "mypkg[locked] @ git+https://github.com/myorg/mypkg"
