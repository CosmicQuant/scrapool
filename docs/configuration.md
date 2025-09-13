# Configuration Guide

## Initial Setup

### 1. Configure Target Website

Edit `image_scraper/spiders/image_spider.py`:

```python
start_urls = ['https://your-target-website.com/']
allowed_domains = ['your-target-website.com', 'www.your-target-website.com']
```

### 2. Configure waifu2x Path

Edit `image_scraper/settings.py`:

```python
WAIFU2X_PATH = r"C:\path\to\your\waifu2x-ncnn-vulkan.exe"
```

Or set it in the spider's custom_settings:

```python
custom_settings = {
    'WAIFU2X_PATH': r'C:\your\path\waifu2x-ncnn-vulkan.exe'
}
```

## Advanced Configuration

### Crawling Behavior

```python
# In spider's custom_settings
'DEPTH_LIMIT': 1,                  # How deep to crawl
'CLOSESPIDER_PAGECOUNT': 20,       # Stop after N pages
'CLOSESPIDER_ITEMCOUNT': 100,      # Stop after N images
'DOWNLOAD_DELAY': 2,               # Delay between requests
'CONCURRENT_REQUESTS_PER_DOMAIN': 1, # Parallel requests
```

### Image Filtering

```python
# In spider's custom_settings
'IMAGES_MIN_HEIGHT': 100,          # Minimum image height
'IMAGES_MIN_WIDTH': 100,           # Minimum image width
```

### Rate Limiting

```python
# In pipelines.py RateLimiter class
RateLimiter(max_requests=10, time_window=60)  # 10 requests per minute
```

## Examples

### Example 1: E-commerce Site
```python
start_urls = ['https://shop.example.com/']
allowed_domains = ['shop.example.com']
custom_settings = {
    'IMAGES_MIN_HEIGHT': 200,  # Higher quality for product images
    'DOWNLOAD_DELAY': 3,       # Slower for respectful crawling
}
```

### Example 2: Gallery/Portfolio Site
```python
start_urls = ['https://gallery.example.com/']
allowed_domains = ['gallery.example.com']
custom_settings = {
    'DEPTH_LIMIT': 2,          # Deeper crawling for galleries
    'IMAGES_MIN_HEIGHT': 300,  # High quality images only
}
```

### Example 3: News/Blog Site
```python
start_urls = ['https://news.example.com/']
allowed_domains = ['news.example.com']
custom_settings = {
    'CLOSESPIDER_PAGECOUNT': 50,  # More pages for content sites
    'DOWNLOAD_DELAY': 1,          # Faster for public content
}
```