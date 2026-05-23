"""
Scrapy settings for LLM-guided web crawling.

These settings configure Scrapy for intelligent, LLM-controlled crawling
that respects websites and provides reliable extraction.
"""

# Crawl responsibly - respect robots.txt
ROBOTSTXT_OBEY = True

# Concurrent requests
# Set to 1 for sequential LLM-controlled crawling
# Can increase for faster crawling without LLM control
CONCURRENT_REQUESTS = 1

# Download delay (seconds) between requests to same domain
# Helps avoid overwhelming servers and getting blocked
DOWNLOAD_DELAY = 1.0

# Disable cookies (not needed for content extraction)
COOKIES_ENABLED = False

# Depth and page limits
DEPTH_LIMIT = 3  # Maximum crawl depth
CLOSESPIDER_PAGECOUNT = 20  # Maximum pages to crawl
CLOSESPIDER_TIMEOUT = 300  # Maximum crawl time in seconds (5 minutes)

# User agent - identify ourselves
USER_AGENT = (
    "AIRunner Research Bot (+https://github.com/Capsize-Games/airunner)"
)

# Retry settings
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Request timeout
DOWNLOAD_TIMEOUT = 15

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(levelname)s: %(message)s"

# Autothrottle settings - automatically adjust delays based on load
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Middleware settings
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 90,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
}

# Spider middlewares
SPIDER_MIDDLEWARES = {
    "scrapy.spidermiddlewares.httperror.HttpErrorMiddleware": 50,
    "scrapy.spidermiddlewares.offsite.OffsiteMiddleware": 500,
    "scrapy.spidermiddlewares.referer.RefererMiddleware": 700,
    "scrapy.spidermiddlewares.urllength.UrlLengthMiddleware": 800,
    "scrapy.spidermiddlewares.depth.DepthMiddleware": 900,
}

# Item pipelines (none needed for now)
ITEM_PIPELINES = {}

# Enable HTTP caching for development
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 86400  # 1 day
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504]

# Extension settings
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,  # Disable telnet
}

# Memory limits
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512
MEMUSAGE_WARNING_MB = 256

# DNS settings
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000

# Redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# Feed export settings (if needed)
FEED_EXPORT_ENCODING = "utf-8"

# Statistics
STATS_DUMP = True
