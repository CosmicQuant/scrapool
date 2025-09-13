"""
Defines the image scraper items.
"""

import scrapy


class ImageScraperItem(scrapy.Item):
    """Item for storing image URLs and paths."""
    image_urls = scrapy.Field()
    images = scrapy.Field()