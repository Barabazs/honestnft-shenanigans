import argparse
import json
import logging
import multiprocessing
import os
import time
from typing import Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from honestnft_utils import chain, config, misc, alchemy

from fair_drop import timer

logger = logging.getLogger("fair_drop.suspicious")


def get_collection_name(contract_address: str) -> str:
    """Get the name of the collection from the contract.

    :param contract_address: Contract address of the collection
    :return: Name of the collection
    """
    try:
        abi = chain.get_contract_abi(address=contract_address)
        abi, contract = chain.get_contract(address=contract_address, abi=abi)

        name_func = chain.get_contract_function(
            contract=contract, func_name="name", abi=abi
        )
        name: str = name_func().call()

        return name

    except Exception as error:
        logger.error("Error while trying to get collection name from contract")
        logger.error(error)
        raise Exception(error)


def is_nft_suspicious(
    nft_url: str, session: requests.Session, selector: str
) -> Optional[Dict]:
    """Download and parse the NFT page to check if it is flagged as suspicious

    :param nft_url: URL of the NFT page
    :param session: A requests.Session object
    :param selector: CSS selector to find the suspicious flag
    :return: A dict with relevant information about the NFT and whether it is suspicious or not
    """
    logger.debug(f"Scraping NFT with link: {nft_url}")
    if selector is None or selector == "":
        logger.error("No selector provided")
        raise Exception("No selector provided")

    try:
        res = session.get(nft_url)
    except requests.exceptions.ChunkedEncodingError as error:
        logger.error(
            f"Error while trying to scrape {nft_url}\nWill retry the request..."
        )
        logger.debug(error)
        return is_nft_suspicious(nft_url, session, selector)

    if res.status_code == 200:

        soup = BeautifulSoup(res.text, "html.parser")
        soup.script.decompose()
        is_suspicious = len(soup.select("i.sc-1gugx8q-0.jMbpKx.material-icons")) > 0

        nft_data = {
            "token_id": nft_url.split("/")[-1],
            "url": nft_url,
            "is_suspicious": is_suspicious,
        }

        if is_suspicious:
            logger.info(f"Found suspicious NFT of URL {nft_url}")

        return nft_data
    elif res.status_code == 404:
        logger.error(f"NFT not found at {nft_url}. Skipping...")
        return None
    else:
        logger.error(f"Error while trying to scrape NFT with link {nft_url}")
        logger.error(res.text)
        return None


def list_collection_nfts_urls(
    contract_address: str,
) -> List[str]:
    """List all OpenSea URLs for the NFTs in a collection

    :param contract_address: Contract address of the collection
    :return: list of the OpenSea URLs of NFTs
    """
    nft_urls = []
    token_ids = alchemy.get_all_token_ids(contract_address)
    if len(token_ids) == 0:
        logger.error("No NFTs found in collection")
        raise Exception("No NFTs found in collection")

    for token_id in token_ids:
        # for i in :
        nft_urls.append(
            f"https://opensea.io/assets/ethereum/{contract_address}/{token_id}"
        )
    return nft_urls


@timer.Timer(text="Executed in {:.2f} seconds")
def main(
    contract_address: str,
    selector: str,
    total_retries: int,
    backoff_factor: int,
    batch_size: int,
    keep_cache: bool,
) -> None:
    """Main function to scrape all NFTs in a collection and check if they are suspicious

    :param contract_address: Contract address of the collection
    :param selector: CSS selector to find the suspicious flag
    :param total_retries: Total number of retries to allow.
    :param backoff_factor: A backoff factor to apply between attempts after the second try.
    :param batch_size: Batch size of NFT URLs to be processed
    """

    logger.basicConfig(
        level="INFO",
        filename=f"{config.SUSPICIOUS_NFTS_FOLDER}/.logs/{contract_address}.log",
        filemode="a",
    )

    session = misc.mount_session(
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        total_retries=total_retries,
        backoff_factor=backoff_factor,
        raise_on_status=False,
        user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0",
    )

    collection_nfts_urls = list_collection_nfts_urls(contract_address=contract_address)

    logger.info(f"Collection contains {len(collection_nfts_urls)} NFTs")

    collection_cache = load_scrape_cache(contract_address)
    logger.info(f"Found {len(collection_cache)} NFTs in collection cache")

    for index, nft in collection_cache.iterrows():
        if nft["url"] in collection_nfts_urls:
            logger.debug(f"NFT to be scraped already in cache. Skipping {nft['url']}")
            collection_nfts_urls.remove(nft["url"])
    logger.info(f"Scraping a list of {len(collection_nfts_urls)} NFTs")

    nft_urls_batches = [
        collection_nfts_urls[i : i + batch_size]
        for i in range(0, len(collection_nfts_urls), batch_size)
    ]
    for index, url_batch in enumerate(nft_urls_batches):
        logger.info(f"Scraped {index * batch_size} NFT URLs so far")

        batch = [(url, session, selector) for url in list(url_batch)]

        with multiprocessing.Pool(multiprocessing.cpu_count() - 1) as p:
            results = p.starmap(is_nft_suspicious, batch)
            results = list(filter(None, results))
            if results == []:
                logger.info("Reached a batch of NFTs not found. Exiting...")
                return

            df = pd.DataFrame(results)
            df.to_csv(
                f"{config.SUSPICIOUS_NFTS_FOLDER}/.cache/{contract_address}.csv",
                mode="a",
                header=False,
                index=False,
            )

    df = pd.read_csv(f"{config.SUSPICIOUS_NFTS_FOLDER}/.cache/{contract_address}.csv")
    total_scraped_urls = df.shape[0]
    if total_scraped_urls != len(collection_nfts_urls):
        logger.warning(
            f"Total scraped NFTs ({total_scraped_urls}) does not match total supply ({len(collection_nfts_urls)})"
        )
        logger.warning("Cache will not be removed. Please retry...")
        keep_cache = True
        raise Exception("Total scraped NFTs does not match total supply")
    else:
        logger.info(f"Finished scraping {df.shape[0]} NFT URLs")

        try:
            collection_name = get_collection_name(contract_address)
        except Exception as e:
            logger.info(
                "Failed to query collection name. File will be saved with contract_address as filename."
            )
            logger.error(e)
            collection_name = contract_address

        with open(f"{config.SUSPICIOUS_NFTS_FOLDER}/{collection_name}.json", "w") as f:
            json.dump(
                {
                    "contract": contract_address,
                    "name": collection_name,
                    "scraped_on": int(time.time()),
                    "data": json.loads(df.to_json(orient="records")),
                },
                f,
            )
        if not keep_cache:
            os.remove(f"{config.SUSPICIOUS_NFTS_FOLDER}/.cache/{contract_address}.csv")


def load_scrape_cache(contract_address: str) -> pd.DataFrame:
    """Loads cache of previously scraped collections, based on CSV files saved.

    :param contract_address: Contract address of the collection
    :return: Either a DataFrame with the scraped NFTs or an empty DataFrame if no cache is found
    """
    cache_file = f"{config.SUSPICIOUS_NFTS_FOLDER}/.cache/{contract_address}.csv"
    try:
        df = pd.read_csv(cache_file)
        return df
    except FileNotFoundError:
        logger.debug("No cache file found. Creating a new one...")
        df = pd.DataFrame(
            columns=[
                "token_id",
                "url",
                "is_suspicious",
            ]
        )
        df.to_csv(cache_file, index=False)
        return df


def _cli_parser() -> argparse.ArgumentParser:
    """
    Create the command line argument parser
    """
    parser = argparse.ArgumentParser(
        description="CLI for scraping NFTs flagged as suspicious on OpenSea."
    )
    parser.add_argument(
        "-c",
        "--contract",
        help="Collection contract address",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--selector",
        help="CSS selector to find the suspicious flag",
        required=True,
        type=str,
    )
    parser.add_argument(
        "-r",
        "--retries",
        help="Number of retry attempts",
        required=False,
        type=int,
        default=3,
    )
    parser.add_argument(
        "--backoff",
        help="Retries backoff parameter for failed requests",
        required=False,
        type=int,
        default=3,
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        help="Batch size of NFT URLs to be processed",
        required=False,
        type=int,
        default=50,
    )
    parser.add_argument(
        "--log",
        help="Set the desired log level",
        required=False,
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--keep-cache",
        help="Keep the cache file after scraping",
        type=misc.strtobool,
        const=True,
        nargs="?",
        default=False,
        choices=[True, False],
    )

    return parser


if __name__ == "__main__":

    args = _cli_parser().parse_args()

    main(
        contract_address=args.contract,
        selector=args.selector,
        total_retries=args.retries,
        backoff_factor=args.backoff,
        batch_size=args.batch_size,
        keep_cache=args.keep_cache,
    )
