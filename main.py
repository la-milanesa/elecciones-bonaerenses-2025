import time
import logging
import argparse
from typing import Optional

from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from tenacity import retry, stop_after_attempt, wait_fixed
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)

from src.driver import with_driver
from src.utils import (
    load_all_cards,
    as_float,
    as_int,
    generate_file,
)
from src.constants import (
    TABLE_TIMEOUT,
    ATTEMPTS,
    RETRY_AFTER,
    SECONDS_TO_SLEEP,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("errors.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)


@retry(
    stop=stop_after_attempt(ATTEMPTS),
    wait=wait_fixed(RETRY_AFTER),
    retry=(lambda exc: isinstance(exc, (TimeoutException, WebDriverException)))
)
@with_driver
def get_table(
    url: str = "",
    headless: bool = True,
    driver: Optional[webdriver.Chrome] = None,
):
    assert driver is not None
    driver.get(url)
    WebDriverWait(driver, TABLE_TIMEOUT).until(
        EC.presence_of_element_located((By.TAG_NAME, "tbody"))
    )

    results = []
    rows = driver.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if cells and row.text != "":
            party = cells[0].text.split("\n")[-1]
            votes = int(cells[1].text)
            percentage = as_float(cells[2].text)
            results.append({
                "party": party,
                "votes": votes,
                "percentage": percentage,
            })
    return results


@retry(
    stop=stop_after_attempt(ATTEMPTS),
    wait=wait_fixed(RETRY_AFTER),
    retry=(lambda exc: isinstance(exc, (TimeoutException, WebDriverException)))
)
@with_driver
def get_school(
    school_name: str,
    url: str = "",
    headless: bool = True,
    driver: Optional[webdriver.Chrome] = None,
):
    assert driver is not None
    driver.get(url)
    load_all_cards(driver)

    response = []
    tables = driver.find_elements(By.XPATH, "//ol[@aria-label='Territorios']//li/a")
    for table in tqdm(
        tables,
        desc=f"[{school_name}] Processing tables",
        total=len(tables),
        leave=False,
    ):
        number = table.find_element(By.XPATH, ".//span[starts-with(@id, 'territoryCard')]").text
        scrutinized = as_float(
            table.find_element(By.XPATH, ".//div[@id='territorios-card-agrupacion-text-esccrutado']")
                .find_elements(By.TAG_NAME, "span")[2].text)
        a_link = str(table.get_attribute("href"))
        response.append({
            "number": number,
            "scrutinized": scrutinized,
            "url": a_link,
            "results": get_table(url=a_link, headless=headless),
        })
    return response


@retry(
    stop=stop_after_attempt(ATTEMPTS),
    wait=wait_fixed(RETRY_AFTER),
    retry=(lambda exc: isinstance(exc, (TimeoutException, WebDriverException)))
)
@with_driver
def get_city(
    city_name: str,
    url: str = "",
    headless: bool = True,
    driver: Optional[webdriver.Chrome] = None,
):
    assert driver is not None
    driver.get(url)
    load_all_cards(driver)

    response = []
    schools = driver.find_elements(By.XPATH, "//ol[@aria-label='Territorios']//li/a")
    for school in tqdm(
        schools,
        desc=f"[{city_name}] Processing schools",
        total=len(schools),
        leave=False,
    ):
        name = school.find_element(By.XPATH, ".//span[starts-with(@id, 'territoryCard')]").text
        scrutinized = as_float(
            school.find_element(By.XPATH, ".//div[@id='territorios-card-agrupacion-text-esccrutado']")
                .find_elements(By.TAG_NAME, "span")[2].text)
        a_link = str(school.get_attribute("href"))
        response.append({
            "name": name,
            "scrutinized": scrutinized,
            "url": a_link,
            "tables": get_school(name, url=a_link, headless=headless),
        })
        time.sleep(SECONDS_TO_SLEEP)
    return response


@retry(
    stop=stop_after_attempt(ATTEMPTS),
    wait=wait_fixed(RETRY_AFTER),
    retry=(lambda exc: isinstance(exc, (TimeoutException, WebDriverException)))
)
@with_driver
def get_municipality(
    url: str = "",
    headless: bool = True,
    driver: Optional[webdriver.Chrome] = None,
):
    assert driver is not None
    driver.get(url)
    load_all_cards(driver)

    municipality_name = driver.find_element(
        By.XPATH,
        "/html/body/div/div/div[1]/div/header/div/div[2]/div/div/div/div[1]/div/div/div/div[2]/a/span",
    ).text

    details_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ver detalles de escrutados"]')
    driver.execute_script("arguments[0].click();", details_btn)

    percentage_span = driver.find_element(By.XPATH, '//*[@id="app"]/div/div[1]/header/div/div[3]/div/div/div/div/div/div[1]/span[2]')
    percentage_scrutinized = as_float(percentage_span.get_attribute("innerHTML"), delimiter="&nbsp;")
    parent_div = percentage_span.find_element(By.XPATH, '..')

    voters_data = parent_div.find_element(By.XPATH, 'following-sibling::*[2]')\
        .find_element(By.CLASS_NAME, "rt-Box").get_attribute("innerHTML").split(" de ")
    voters, total_voters = as_int(voters_data[0]), as_int(voters_data[1])

    cities_data = []
    cities = driver.find_elements(By.XPATH, "//ol[@aria-label='Territorios']//li/a")
    for city in tqdm(
        cities,
        desc=f"[{municipality_name}] Processing cities",
        total=len(cities),
        leave=False,
    ):
        name = city.find_element(By.XPATH, ".//span[starts-with(@id, 'territoryCard')]").text
        scrutinized = as_float(
            city.find_element(By.XPATH, ".//div[@id='territorios-card-agrupacion-text-esccrutado']")
                .find_elements(By.TAG_NAME, "span")[2].text)
        a_link = str(city.get_attribute("href"))
        cities_data.append({
            "name": name,
            "scrutinized": scrutinized,
            "url": a_link,
            "schools": get_city(name, url=a_link, headless=headless),
        })

    return {
        "name": municipality_name,
        "voters": voters,
        "total_voters": total_voters,
        "scrutinized": percentage_scrutinized,
        "cities": cities_data,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrapping from Buenos Aires province election results website")
    subparsers = parser.add_subparsers(dest="type", required=True)
    parser_sen = subparsers.add_parser("senators", help="Get all votes for senators")
    parser_dip = subparsers.add_parser("deputies", help="Get all votes for deputies")
    parser_con = subparsers.add_parser("councilors", help="Get all votes for councilors")
    parser_mun = subparsers.add_parser("municipality", help="Get all votes just for an specific municipality")
    parser_mun.add_argument("--url", required=True, help="Municipality URL to process")

    parser.add_argument("--headless", type=str, default="true",
                        help="Execute on headless mode (true/false). Default: true")

    args = parser.parse_args()
    headless = args.headless.lower() in ("true", "1", "yes")

    match args.type:
        case "senators":
            pass
        case "deputies":
            pass
        case "councilors":
            pass
        case "municipality":
            if not hasattr(args, "url") or not args.url:
                raise parser.error("--url is mandatory when 'type' is 'municipality'")
            result = get_municipality(url=args.url, headless=headless)
        case _:
            raise parser.error("--type should be one of the following options: 'senators', 'deputies', 'councilors' or 'municipality'")

    generate_file(result, args.type)
