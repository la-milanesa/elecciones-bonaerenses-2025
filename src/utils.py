import json
from typing import Optional
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)
from src.constants import WEB_DRIVER_TIMEOUT


def load_all_cards(driver):
    while True:
        try:
            both_elements = WebDriverWait(driver, WEB_DRIVER_TIMEOUT).until(
                lambda d: (
                    d.find_element(By.XPATH, "//ol[@aria-label='Territorios']"),
                    d.find_element(By.XPATH, ".//button[contains(text(), 'Cargar más')]")
                )
            )
            _, load_more_btn = both_elements
            driver.execute_script("arguments[0].click();", load_more_btn)
        except TimeoutException:
            break
        except NoSuchElementException:
            break


def as_float(percentage_string: Optional[str], delimiter=" %") -> float:
    if percentage_string:
        return float(percentage_string.split(delimiter)[0].replace(',', '.'))
    else:
        raise ValueError(f"Parameter percentage_string should be a str: {type(percentage_string)}")


def as_int(integer_string: Optional[str]) -> int:
    if integer_string:
        return int(integer_string.replace('.', ''))
    else:
        raise ValueError(f"Parameter integer_string should be a str: {type(integer_string)}")


def generate_file(result, _type):
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    if _type == "municipality":
        prefix = f"{_type}_{result['name']}"
    else:
        prefix = _type
    output_file = f"{prefix}_{ts}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Resultados guardados en {output_file}")
