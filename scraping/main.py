import pandas as pd
from fair_drop import suspicious
import logging

formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")


def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


logger = setup_logger("main.py", "main.log")

df = pd.read_csv(
    "contracts.csv"
)

_df = df[df["done"].isna()]
for contract_address in _df["address"].values.tolist():
    df.loc[df["address"] == contract_address, "done"] = "pending"
    print(contract_address)
    logger.info(f"Scraping {contract_address} ...")
    try:
        suspicious.main(
            contract_address=contract_address,
            total_retries=3,
            backoff_factor=3,
            batch_size=50,
            lower_id=None,
            upper_id=None,
            total_supply=None,
            keep_cache=False,
        )

        df.loc[df["address"] == contract_address, "done"] = "ok"
        logger.info(f"Finished scraping {contract_address}")

    except Exception as e:
        logger.warning("Exception while scraping contract: {contract_address}")
        logger.exception(e)
