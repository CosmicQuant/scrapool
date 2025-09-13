# ScraPool - AI-Enhanced Image Scraper

A powerful web scraper that automatically discovers, downloads, and enhances images using AI upscaling technology.

## Features

- 🕷️ **Smart Web Crawling**: Automatically discovers images across websites
- 🚀 **AI Enhancement**: Uses waifu2x-ncnn-vulkan for 2x image upscaling
- 🔄 **Duplicate Prevention**: Intelligent tracking prevents re-downloading
- ⚡ **Batch Processing**: Efficient bulk image enhancement
- 📊 **Progress Tracking**: Detailed logging and statistics
- 🛡️ **Rate Limiting**: Respectful crawling with configurable delays

## Technology Stack

- **Scrapy**: Web crawling framework
- **waifu2x-ncnn-vulkan**: AI image enhancement
- **Python 3.8+**: Core language
- **JSON**: Data persistence

## Quick Start

### Prerequisites

1. Python 3.8 or higher
2. [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) installed

### Installation

```bash
# Clone the repository
git clone https://github.com/CosmicQuant/scrapool.git
cd scrapool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Update the waifu2x path in `image_scraper/settings.py`:
```python
WAIFU2X_PATH = r"path\to\your\waifu2x-ncnn-vulkan.exe"
```

2. Configure target website in `image_scraper/spiders/image_spider.py`:
```python
start_urls = ['https://your-target-website.com']
```

### Usage

```bash
# Navigate to project directory
cd image_scraper

# Run the spider
scrapy crawl image_spider

# View results
ls downloaded_images/full/  # Original images
ls path/to/waifu2x/output/  # Enhanced images
```

## Configuration Options

### Spider Settings (`image_scraper/settings.py`)

```python
# Crawling limits
DEPTH_LIMIT = 1                    # How deep to crawl
CLOSESPIDER_PAGECOUNT = 20         # Stop after N pages
CLOSESPIDER_ITEMCOUNT = 100        # Stop after N images

# Image filtering
IMAGES_MIN_HEIGHT = 100            # Minimum image height
IMAGES_MIN_WIDTH = 100             # Minimum image width

# Rate limiting
DOWNLOAD_DELAY = 2                 # Delay between requests
CONCURRENT_REQUESTS = 1            # Parallel requests
```

### Pipeline Settings

```python
# Enhancement settings
WAIFU2X_SCALE = 2                  # Upscaling factor
WAIFU2X_NOISE = 1                  # Noise reduction level
WAIFU2X_TILE_SIZE = 32            # Memory efficiency
```

## Project Structure

```
scrapool/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── scrapy.cfg               # Scrapy project config
├── image_scraper/           # Main package
│   ├── __init__.py
│   ├── items.py             # Data structures
│   ├── middlewares.py       # Request/response processing
│   ├── pipelines.py         # Image processing pipeline
│   ├── settings.py          # Configuration
│   └── spiders/
│       ├── __init__.py
│       └── image_spider.py  # Main spider
├── downloaded_images/       # Output directory (gitignored)
├── logs/                    # Log files (gitignored)
└── docs/                    # Documentation
```

## Output Files

- `downloaded_images/full/`: Original downloaded images
- `image_status.json`: Tracking database of processed images
- `pipeline_stats.json`: Performance statistics
- `image_pipeline.log`: Detailed operation logs

## Advanced Features

### Duplicate Detection

The system uses multi-level duplicate detection:
1. **Session-level**: Prevents finding same URLs multiple times per run
2. **Persistent-level**: Avoids re-downloading previously processed images

### AI Enhancement

- Uses waifu2x-ncnn-vulkan for high-quality upscaling
- Configurable enhancement parameters
- Batch processing for efficiency
- Automatic fallback handling

### Smart Crawling

- Respects robots.txt
- Configurable depth and page limits
- Intelligent image URL detection
- Size and format filtering

## Examples

### Basic Usage

```bash
# Scrape images from a single website
cd image_scraper
scrapy crawl image_spider
```

### Custom Configuration

```python
# In image_spider.py
start_urls = ['https://ticketsasa.com/']  # Target website
allowed_domains = ['ticketsasa.com']      # Stay within domain
```

### Advanced Settings

```python
# In settings.py
DOWNLOAD_DELAY = 3              # Slower crawling
IMAGES_MIN_HEIGHT = 200         # Higher quality images only
DEPTH_LIMIT = 2                 # Deeper crawling
```

## Troubleshooting

### Common Issues

1. **waifu2x not found**: Update `WAIFU2X_PATH` in settings
2. **Memory errors**: Reduce `WAIFU2X_TILE_SIZE` or limit concurrent requests
3. **Rate limiting**: Increase `DOWNLOAD_DELAY` in settings
4. **No images found**: Check website structure and image URL patterns

### Performance Tips

- Use `IMAGES_MIN_HEIGHT` and `IMAGES_MIN_WIDTH` to filter small images
- Adjust `DOWNLOAD_DELAY` based on target website's response time
- Monitor `image_pipeline.log` for debugging information

### Logging

Check `image_pipeline.log` for detailed operation logs:
```bash
tail -f image_pipeline.log  # Follow logs in real-time
```

## Recent Targets Tested

- ✅ **whats-on-mombasa.com**: 108+ images successfully processed
- ✅ **ticketsasa.com**: 18 new images with event promotional content
- 🎯 **Performance**: 100% success rate with AI enhancement

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Scrapy](https://scrapy.org/) for the excellent web crawling framework
- [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) for AI image enhancement
- Community contributors and testers

## Support

If you encounter any issues or have questions:
1. Check the [Issues](https://github.com/CosmicQuant/scrapool/issues) page
2. Review the troubleshooting section above
3. Create a new issue with detailed information

---

**Happy Scraping!** 🕷️✨