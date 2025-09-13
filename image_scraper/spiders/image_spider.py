"""
Spider for scraping images from websites.
Features:
- Crawls entire website to discover all images
- Extracts all images from pages and follows links
- Converts relative URLs to absolute URLs
- Configurable settings for image quality
"""

import scrapy
import json
from urllib.parse import urljoin, urlparse

class ImageSpider(scrapy.Spider):
    name = 'image_spider'
    start_urls = ['https://example.com/']  # Change this to your target website
    
    # Allowed domains to prevent crawling external sites
    allowed_domains = ['example.com', 'www.example.com']  # Change this to your target domain
    
    def __init__(self):
        super().__init__()
        self.found_image_urls = set()  # Track found URLs to avoid duplicates
        self.pages_processed = 0       # Track processed pages
        self.max_pages = 20           # Limit pages to process
        self.previously_downloaded = set()  # Track already downloaded images
        self.load_image_status()      # Load existing downloads

    custom_settings = {
        'ITEM_PIPELINES': {
            'image_scraper.pipelines.EnhancedImagePipeline': 1,
        },
        'IMAGES_STORE': 'downloaded_images',
        'IMAGES_MIN_HEIGHT': 100,  # Skip small images (icons/buttons)
        'IMAGES_MIN_WIDTH': 100,   # Skip small images (icons/buttons)
        'IMAGES_EXPIRES': 0,     # Never expire images
        'MEDIA_ALLOW_REDIRECTS': True,  # Follow redirects for best quality
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Be respectful to servers
        'DOWNLOAD_DELAY': 2,  # Increase delay between requests
        'DEPTH_LIMIT': 1,  # ONLY 1 level deep to prevent loops
        'CLOSESPIDER_PAGECOUNT': 20,  # STOP after processing 20 pages
        'CLOSESPIDER_ITEMCOUNT': 100,  # STOP after finding 100 images
        'DUPEFILTER_DEBUG': True,  # Debug duplicate filtering
        'WAIFU2X_PATH': 'waifu2x-ncnn-vulkan.exe'  # Path to waifu2x executable - CHANGE THIS
    }

    def load_image_status(self):
        """Load status of all processed images to avoid re-downloading."""
        try:
            with open('image_status.json', 'r') as f:
                data = json.load(f)
                image_status = data.get('images', {})
                self.previously_downloaded = set(image_status.keys())
                self.logger.info(f"Loaded {len(self.previously_downloaded)} previously downloaded images")
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.info("No previous image status found - starting fresh")
            self.previously_downloaded = set()

    def parse(self, response):
        """Parse pages and extract images and links."""
        self.pages_processed += 1
        self.logger.info(f"Crawling page {self.pages_processed}: {response.url}")
        
        # Stop if we've processed enough pages
        if self.pages_processed > self.max_pages:
            self.logger.info(f"Reached max pages limit ({self.max_pages}), stopping crawler")
            return
        
        # Extract all image URLs from the current page
        image_urls = []
        new_images_found = 0
        
        # Find images in <img> tags
        for img in response.css('img'):
            src = img.css('::attr(src)').get()
            if src:
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(response.url, src)
                if (self.is_valid_image_url(absolute_url) and 
                    absolute_url not in self.found_image_urls and
                    absolute_url not in self.previously_downloaded):
                    self.found_image_urls.add(absolute_url)
                    image_urls.append(absolute_url)
                    new_images_found += 1
                    self.logger.info(f"Found NEW image: {absolute_url}")
                elif absolute_url in self.previously_downloaded:
                    self.logger.debug(f"Skipping already downloaded image: {absolute_url}")
        
        # Find direct image links in <a> tags
        for link in response.css('a::attr(href)').getall():
            if link:
                absolute_url = urljoin(response.url, link)
                if (self.is_valid_image_url(absolute_url) and 
                    absolute_url not in self.found_image_urls and
                    absolute_url not in self.previously_downloaded):
                    self.found_image_urls.add(absolute_url)
                    image_urls.append(absolute_url)
                    new_images_found += 1
                    self.logger.info(f"Found NEW image link: {absolute_url}")
                elif absolute_url in self.previously_downloaded:
                    self.logger.debug(f"Skipping already downloaded image link: {absolute_url}")
        
        # Yield images if any NEW ones found on this page
        if image_urls:
            yield {
                'image_urls': image_urls
            }
            self.logger.info(f"Found {new_images_found} NEW images on {response.url}")
        else:
            self.logger.info(f"No new images found on {response.url}")
        
        # Stop if we've found enough images
        if len(self.found_image_urls) >= 100:
            self.logger.info(f"Found {len(self.found_image_urls)} images, stopping crawler")
            return
        
        # Follow only a few internal links to continue crawling (limit to prevent loops)
        links_followed = 0
        max_links_per_page = 5  # Limit links per page
        
        for link in response.css('a::attr(href)').getall():
            if links_followed >= max_links_per_page:
                break
                
            if link:
                # Convert to absolute URL
                absolute_link = urljoin(response.url, link)
                
                # Check if it's an internal link and not an image
                if (self.is_internal_link(absolute_link, response.url) and 
                    not self.is_valid_image_url(absolute_link)):
                    links_followed += 1
                    yield response.follow(link, callback=self.parse)
    
    def is_valid_image_url(self, url):
        """Check if URL points to a valid image file."""
        if not url:
            return False
            
        # Common image extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff']
        
        # Skip small icons, buttons, and UI elements
        skip_patterns = [
            'icon', 'button', 'arrow', 'bullet', 'bg_', 'background',
            'spacer', 'pixel', 'transparent', 'clear', 'small',
            'thumb', 'mini', 'tiny', '_s.', '_xs.', '_sm.',
            'favicon', 'logo_small', 'nav_', 'menu_'
        ]
        
        # Check if URL ends with image extension
        url_lower = url.lower()
        
        # Must be an image extension
        if not any(url_lower.endswith(ext) for ext in image_extensions):
            return False
            
        # Skip if URL contains patterns we want to avoid
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
            
        return True
    
    def is_internal_link(self, url, base_url):
        """Check if URL is internal to the domain."""
        try:
            url_domain = urlparse(url).netloc.lower()
            base_domain = urlparse(base_url).netloc.lower()
            
            # Check if it's the same domain or a subdomain
            return (url_domain == base_domain or 
                    url_domain in self.allowed_domains or
                    any(domain in url_domain for domain in self.allowed_domains))
        except:
            return False