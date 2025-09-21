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
    start_urls = [
        'https://whats-on-mombasa.com',
        'https://ticketsasa.com'
    ]
    # Allowed domains to prevent crawling external sites
    allowed_domains = ['whats-on-mombasa.com', 'www.whats-on-mombasa.com', 'ticketsasa.com', 'www.ticketsasa.com']
    
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
        'IMAGES_STORE': r'C:/Users/ADMIN/Desktop/scrape/image_scraper/downloaded_images',
        'IMAGES_MIN_HEIGHT': 100,  # Skip small images (icons/buttons)
        'IMAGES_MIN_WIDTH': 100,   # Skip small images (icons/buttons)
        'IMAGES_EXPIRES': 0,     # Never expire images
        'MEDIA_ALLOW_REDIRECTS': True,  # Follow redirects for best quality
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Be respectful to servers
        'DOWNLOAD_DELAY': 2,  # Reasonable delay for dynamic content
        'DEPTH_LIMIT': 5,  # Allow 3 levels for better pagination
        'CLOSESPIDER_PAGECOUNT': 100,  # STOP after processing 100 pages
        'CLOSESPIDER_ITEMCOUNT': 500,  # STOP after finding 500 images
        'DUPEFILTER_DEBUG': True,  # Debug duplicate filtering
        'WAIFU2X_PATH': r'c:\Users\ADMIN\Desktop\waifu2x-ncnn-vulkan-20250504-windows\waifu2x-ncnn-vulkan-20250504-windows\waifu2x-ncnn-vulkan.exe',  # Path to waifu2x executable
        'RANDOMIZE_DOWNLOAD_DELAY': True,  # Random delays for better scraping
        'DOWNLOAD_TIMEOUT': 30,  # Longer timeout for lazy loading
        'COOKIES_ENABLED': True,  # Enable cookies for session management
        'RETRY_ENABLED': True,    # Enable retries for failed requests
        'RETRY_TIMES': 3,         # Retry failed requests 3 times
    }

    def load_image_status(self):
        """Load status of all processed images to avoid re-downloading."""
        import os
        status_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'image_status.json')
        try:
            with open(status_file, 'r') as f:
                data = json.load(f)
                image_status = data.get('images', {})
                # Use direct URLs as keys
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
        if self.pages_processed > 50:  # Increased for pagination
            self.logger.info(f"Reached max pages limit (50), stopping crawler")
            return
        
        # Extract all image URLs from the current page
        image_urls = []
        new_images_found = 0
        
        # Find images in <img> tags with comprehensive lazy loading support
        for img in response.css('img'):
            # Check all possible image source attributes
            src_attributes = [
                '::attr(src)',
                '::attr(data-src)', 
                '::attr(data-lazy-src)', 
                '::attr(data-original)',
                '::attr(data-url)',
                '::attr(data-image)',
                '::attr(data-img)',
                '::attr(data-lazy)',
                '::attr(data-srcset)',
                '::attr(srcset)'
            ]
            
            for attr in src_attributes:
                image_src = img.css(attr).get()
                if image_src:
                    # Handle srcset (take first URL)
                    if 'srcset' in attr and ',' in image_src:
                        image_src = image_src.split(',')[0].strip().split(' ')[0]
                    
                    # Convert relative URLs to absolute URLs
                    absolute_url = urljoin(response.url, image_src)
                    if (self.is_valid_image_url(absolute_url) and 
                        absolute_url not in self.found_image_urls and
                        absolute_url not in self.previously_downloaded):
                        self.found_image_urls.add(absolute_url)
                        image_urls.append(absolute_url)
                        new_images_found += 1
                        self.logger.info(f"Found NEW image: {absolute_url}")
                    elif absolute_url in self.previously_downloaded:
                        self.logger.debug(f"Skipping already downloaded image: {absolute_url}")
        
        # Look for images in various container elements that might use lazy loading
        lazy_containers = [
            '.event-card img',
            '.event-image img', 
            '.card-img img',
            '.thumb img',
            '.thumbnail img',
            '[data-src]',
            '[data-lazy-src]',
            '.lazy img',
            '.lazyload img'
        ]
        
        for container_selector in lazy_containers:
            for element in response.css(container_selector):
                for attr in ['::attr(src)', '::attr(data-src)', '::attr(data-lazy-src)', '::attr(data-original)']:
                    image_src = element.css(attr).get()
                    if image_src:
                        absolute_url = urljoin(response.url, image_src)
                        if (self.is_valid_image_url(absolute_url) and 
                            absolute_url not in self.found_image_urls and
                            absolute_url not in self.previously_downloaded):
                            self.found_image_urls.add(absolute_url)
                            image_urls.append(absolute_url)
                            new_images_found += 1
                            self.logger.info(f"Found NEW lazy-loaded image: {absolute_url}")
                        break
        
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
        
        # Look for lazy-loaded images in background-image styles
        for element in response.css('[style*="background-image"]'):
            style = element.css('::attr(style)').get()
            if style and 'url(' in style:
                # Extract URL from background-image: url(...)
                import re
                url_match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                if url_match:
                    image_src = url_match.group(1)
                    absolute_url = urljoin(response.url, image_src)
                    if (self.is_valid_image_url(absolute_url) and 
                        absolute_url not in self.found_image_urls and
                        absolute_url not in self.previously_downloaded):
                        self.found_image_urls.add(absolute_url)
                        image_urls.append(absolute_url)
                        new_images_found += 1
                        self.logger.info(f"Found NEW background image: {absolute_url}")
        
        # Yield images if any NEW ones found on this page
        if image_urls:
            yield {
                'image_urls': image_urls
            }
            self.logger.info(f"Found {new_images_found} NEW images on {response.url}")
        else:
            self.logger.info(f"No new images found on {response.url}")
        
        # Stop if we've found enough images
        if len(self.found_image_urls) >= 200:  # Increased limit
            self.logger.info(f"Found {len(self.found_image_urls)} images, stopping crawler")
            return
        
        # Handle pagination - look for "next" or "load more" buttons with more specific selectors
        pagination_selectors = [
            'a[rel="next"]',  # Standard pagination
            '.pagination .next',
            '.pagination-next',
            '.pagination a:contains("Next")',
            '.pagination a:contains("›")',
            '.pagination a:contains(">")', 
            'a:contains("Next")',
            'a:contains("Load More")',
            'button:contains("Load More")',
            '.load-more',
            '.btn-load-more',
            '.pagination a:not(.disabled):last-child',  # Last pagination link
            '[data-page]',  # Data-page attributes for AJAX pagination
            '.page-item .page-link:contains("Next")',
            '.btn:contains("Show More")',
            '.pagination-next-link'
        ]
        
        pagination_found = False
        for selector in pagination_selectors:
            next_page_links = response.css(selector)
            for link_element in next_page_links:
                next_page = link_element.css('::attr(href)').get()
                if next_page and next_page not in ['#', 'javascript:void(0)', 'javascript:;']:
                    self.logger.info(f"Found pagination link with selector '{selector}': {next_page}")
                    yield response.follow(next_page, callback=self.parse)
                    pagination_found = True
                    break
            if pagination_found:
                break
        
        # Also look for AJAX pagination patterns in URLs
        current_url = response.url
        if '/events/listing/upcoming' in current_url:
            # Try different page parameters that might work
            page_params = ['page', 'p', 'offset', 'start']
            for param in page_params:
                if f'{param}=' in current_url:
                    # Extract current page number and try next page
                    import re
                    match = re.search(f'{param}=(\\d+)', current_url)
                    if match:
                        current_page = int(match.group(1))
                        next_page_url = re.sub(f'{param}=\\d+', f'{param}={current_page + 1}', current_url)
                        if next_page_url != current_url:
                            self.logger.info(f"Trying next page via URL parameter: {next_page_url}")
                            yield response.follow(next_page_url, callback=self.parse)
                            break
                else:
                    # Try adding page parameter
                    separator = '&' if '?' in current_url else '?'
                    next_page_url = f"{current_url}{separator}{param}=2"
                    self.logger.info(f"Trying pagination with new parameter: {next_page_url}")
                    yield response.follow(next_page_url, callback=self.parse)
                    break
        
        # Follow internal links to continue crawling (limit to prevent loops)
        links_followed = 0
        max_links_per_page = 15  # Increased for more thorough crawling
        
        for link in response.css('a::attr(href)').getall():
            if links_followed >= max_links_per_page:
                break
                
            if link:
                # Convert to absolute URL
                absolute_link = urljoin(response.url, link)
                
                # ONLY follow events-related URLs, skip flights/hotels/other sections
                if (self.is_internal_link(absolute_link, response.url) and 
                    not self.is_valid_image_url(absolute_link) and
                    self.is_events_related_url(absolute_link)):
                    
                    links_followed += 1
                    yield response.follow(link, callback=self.parse)
    
    def is_events_related_url(self, url):
        """Check if URL is related to events (not flights/hotels/other sections)."""
        if not url:
            return False
            
        url_lower = url.lower()
        
        # Allow only events-related URLs
        events_patterns = [
            '/events/',
            '/event/',
            '/events/listing',
            '/events/upcoming',
            '/events/category'
        ]
        
        # Block non-events sections
        blocked_patterns = [
            '/flights/',
            '/flight/',
            '/hotels/',
            '/hotel/',
            '/booking/',
            '/travel/',
            '/packages/',
            '/tours/',
            '/accommodation',
            '/transport',
            '/visa',
            '/payment',
            '/checkout',
            '/cart',
            '/user/',
            '/profile/',
            '/account/',
            '/login',
            '/register',
            '/admin/',
            '/api/',
            '/cdn-cgi/',
            '/privacy',
            '/terms',
            '/contact',
            '/about',
            '/support',
            '/help'
        ]
        
        # First check if it's blocked
        for pattern in blocked_patterns:
            if pattern in url_lower:
                return False
        
        # Then check if it's events-related OR the main listing page
        for pattern in events_patterns:
            if pattern in url_lower:
                return True
                
        # Also allow main listing pages that might contain events
        if '/listing/' in url_lower and '/upcoming' in url_lower:
            return True
            
        return False
    
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