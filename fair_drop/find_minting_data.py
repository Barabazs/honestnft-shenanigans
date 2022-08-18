import argparse

import pandas as pd

from honestnft_utils import config, constants, opensea


def main(collection: str, contract: str, before_time: str, method: str) -> None:
    """Main function

    :param collection: Collection name. e.g. Quaks
    :param contract: Contract address
    :param before_time: Time before which to find events. Preferably one day after the last mint. e.g. 2021-09-02T00:00 or 1630533600
    :param method: Method used to calculate rarity. e.g. raritytools
    """

    print(f"Fetching mint events for {collection}")
    # Download mint events from OpenSea
    data = opensea.get_opensea_events(
        contract_address=contract,
        account_address=constants.MINT_ADDRESS,
        event_type="transfer",
        occurred_before=before_time,
    )

    df_opensea_events = pd.json_normalize(data)

    df_opensea_events = df_opensea_events.loc[
        df_opensea_events["from_account.address"] == constants.MINT_ADDRESS
    ]

    # Compare downloaded events with rarity data for missing tokens
    rarity_db = pd.read_csv(f"{config.RARITY_FOLDER}/{collection}_{method}.csv")
    df_rarity = pd.DataFrame(rarity_db)

    os_tokens = df_opensea_events["asset.token_id"].astype(int).tolist()
    rar_tokens = df_rarity["TOKEN_ID"].astype(int).tolist()

    set1 = set(rar_tokens)
    set2 = set(os_tokens)

    missing_tokens = list(sorted(set1 - set2))
    if missing_tokens:
        print(
            f"Missing tokens: {missing_tokens}\nTrying to fetch event for missing tokens..."
        )

    missing_data = []
    for token in missing_tokens:
        missing_data.extend(
            opensea.get_opensea_events(
                contract_address=contract,
                account_address=constants.MINT_ADDRESS,
                event_type="transfer",
                occurred_before=before_time,
                token_id=token,
            )
        )

    df_missing_data = pd.json_normalize(missing_data)

    # Merge missing data with rest of data
    df_all = pd.concat([df_opensea_events, df_missing_data])

    # make sure token_id is an integer
    df_all["asset.token_id"] = df_all["asset.token_id"].astype(int)
    rarity_db["TOKEN_ID"] = rarity_db["TOKEN_ID"].astype(int)

    # add rarity rank to minting data
    df_all = df_all.merge(rarity_db, left_on="asset.token_id", right_on="TOKEN_ID")

    # Keep only the columns we want
    df_all = df_all[
        [
            "transaction.transaction_hash",
            "to_account.address",
            "asset.token_id",
            "asset.owner.address",
            "Rank",
            "transaction.timestamp",
        ]
    ]

    # Rename columns
    df_all.columns = [
        "txid",
        "to_account",
        "TOKEN_ID",
        "current_owner",
        "rank",
        "time",
    ]

    print(f"Downloaded {df_all.shape[0]} events")

    mint_db = df_all.sort_values(by=["TOKEN_ID"])
    mint_db.to_csv(f"{config.MINTING_FOLDER}/{collection}_minting.csv", index=False)


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
        "--contract",
        type=str,
        default=None,
        required=True,
        help="Contract address",
    )

    parser.add_argument(
        "--method",
        type=str,
        choices=[
            "raritytools",
        ],
        default="raritytools",
        help="Method used to calculate rarity. e.g. raritytools",
    )
    parser.add_argument(
        "--before_time",
        type=str,
        default=None,
        required=True,
        help="Time before which to find events. Preferably one day after the last mint (e.g. https://etherscan.io/tx/0x206c846d0d1739faa9835e16ff419d15708a558357a9413619e65dacf095ac7a)",
    )

    return parser


if __name__ == "__main__":

    # Parse command line arguments

    args = _cli_parser().parse_args()

    main(
        collection=args.collection,
        contract=args.contract,
        method=args.method,
        before_time=args.before_time,
    )
