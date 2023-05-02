import os
import logging
from typing import List, Dict

from .category_parser import CategoryParser, SubcategoryParser
from .items_parser import ItemsParser

from fake_useragent import UserAgent  # type: ignore

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.proxy import Proxy, ProxyType

import atexit

log_filename = 'logs/parser.log'
os.makedirs(os.path.dirname(log_filename), exist_ok=True)

logging.basicConfig(
    filename=log_filename,
    filemode='w',
    level=logging.DEBUG
)


class Parser:
    def __init__(self) -> None:
        self.browser = self.get_browser()
        self.category_parser = CategoryParser(self.browser)
        self.subcategory_parser = SubcategoryParser(self.browser)
        # self.items_parser = ItemsParser()

    def get_browser(self) -> webdriver:
        """Return a Selenium browser."""
        PROXY_HOST = '94.242.54.126'
        PROXY_PORT = '24397'
        PROXY_USER = 'KaBVRBKw'
        PROXY_PASS = 'TYQruJSz'

        options = webdriver.ChromeOptions()
        useragent = UserAgent()
        options.add_argument(f'user-agent={useragent.random}')
        # options.add_argument('--headless')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument(f'--proxy-server=http://62.210.209.223:3128')

        # Создаем объект WebDriver с настройками
        browser = webdriver.Remote(
            command_executor='http://172.25.0.5:4444/wd/hub',
            desired_capabilities=webdriver.DesiredCapabilities.CHROME,
            options=options
        )

        def close_browser():
            browser.quit()

        atexit.register(close_browser)

        return browser

    def get_parent_categories(self, url: str) -> List[Dict]:
        return self.category_parser.get_categories(url)

    def get_subcategories(self, urls: List[str]) -> List[Dict]:
        return self.subcategory_parser.get_subcategories(urls)

    def get_items(self, url: str) -> List[Dict]:
        return self.items_parser.get_items(url)
