
fair\_drop.find\_minting\_data\_from\_moralis
=============================================

.. admonition:: Prerequisites

   * API: Moralis API key, see :doc:`/guides/api-keys`
   * file: rarity csv

This module can be used to download minting data from Moralis. This is often the fastest method.
For example, if you want to download the minting data for `Quaks <https://opensea.io/collection/quaks>`_, you simply have to provide the collection name, the contract address and the blockchain (if it isn't on Ethereum mainnet).

.. code-block:: shell

   $ python3 fair_drop/find_minting_data_from_moralis.py --collection Quaks --contract 0x07bbdaf30e89ea3ecf6cadc80d6e7c4b0843c729 --blockchain ethereum



Command Line
------------
.. autoprogram:: fair_drop.find_minting_data_from_moralis:_cli_parser()
   :prog: find_minting_data_from_moralis.py
   :no_description:
   :no_title: 

------------

Internal functions
------------------
.. automodule:: fair_drop.find_minting_data_from_moralis
   :members:
   :undoc-members:
   :show-inheritance:
