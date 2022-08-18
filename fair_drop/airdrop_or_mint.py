import argparse
import concurrent.futures
import os

import numpy as np
import pandas as pd
from web3 import Web3

from honestnft_utils import config


def analyse_transaction(df_series: pd.Series, endpoint: str) -> str:
    """Analyse a transaction and return wether it is a mint or an airdrop

    :param df_series: A pandas Series containing the transaction data
    :param endpoint: The web3 endpoint to use
    :return: "Airdrop" or "Mint"
    """
    txid = df_series["txid"].values[0]
    recipient = df_series["to_account"].values[0]
    w3 = Web3(Web3.HTTPProvider(endpoint))
    transaction = w3.eth.get_transaction(transaction_hash=txid)
    if transaction["from"].lower() == recipient.lower():
        return "Mint"
    else:
        return "Airdrop"


def analyse_dataframe(df: pd.DataFrame, endpoint: str) -> pd.DataFrame:
    """Given a DataFrame, calls analyse_transaction for each transaction and return the result

    :param df: The DataFrame to analyse
    :param endpoint: The web3 endpoint to use
    :return: The DataFrame with the airdrop_or_mint column added
    """

    grouped = df.groupby(["txid", "to_account"])
    df = df.merge(
        grouped.apply(analyse_transaction, endpoint).rename("airdrop_or_mint"),
        on=["txid", "to_account"],
    )
    return df


def main(collection: str, endpoint: str) -> None:
    """
    Main function

    :param collection: Collection name. e.g. Quaks
    :param endpoint: The web3 endpoint to use
    """

    mint_path = f"{config.MINTING_FOLDER}/{collection}_minting.csv"
    minting_df = pd.read_csv(mint_path)

    # Drop existing airdrop_or_mint column
    minting_df.drop(columns=["airdrop_or_mint"], inplace=True, errors="ignore")

    threads = min(32, os.cpu_count() + 4)  # type: ignore
    df_results = []
    splitted_df = np.array_split(ary=minting_df, indices_or_sections=threads)

    with concurrent.futures.ProcessPoolExecutor(max_workers=threads) as executor:
        results = [
            executor.submit(analyse_dataframe, df=df, endpoint=endpoint)
            for df in splitted_df
        ]
        for result in concurrent.futures.as_completed(results):
            try:
                df_results.append(result.result())
            except Exception as exc:
                print(exc)
                raise

    combined_df = pd.concat(df_results)

    combined_df.sort_values(by=["TOKEN_ID"], ascending=True, inplace=True)

    combined_df.to_csv(mint_path, index=False)

    # Count number of mints and airdrops
    mints = combined_df[combined_df["airdrop_or_mint"] == "Mint"].shape[0]
    airdrops = combined_df[combined_df["airdrop_or_mint"] == "Airdrop"].shape[0]
    print(f"Mints: {mints}")
    print(f"Airdrops: {airdrops}")
    print(f"Total: {mints + airdrops}")


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
        help="Collection name. e.g. Quaks",
    )

    parser.add_argument(
        "-b",
        "--blockchain",
        type=str,
        choices=[
            "arbitrum",
            "avalanche",
            "binance",
            "ethereum",
            "fantom",
            "optimism",
            "polygon",
        ],
        default="ethereum",
        help="Blockchain where the contract is located. (default: ethereum)",
    )

    return parser


if __name__ == "__main__":

    # Parse command line arguments

    args = _cli_parser().parse_args()

    if args.blockchain == "arbitrum":
        endpoint = config.ARBITRUM_ENDPOINT
    elif args.blockchain == "avalanche":
        endpoint = config.AVALANCHE_ENDPOINT
    elif args.blockchain == "binance":
        endpoint = config.BINANCE_ENDPOINT
    elif args.blockchain == "ethereum":
        endpoint = config.ENDPOINT
    elif args.blockchain == "fantom":
        endpoint = config.FANTOM_ENDPOINT
    elif args.blockchain == "optimism":
        endpoint = config.OPTIMISM_ENDPOINT
    elif args.blockchain == "polygon":
        endpoint = config.POLYGON_ENDPOINT
    else:
        raise ValueError(f"Blockchain {args.blockchain} not supported")

    main(collection=args.collection, endpoint=endpoint)
