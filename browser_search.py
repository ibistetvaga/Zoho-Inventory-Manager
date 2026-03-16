"""Browser search utilities for opening searches in the default browser."""

import webbrowser
import urllib.parse
import time
from typing import ClassVar


class BrowserSearch:
    """Handles opening search queries in the default browser."""

    # URL Templates for different search engines
    URLS: ClassVar[dict[str, str]] = {
        'google': "https://www.google.com/search?q={query}",
        'google_ai': "https://www.google.com/search?q={query}&udm=50",
        'zoro': "https://www.zoro.com/search?q={query}",
        'grainger': "https://www.grainger.com/search?searchQuery={query}&searchBar=true",
        'ebay': "https://www.ebay.com/sch/i.html?_nkw={query}",
        'amazon': "https://www.amazon.com/s?k={query}",
        'eaton': "https://www.eaton.com/us/en-us/site-search.html.searchTerm${query}.tabs$all.html",
        'tequipment': "https://www.tequipment.net/search/?F_Keyword={query}",
        'lowes': "https://www.lowes.com/search?searchTerm={query}",
    }

    # Display names for sources
    DISPLAY_NAMES: ClassVar[dict[str, str]] = {
        'google': 'Google Search',
        'google_ai': 'Google AI Search',
        'zoro': 'Zoro',
        'grainger': 'Grainger',
        'ebay': 'eBay',
        'amazon': 'Amazon',
        'eaton': 'Eaton',
        'tequipment': 'Tequipment',
        'lowes': "Lowe's",
    }

    @staticmethod
    def _open_search_url(url_template: str, query: str, encode: bool = True) -> bool:
        """Open a search URL in the default browser."""
        if not query or not query.strip():
            return False

        processed_query = urllib.parse.quote(query) if encode else query
        url = url_template.format(query=processed_query)

        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"Error opening URL: {e}")
            return False

    @classmethod
    def open_search(cls, source: str, query: str) -> bool:
        """Open a search for a specific source.

        Args:
            source: Source name ('google', 'google_ai', 'zoro', 'grainger', 'ebay', 'amazon', 'eaton')
            query: The search query

        Returns:
            True if successful, False otherwise
        """
        url_template = cls.URLS.get(source)
        if not url_template:
            print(f"Unknown search source: {source}")
            return False

        # Eaton doesn't use URL encoding
        encode = source != 'eaton'
        return cls._open_search_url(url_template, query, encode)

    @classmethod
    def open_google_search(cls, query: str) -> bool:
        """Open a Google search in the default browser."""
        return cls.open_search('google', query)

    @classmethod
    def open_google_ai_search(cls, query: str) -> bool:
        """Open a Google AI (SGE) search in the default browser."""
        return cls.open_search('google_ai', query)

    @classmethod
    def open_zoro_search(cls, query: str) -> bool:
        """Open a Zoro search in the default browser."""
        return cls.open_search('zoro', query)

    @classmethod
    def open_grainger_search(cls, query: str) -> bool:
        """Open a Grainger search in the default browser."""
        return cls.open_search('grainger', query)

    @classmethod
    def open_ebay_search(cls, query: str) -> bool:
        """Open an eBay search in the default browser."""
        return cls.open_search('ebay', query)

    @classmethod
    def open_amazon_search(cls, query: str) -> bool:
        """Open an Amazon search in the default browser."""
        return cls.open_search('amazon', query)

    @classmethod
    def open_eaton_search(cls, query: str) -> bool:
        """Open an Eaton search in the default browser."""
        return cls.open_search('eaton', query)

    @classmethod
    def open_tequipment_search(cls, query: str) -> bool:
        """Open a Tequipment search in the default browser."""
        return cls.open_search('tequipment', query)

    @classmethod
    def open_lowes_search(cls, query: str) -> bool:
        """Open a Lowe's search in the default browser."""
        return cls.open_search('lowes', query)

    @classmethod
    def open_both_searches(cls, query: str) -> tuple[bool, bool]:
        """Open both Google and Google AI searches in the default browser."""
        return cls.open_google_search(query), cls.open_google_ai_search(query)

    @classmethod
    def search_all_sources(cls, query: str, selected_sources: dict, delay: float = 0.5) -> dict:
        """
        Search across all selected sources with a delay between each to avoid overwhelming the system.
        Returns dict with results for each source.
        """
        results = {}
        for source, enabled in selected_sources.items():
            if enabled:
                success = cls.open_search(source, query)
                results[source] = {'success': success, 'query': query}
                if delay > 0:
                    time.sleep(delay)  # small pause between launches
        return results

    @classmethod
    def open_zoho_books_search(cls, query: str, org_id: str) -> bool:
        """Open Zoho Books web app with a search for the given query.

        Args:
            query: The search term (item name + optional brand)
            org_id: Your Zoho Books organization ID

        Returns:
            True if the browser opened successfully, False otherwise
        """
        if not query or not org_id:
            return False

        # URL-encode the query to be safe (though it will be placed inside JSON)
        encoded_query = urllib.parse.quote(query, safe='')

        # Construct the URL with proper escaping of curly braces in the JSON part
        # The pattern: https://books.zoho.com/app/{org_id}#/inventory/items?filter_by=Status.All&per_page=25&search_criteria={"search_text":"{query}"}&sort_column=name&sort_order=A
        # We need to double the braces inside the f-string to output literal braces.
        url = (f"https://books.zoho.com/app/{org_id}#/inventory/items"
            f"?filter_by=Status.All&per_page=25"
            f"&search_criteria={{%22search_text%22%3A%22{encoded_query}%22}}"
            f"&sort_column=name&sort_order=A")

        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"Error opening Zoho Books URL: {e}")
            return False

    @classmethod
    def get_source_names(cls) -> list[str]:
        """Get list of all available source names."""
        return list(cls.URLS.keys())

    @classmethod
    def get_source_display_name(cls, source: str) -> str:
        """Get display name for a source."""
        return cls.DISPLAY_NAMES.get(source, source.title())
