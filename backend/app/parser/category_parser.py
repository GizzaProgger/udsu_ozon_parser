import re
import json
import asyncio
import logging
from urllib.parse import urlparse
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, AsyncGenerator

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import httpx
from bs4 import BeautifulSoup  # type: ignore

class Fetcher:
    """Class for fetching web pages content."""

    def __init__(self, browser):
        self.browser = browser
    
    async def fetch_page_content(self, url: str) -> Tuple[str, str]:
        """Fetch page content using a Selenium browser."""
        self.browser.get(url)
        wait = WebDriverWait(self.browser, 30)
        header = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'header')))
        content = self.browser.page_source
        return url, content

    async def fetch_pages_content(self, urls: List[str]) -> AsyncGenerator:
        """Asyncroniously fetch and page's html content from urls."""
        tasks = []
        for url in urls:
            if url.startswith(("http://", "https://")):
                tasks.append(asyncio.create_task(self.fetch_page_content(url)))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))

        for task_result in asyncio.as_completed(tasks):
            fetched_content = await task_result
            url, content = fetched_content
            yield url, content

class ContentParser(Fetcher, ABC):
    """Class for parse page's html content.
    """

    async def get_pages_content(self, urls: List[str]) -> List[Dict]:
        """Asyncroniously get pages' html content and parse it.
        """
        pages_content = []
        async for url, page_html in self.fetch_pages_content(urls):

            logging.debug(
                'Parsing url: %s',
                url
            )
            page_content = self.parse(page_html)
            pages_content.append({url: page_content})

        return pages_content

    @abstractmethod
    def parse(self, page_html: str):
        """Abstract method for parsing html.
        """
        pass


class CategoryParser(ContentParser):
    """Class to get parent (from main page) categories' names and urls.
    """
    PATTERN: str = 'catalogMenu'

    def process_pattern(self, page_json: Dict) -> List[Dict[str, str]]:
        """Process dict of categories.
        """
        page_content = []

        for category in page_json['categories']:
            category_dict = {
                'name': category['title'],
                'url': category['url']
            }
            page_content.append(category_dict)

        return page_content

    def parse(self, page_html: str) -> List[Dict[str, str]]:
        """Find and process tag with given pattern,
        return list of categories.
        """
        soup = BeautifulSoup(page_html, 'lxml')

        tag = soup.find(id=re.compile(self.PATTERN))
        tag_content = tag['data-state']

        page_json = json.loads(tag_content)
        page_content = self.process_pattern(page_json)

        return page_content

    def get_categories(self, url: str) -> List[Dict[str, str]]:
        categories = asyncio.run(self.get_pages_content([url]))
        return categories


class SubcategoryParser(ContentParser):
    """Class to get non-parent categories' names and urls.
    """
    PATTERNS: List[str] = [
        'searchCategorySubtree',
        'catalogHorizontalMenu',
        'objectLine'
    ]

    def process_subtree_pattern(
        self,
        page_json: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """Process dict of categories when pattern 'searchCategorySubtree'.
        """
        page_content = []

        for category in page_json['categories'][0]['categories']:
            try:
                subtree_pattern_category = SubtreePattern(category)
            except Exception:
                continue
            else:
                page_content.append(subtree_pattern_category.as_dict())

        return page_content

    def process_horizontalmenu_pattern(
        self,
        page_json: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """Process dict of categories when pattern 'catalogHorizontalMenu'.
        """
        page_content = []

        for category in page_json['categories']:
            try:
                horiz_pattern_category = HorizontalPattern(category)
            except Exception:
                continue
            else:
                page_content.append(horiz_pattern_category.as_dict())

        return page_content

    def process_objectline_pattern(
        self,
        page_json: Dict[str, List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Process dict of categories when pattern 'objectLine'.
        """
        page_content = []

        for category in page_json['items']:
            try:
                objline_pattern_category = ObjectlinePattern(category)
            except Exception:
                continue
            else:
                page_content.append(objline_pattern_category.as_dict())

        return page_content

    def parse(self, page_html: str) -> List[Dict]:
        """Find and process tag with given pattern,
        return list of categories.
        """
        soup = BeautifulSoup(page_html, 'lxml')
        # Trying to find out what pattern is using on page
        # Сonsequentially check each pattern
        # When pattern found, break
        for pattern in self.PATTERNS:
            tag = soup.find(id=re.compile(pattern))
            if tag:
                break
        else:
            return []

        tag_content = tag['data-state']
        page_json = json.loads(tag_content)

        # Get function for processing depending on found pattern
        process_functions = {
            'searchCategorySubtree': self.process_subtree_pattern,
            'catalogHorizontalMenu': self.process_horizontalmenu_pattern,
            'objectLine': self.process_objectline_pattern
        }

        function = process_functions[pattern]
        page_content = function(page_json)
        return page_content

    def get_subcategories(self, urls: List[str]) -> List[Dict]:
        subcategories = asyncio.run(self.get_pages_content(urls[0:3]))
        return subcategories


class InvalidCategoryError(Exception):
    """Exception raised when invalid category passed.
    """
    pass


class Pattern(ABC):
    """Abstract class for objects that respresents patterns used
    for parsing subcategory pages.
    """

    def __init__(self, category):
        self.name = self.extract_name(category)
        self.url = self.extract_url(category)
        self.sections = self.extract_sections(category)

    @abstractmethod
    def extract_name(self, category):
        """Extract category's name.
        """
        pass

    @abstractmethod
    def extract_url(self, category):
        """Extract category's urls.
        """
        pass

    @abstractmethod
    def extract_sections(self, category):
        """Extract category's children categories (sections).
        """
        pass

    @staticmethod
    def add_slash_to_end(url):
        if url and url[-1] != '/':
            url = '{}/'.format(url)
        return url

    @staticmethod
    def remove_query(url):
        return urlparse(url).path

    def get_cleaned_url(self, url):
        """Clean url after extracting.
        """
        url = self.remove_query(url)
        return self.add_slash_to_end(url.strip())

    def filter_sections(self, sections):
        """Filter out section categories to avoid duplicates.
        """
        unique_urls = set()
        unique_urls.add(self.url)

        filtered_sections = []

        for section in sections:
            url = section['url']
            if url in unique_urls:
                continue
            else:
                filtered_sections.append(section)
                unique_urls.add(url)

        return filtered_sections

    def as_dict(self):
        """Display pattern object as dictionary.
        """
        return {
            'name': self.name,
            'url': self.url,
            'sections': self.sections
        }


class ObjectlinePattern(Pattern):
    """Represents pattern 'objectLine'.
    """

    def extract_name(self, category):
        if 'title' not in category:
            raise InvalidCategoryError
        return category['title']

    def extract_url(self, category):
        if 'link' not in category:
            raise InvalidCategoryError
        url = category['link']
        return self.add_slash_to_end(url)

    def extract_sections(self, category):
        return []


class SubtreePattern(Pattern):
    """Represents pattern 'searchCategorySubtree'.
    """

    def extract_name(self, category):
        if 'info' not in category or 'name' not in category['info']:
            raise InvalidCategoryError
        return category['info']['name']

    def extract_url(self, category):
        if 'info' not in category or 'urlValue' not in category['info']:
            raise InvalidCategoryError
        url = '/category/{}'.format(category['info']['urlValue'])
        return self.get_cleaned_url(url)

    def extract_sections(self, category):
        result = []
        sections = category.get('categories')
        if not sections:
            return result

        for section in sections:
            try:
                name = self.extract_name(section)
                url = self.extract_url(section)
            except InvalidCategoryError:
                continue
            else:
                result.append({'name': name, 'url': url})

        return self.filter_sections(result)


class HorizontalPattern(Pattern):
    """Represents pattern 'catalogHorizontalMenu'.
    """

    def extract_name(self, category):
        if 'title' not in category:
            raise InvalidCategoryError
        return category['title'].capitalize()

    def extract_url(self, category):
        url = category.get('url')
        if not url or not url.startswith('/category'):
            raise InvalidCategoryError
        return self.get_cleaned_url(url)

    def extract_sections(self, category):
        result = []
        sections = category.get('section')
        if not sections:
            return result

        for section in sections:
            try:
                name = self.extract_name(section)
                url = self.extract_url(section)
            except InvalidCategoryError:
                continue
            else:
                result.append({'name': name, 'url': url})

        return self.filter_sections(result)
