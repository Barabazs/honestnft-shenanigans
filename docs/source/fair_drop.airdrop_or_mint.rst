
fair\_drop.airdrop\_or\_mint
============================

.. admonition:: Prerequisites

   * file: minting data csv

This module can be used to analyse minting data and see which transaction was a regular mint event or an airdrop.
For example, if you want to analyse the `Quaks <https://opensea.io/collection/quaks>`_ data, you simply have to provide the collection name.

.. code-block:: shell

   $ python3 fair_drop/airdrop_or_mint.py --collection Quaks

Command Line
------------
.. autoprogram:: fair_drop.airdrop_or_mint:_cli_parser()
   :prog: airdrop_or_mint.py
   :no_description:
   :no_title: 

------------

Internal functions
------------------
.. automodule:: fair_drop.airdrop_or_mint
   :members:
   :undoc-members:
   :show-inheritance:
