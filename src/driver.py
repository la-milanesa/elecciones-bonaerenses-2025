import logging
from functools import wraps
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from src.constants import (
    DRIVER_PATH,
    BROWSER_TIMEOUT,
)


def __get_driver(headless: bool, driver_path: str) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(BROWSER_TIMEOUT)
    driver.set_script_timeout(BROWSER_TIMEOUT)
    return driver


def with_driver(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        driver = None
        try:
            headless = kwargs.get("headless", True)
            driver = __get_driver(headless, DRIVER_PATH)
            kwargs["driver"] = driver
            return func(*args, **kwargs)

        except TimeoutException as error:
            logging.error(f"❌ Timeout on {kwargs.get('url')} | Error: {error}", exc_info=False)
            raise
        except NoSuchElementException as error:
            logging.error(f"❌ NoSuchElement on {kwargs.get('url')} | Error: {error}", exc_info=False)
            raise
        except WebDriverException as error:
            logging.error(f"❌ WebDriver error on {kwargs.get('url')} | Error: {error}", exc_info=False)
            raise
        except Exception as error:
            logging.error(f"❌ Exception on {kwargs.get('url')} | Error: {error}", exc_info=True)
            raise
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logging.error(f"⚠️ Error during driver exit: {e}", exc_info=True)
    return wrapper
