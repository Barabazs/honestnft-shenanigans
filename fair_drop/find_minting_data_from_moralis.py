import argparse
from typing import Optional

import pandas as pd

from honestnft_utils import config, constants, misc


def get_all_contract_transfers(
    contract: str,
    blockchain: str,
    cursor: Optional[str] = None,
    have: list = [],
):
    """Download all transfers for a given contract from Moralis.

    :param contract: Contract address
    :param blockchain: Blockchain where the contract is located
    :param cursor: Pagination cursor if known, defaults to None
    :param have: List of transactions already downloaded, defaults to []
    :raises Exception: If the request fails
    :return: A list of all transfers for the contract
    """
    all_data = []

    all_data.extend(have)
    session = misc.mount_session()
    session.headers.update(
        {"Content-type": "application/json", "X-API-KEY": config.MORALIS_API_KEY}
    )
    url = f"https://deep-index.moralis.io/api/v2/nft/{contract}/transfers"
    querystring = {
        "chain": blockchain,
        "format": "decimal",
        "limit": 100,
        "cursor": cursor,
    }

    response = session.get(url, params=querystring)  # type: ignore

    if response.status_code == 200:
        # print(response.text)
        response_content = response.json()
        cursor = response_content.get("cursor")
        # add new data to existing list
        all_data.extend(response_content["result"])

        if cursor is not None:
            return get_all_contract_transfers(contract, blockchain, cursor, all_data)
        else:
            return all_data

    else:
        print(response.text)
        raise Exception(f"Got a {response.status_code} response from the server")


def main(
    collection_name: str,
    contract: str,
    blockchain: str,
) -> None:
    """Main function.

    :param collection_name: Collection name. e.g. Quaks
    :param contract: Contract address
    :param blockchain: Blockchain where the contract is located
    """

    moralis_chain_mapping = {
        "avalanche": "avalanche",
        "binance": "bsc",
        "ethereum": "eth",
        "fantom": "fantom",
        "polygon": "polygon",
    }
    print(f"Fetching mint events for {collection_name}")

    all_data = get_all_contract_transfers(
        contract=contract, blockchain=moralis_chain_mapping[blockchain]
    )

    rarity_db = pd.read_csv(f"{config.RARITY_FOLDER}/{collection_name}_raritytools.csv")

    mint_df = pd.json_normalize(all_data)
    # remove non minting rows
    mint_df = mint_df.loc[mint_df["from_address"] == constants.MINT_ADDRESS]

    # make sure token_id is an integer
    mint_df["token_id"] = mint_df["token_id"].astype(int)

    # add rarity rank to minting data
    mint_df = mint_df.merge(rarity_db, left_on="token_id", right_on="TOKEN_ID")

    # discard unwanted columns
    mint_df = mint_df[
        [
            "transaction_hash",
            "to_address",
            "token_id",
            "from_address",
            "Rank",
            "block_timestamp",
        ]
    ]

    mint_df.drop_duplicates(subset=["token_id"], inplace=True)

    # get matching columns names to HonestNFT csv format
    mint_df.columns = [
        "txid",
        "to_account",
        "TOKEN_ID",
        "current_owner",
        "rank",
        "time",
    ]

    # clean 'time' field to make it compatible with the csv produced by 'find_minting_data.ipynb'
    mint_df["time"] = mint_df["time"].str.replace(".000Z", "", regex=False)
    mint_df = mint_df.sort_values(by=["TOKEN_ID"])
    mint_df.to_csv(
        f"{config.MINTING_FOLDER}/{collection_name}_minting.csv", index=False
    )

    print(f"Finished downloading {mint_df.shape[0]} mint events")


def _cli_parser() -> argparse.ArgumentParser:
    """
    Create the command line argument parser
    """

    parser = argparse.ArgumentParser(description="CLI for pulling NFT metadata.")
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        required=True,
        help="Collection name. e.g. Quaks. This will also be used in the file name.",
    )

    parser.add_argument(
        "--contract",
        type=str,
        default=None,
        required=True,
        help="Contract address",
    )

    parser.add_argument(
        "-b",
        "--blockchain",
        type=str,
        choices=[
            "avalanche",
            "binance",
            "ethereum",
            "fantom",
            "polygon",
        ],
        default="ethereum",
        help="Blockchain where the contract is located. (default: ethereum)",
    )
    return parser


if __name__ == "__main__":
    # Parse command line arguments

    args = _cli_parser().parse_args()

    main(
        collection_name=args.collection,
        contract=args.contract,
        blockchain=args.blockchain,
    )
