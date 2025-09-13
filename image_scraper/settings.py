"""
Base settings for the image scraper project.
Individual spiders can override these settings using custom_settings.
"""

BOT_NAME = "image_scraper"

SPIDER_MODULES = ["image_scraper.spiders"]
NEWSPIDER_MODULE = "image_scraper.spiders"

# Be respectful to websites by default
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Default pipeline setup (can be overridden by spiders)
ITEM_PIPELINES = {
    "image_scraper.pipelines.EnhancedImagePipeline": 1,
}

# Image storage configuration
IMAGES_STORE = "image_scraper/downloaded_images"

# Optimize for best quality images
IMAGES_MIN_HEIGHT = 0
IMAGES_MIN_WIDTH = 0
IMAGES_EXPIRES = 0
MEDIA_ALLOW_REDIRECTS = True

# User agent to identify our bot
USER_AGENT = "ImageScraper (+https://www.example.com)"

# Use UTF-8 encoding for exports
FEED_EXPORT_ENCODING = "utf-8"

# waifu2x path - UPDATE THIS TO YOUR INSTALLATION
WAIFU2X_PATH = r"waifu2x-ncnn-vulkan.exe"  # Change this to your waifu2x path