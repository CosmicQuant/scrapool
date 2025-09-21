"""
Enhanced pipeline that downloads images and processes them with waifu2x-ncnn-vulkan.
Simplified version that uses waifu2x's built-in batch processing.
"""

import json
import os
import time
import logging
import subprocess
import re
from pathlib import Path
from random import uniform
from collections import deque
from datetime import datetime, timedelta
from urllib.parse import urlparse
import scrapy
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem

class RateLimiter:
    """Professional-grade rate limiter using token bucket algorithm."""
    
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    def wait_if_needed(self):
        now = datetime.now()
        # Clean old requests
        while self.requests and (now - self.requests[0]) > timedelta(seconds=self.time_window):
            self.requests.popleft()
        # Apply rate limiting
        if len(self.requests) >= self.max_requests:
            wait_time = (self.requests[0] + timedelta(seconds=self.time_window) - now).total_seconds()
            if wait_time > 0:
                time.sleep(wait_time)
        self.requests.append(now)

class EnhancedImagePipeline(ImagesPipeline):
    def save_image_status(self):
        """Save status of all processed images with normalized keys."""
        status_file = self.base_dir / 'image_status.json'
        normalized_status = {self.normalize_url(k): v for k, v in self.image_status.items()}
        with open(status_file, 'w') as f:
            json.dump({
                'images': normalized_status,
                'last_updated': datetime.now().isoformat(),
                'stats': {
                    'total': len(normalized_status),
                    'enhanced': sum(1 for status in normalized_status.values() if status.get('enhanced')),
                    'failed': sum(1 for status in normalized_status.values() if status.get('failed'))
                }
            }, f, indent=2)
    """Enhanced image pipeline that uses waifu2x's built-in batch processing."""
    
    def __init__(self, store_uri, waifu2x_path=None, *args, **kwargs):
        super().__init__(store_uri, *args, **kwargs)
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
        self.all_urls = set()
        self.image_status = {}  # Dict to track status of all images
        self.previously_downloaded = set()  # Set of URLs for quick lookup
        self.new_images = []  # List to track paths of newly downloaded images
        
        # Set up base directory for all pipeline files
        self.base_dir = Path(__file__).parent  # This will be image_scraper/ directory
        
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
        # File handler - use absolute path in image_scraper directory
        log_file = self.base_dir / 'image_pipeline.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Path to waifu2x-ncnn-vulkan executable - configurable
        self.waifu2x_path = waifu2x_path or "waifu2x-ncnn-vulkan.exe"
        self.logger.info(f"Using waifu2x path: {self.waifu2x_path}")
        
        # Track processing statistics
        self.stats = {
            'downloaded': 0,
            'enhanced': 0,
            'failed': 0,
            'start_time': datetime.now()
        }
        
        self.load_image_status()

    @classmethod
    def from_settings(cls, settings):
        store_uri = settings['IMAGES_STORE']
        waifu2x_path = settings.get('WAIFU2X_PATH', 'waifu2x-ncnn-vulkan')
        return cls(store_uri, waifu2x_path)

    def load_image_status(self):
        """Load status of all processed images."""
        status_file = self.base_dir / 'image_status.json'
        try:
            with open(status_file, 'r') as f:
                data = json.load(f)
                self.image_status = data.get('images', {})
                enhanced = sum(1 for status in self.image_status.values() if status.get('enhanced'))
                total = len(self.image_status)
                self.logger.info(f"Loaded status for {total} images ({enhanced} enhanced)")
                self.previously_downloaded = set(self.image_status.keys())
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.info("No previous image status found")
            self.image_status = {}
            self.previously_downloaded = set()

    def save_image_status(self):
        """Save status of all processed images with normalized keys (no double normalization)."""
        status_file = self.base_dir / 'image_status.json'
        # image_status already uses normalized keys, so save as-is
        with open(status_file, 'w') as f:
            json.dump({
                'images': self.image_status,
                'last_updated': datetime.now().isoformat(),
                'stats': {
                    'total': len(self.image_status),
                    'enhanced': sum(1 for status in self.image_status.values() if status.get('enhanced')),
                    'failed': sum(1 for status in self.image_status.values() if status.get('failed'))
                }
            }, f, indent=2)

    def copy_to_waifu2x(self, image_path):
        """Copy a newly downloaded image to waifu2x input folder."""
        if not os.path.exists(image_path):
            self.logger.error(f"Image not found: {image_path}")
            return False

        if not os.path.exists(self.waifu2x_path):
            self.logger.error(f"waifu2x executable not found at: {self.waifu2x_path}")
            return False

        try:
            # Get waifu2x input directory
            input_dir = os.path.join(os.path.dirname(self.waifu2x_path), "input")
            
            # Copy file to input directory keeping original name
            import shutil
            shutil.copy2(image_path, os.path.join(input_dir, os.path.basename(image_path)))
            self.logger.info(f"Copied new image to waifu2x input: {os.path.basename(image_path)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy image to input directory: {str(e)}")
            return False

    def run_waifu2x(self):
        """Run waifu2x on all images in the input folder."""
        waifu2x_dir = os.path.dirname(self.waifu2x_path)
        input_dir = os.path.join(waifu2x_dir, "input")
        output_dir = os.path.join(waifu2x_dir, "output")
        models_path = str(Path(self.waifu2x_path).parent / "models-cunet")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        if not os.listdir(input_dir):
            self.logger.info("No new images to enhance")
            return True

        # Prepare waifu2x command
        cmd = [
            self.waifu2x_path,
            "-i", input_dir,
            "-o", output_dir,
                "-n", "2",  # Increased noise reduction level
            "-s", "2",  # Scale factor
            "-t", "32",  # Tile size for memory efficiency
            "-m", models_path,
            "-g", "auto",  # Auto GPU selection
            "-j", "1:2:2",  # Thread configuration
            "-f", "jpg",  # Output as JPG
            "-v"  # Verbose output
        ]

        try:
            # Run waifu2x on all images at once
            self.logger.info(f"Enhancing all images in {input_dir}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(Path(self.waifu2x_path).parent)
            )
            stdout, stderr = process.communicate()

            if stdout:
                self.logger.debug(f"waifu2x stdout: {stdout.decode()}")
            if stderr:
                self.logger.debug(f"waifu2x stderr: {stderr.decode()}")

            return process.returncode == 0

        except Exception as e:
            self.logger.error(f"Error running waifu2x: {str(e)}")
            return False

    def clean_waifu2x_folders(self):
        """Clean up both waifu2x input and output folders"""
        waifu2x_dir = os.path.dirname(self.waifu2x_path)
        input_dir = os.path.join(waifu2x_dir, "input")
        output_dir = os.path.join(waifu2x_dir, "output")
        
        # Clean and ensure input folder exists
        if os.path.exists(input_dir):
            self.logger.info("Cleaning waifu2x input folder")
            for f in os.listdir(input_dir):
                try:
                    os.remove(os.path.join(input_dir, f))
                except Exception as e:
                    self.logger.error(f"Failed to remove input file {f}: {str(e)}")
        else:
            os.makedirs(input_dir)
            
        # Clean and ensure output folder exists
        if os.path.exists(output_dir):
            self.logger.info("Cleaning waifu2x output folder")
            for f in os.listdir(output_dir):
                try:
                    os.remove(os.path.join(output_dir, f))
                except Exception as e:
                    self.logger.error(f"Failed to remove output file {f}: {str(e)}")
        else:
            os.makedirs(output_dir)

    def get_media_requests(self, item, info):
        """Request only images not already tracked in image_status.json."""
        urls = item.get('image_urls', [])
        self.all_urls.update(urls)
        for url in urls:
            if url not in self.image_status:
                self.logger.info(f"Queuing image for download: {url}")
                request = scrapy.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Referer': url
                })
                self.rate_limiter.wait_if_needed()
                time.sleep(uniform(0.5, 1.5))
                yield request
            else:
                self.logger.info(f"Skipping already tracked image: {url}")

    def file_path(self, request, response=None, info=None, *, item=None):
        """Generate a meaningful filename with domain prefix and original name."""
        url = request.url
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Extract original filename from URL
        original_filename = Path(parsed_url.path).name
        
        # If no filename in URL, create one from the last path segment
        if not original_filename or '.' not in original_filename:
            path_parts = [p for p in parsed_url.path.split('/') if p]
            if path_parts:
                original_filename = f"{path_parts[-1]}.jpg"
            else:
                original_filename = "image.jpg"
        
        # Create domain prefix
        domain_prefix = ""
        if 'whats-on-mombasa.com' in domain:
            domain_prefix = "mombasa_"
        elif 'ticketsasa.com' in domain:
            domain_prefix = "ticketsasa_"
        else:
            # For other domains, use first part of domain
            domain_prefix = f"{domain.split('.')[0]}_"
        
        # Sanitize filename - remove invalid characters
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', original_filename)
        safe_filename = re.sub(r'[^\w\-_\.]', '_', safe_filename)
        
        # Combine prefix with sanitized filename
        final_filename = f"{domain_prefix}{safe_filename}"
        
        # Ensure it's not too long (Windows has 260 char path limit)
        if len(final_filename) > 100:
            name_part, ext = os.path.splitext(final_filename)
            final_filename = f"{name_part[:95]}{ext}"
        
        return f"full/{final_filename}"

    def item_completed(self, results, item, info):
        """Process downloaded images."""
        # Check if this item contains TicketSasa images (skip enhancement)
        skip_enhancement_domains = ['ticketsasa.com', 'admin.ticketsasa.com']
        skip_enhancement = False
        
        for ok, x in results:
            if ok:
                url = x['url']
                if any(domain in url for domain in skip_enhancement_domains):
                    skip_enhancement = True
                    break
        
        for ok, x in results:
            if ok:
                url = x['url']
                path = x['path']
                full_path = os.path.join(self.store.basedir, path)
                # Only queue if URL is not already in image_status
                if url not in self.image_status:
                    self.logger.info(f"DEBUG: Queuing new image for enhancement: URL={url} | Filename={full_path}")
                    if not skip_enhancement:
                        self.new_images.append(full_path)
                        self.logger.info(f"Successfully downloaded new image: {url}")
                    else:
                        self.logger.info(f"Successfully downloaded TicketSasa image (skipping enhancement): {url}")
                    self.stats['downloaded'] += 1
                    self.image_status[url] = {
                        'downloaded': True,
                        'enhanced': skip_enhancement,  # Mark as enhanced if skipping
                        'file_path': path,  # Store relative path like existing entries
                        'download_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                        'filename': os.path.basename(path),
                        'file_size': os.path.getsize(full_path) if os.path.exists(full_path) else 0,
                        'domain': url.split('/')[2] if '://' in url else 'unknown'
                    }
                else:
                    self.logger.debug(f"Skipping previously tracked image: {url}")

        return item

    def close_spider(self, spider):
        """Process all new images and save statistics when spider closes."""
        if self.new_images:
            self.logger.info(f"Found {len(self.new_images)} new images to enhance")
            
            # Clean both input and output folders
            self.clean_waifu2x_folders()
            
            # Copy all new images to input folder
            for image_path in self.new_images:
                self.copy_to_waifu2x(image_path)
            
            # Run enhancement on all new images at once
            if self.run_waifu2x():
                self.logger.info("Successfully enhanced all new images")
                self.stats['enhanced'] = len(self.new_images)
                
                # Update status for enhanced images
                for url, status in self.image_status.items():
                    if 'file_path' in status:
                        full_path = os.path.join(self.store.basedir, status['file_path'])
                        if full_path in self.new_images:
                            status['enhanced'] = True
            else:
                self.logger.error("Failed to enhance some images")
                self.stats['failed'] = len(self.new_images)
                
                # Mark failed images
                for url, status in self.image_status.items():
                    if 'file_path' in status:
                        full_path = os.path.join(self.store.basedir, status['file_path'])
                        if full_path in self.new_images:
                            status['enhanced'] = False
        else:
            self.logger.info("No new images to enhance")
            
        self.save_image_status()
        
        # Calculate runtime statistics
        end_time = datetime.now()
        runtime = end_time - self.stats['start_time']
        avg_time = runtime.total_seconds() / self.stats['downloaded'] if self.stats['downloaded'] > 0 else 0
        success_rate = (self.stats['enhanced'] / self.stats['downloaded'] * 100) if self.stats['downloaded'] > 0 else 0
        
        # Log summary
        self.logger.info("\nSpider finished. Summary:")
        self.logger.info(f"Runtime: {runtime}")
        self.logger.info(f"Total URLs found: {len(self.all_urls)}")
        self.logger.info(f"Downloads: {self.stats['downloaded']}")
        self.logger.info(f"Enhanced: {self.stats['enhanced']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Success rate: {success_rate:.2f}%")
        self.logger.info(f"Average time per image: {avg_time:.2f} seconds")
        
        # Save statistics
        stats_file = self.base_dir / 'pipeline_stats.json'
        with open(stats_file, 'w') as f:
            json.dump({
                'runtime': str(runtime),
                'total_urls': len(self.all_urls),
                'downloaded': self.stats['downloaded'],
                'enhanced': self.stats['enhanced'],
                'failed': self.stats['failed'],
                'success_rate': success_rate,
                'avg_time_per_image': avg_time,
                'timestamp': end_time.isoformat()
            }, f, indent=2)