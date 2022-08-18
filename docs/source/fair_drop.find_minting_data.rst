
fair\_drop.find\_minting\_data
==============================

.. admonition:: Prerequisites

   * API: OpenSea API key, see :doc:`/guides/api-keys`
   * file: rarity csv

This module can be used to download minting data from OpenSea.
For example, if you want to download the minting data for `Quaks <https://opensea.io/collection/quaks>`_, you simply have to provide the collection name, the contract address and the time before which to find events.


.. code-block:: shell

   $ python3 fair_drop/find_minting_data.py --collection Quaks --contract 0x07bbdaf30e89ea3ecf6cadc80d6e7c4b0843c729 --before_time 2021-09-02T00:00


Command Line
------------
.. autoprogram:: fair_drop.find_minting_data:_cli_parser()
   :prog: find_minting_data.py
   :no_description:
   :no_title: 

------------

Internal functions
------------------
.. automodule:: fair_drop.find_minting_data
   :members:
   :undoc-members:
   :show-inheritance:

