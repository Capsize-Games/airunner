"""Web search and scraping tools."""

import asyncio
import ipaddress
import socket
import threading
import time
from typing import Annotated, Any, Callable, Coroutine
from urllib.parse import urlparse

from airunner_services.llm.core.tool_registry import ToolCategory, tool
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.downloads.policy import is_duckduckgo_allowed
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.log_hygiene import (
	fingerprint_value,
	summarize_text,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

_last_search_time = 0
_SEARCH_COOLDOWN = 2.0
_cooldown_lock = threading.Lock()


def _respect_search_cooldown(search_label: str) -> None:
	"""Apply rate limiting between successive internet tool requests."""
	global _last_search_time
	with _cooldown_lock:
		time_since_last = time.time() - _last_search_time
		wait_time = _SEARCH_COOLDOWN - time_since_last
		if wait_time > 0:
			logger.info(
				"Rate limiting: waiting %.1fs before %s",
				wait_time,
				search_label,
			)
			time.sleep(wait_time)
		_last_search_time = time.time()


def _run_provider_coro(coro_factory: Callable[[], Coroutine]) -> Any:
	"""Run one provider coroutine with or without a running loop.

	asyncio.run() raises inside a running event loop, so when one is
	already running the coroutine executes on a helper thread with its
	own loop instead.
	"""
	try:
		asyncio.get_running_loop()
		running = True
	except RuntimeError:
		running = False
	if not running:
		return asyncio.run(coro_factory())
	result: dict[str, Any] = {}

	def _runner() -> None:
		try:
			result["value"] = asyncio.run(coro_factory())
		except Exception as exc:
			result["error"] = exc

	worker = threading.Thread(target=_runner, daemon=True)
	worker.start()
	worker.join()
	if "error" in result:
		raise result["error"]
	return result.get("value")


def _duckduckgo_web_results(query: str, num_results: int = 10) -> list[dict]:
	"""Return DuckDuckGo web results for one query."""
	from airunner_services.tools.search_providers.duckduckgo_provider import (
		DuckDuckGoProvider,
	)

	provider = DuckDuckGoProvider()
	return _run_provider_coro(
		lambda: provider.search(query, num_results=num_results)
	)


def _duckduckgo_news_results(
	query: str,
	num_results: int = 10,
) -> list[dict]:
	"""Return DuckDuckGo news results for one query."""
	from airunner_services.tools.search_providers.duckduckgo_provider import (
		DuckDuckGoProvider,
	)

	provider = DuckDuckGoProvider()
	return _run_provider_coro(
		lambda: provider.news_search(query, num_results=num_results)
	)


def validate_scrape_url(url: str) -> str:
	"""Validate one scrape URL against the SSRF gate.

	Only http/https URLs whose hosts resolve exclusively to public
	unicast addresses pass. Loopback, link-local, multicast, reserved
	and cloud metadata addresses are rejected, since this tool fetches
	caller-supplied URLs from an agent context.

	Returns the normalized URL, raising ValueError otherwise.
	"""
	parsed = urlparse((url or "").strip())
	if parsed.scheme not in ("http", "https"):
		raise ValueError(f"Refusing to scrape non-http(s) URL: {url!r}")
	host = parsed.hostname or ""
	if not host:
		raise ValueError(f"Refusing to scrape URL without a host: {url!r}")
	lowered = host.lower()
	if lowered in ("localhost", "metadata.google.internal") or lowered.endswith(
		(".localhost", ".internal", ".local", ".lan", ".home", ".corp")
	):
		raise ValueError(f"Refusing to scrape non-public host: {host!r}")
	try:
		addresses = socket.getaddrinfo(host, None)
	except socket.gaierror as exc:
		raise ValueError(f"Refusing to scrape unresolvable host: {host!r}") from exc
	for _family, _kind, _proto, _canon, sockaddr in addresses:
		try:
			address = ipaddress.ip_address(sockaddr[0])
		except ValueError:
			raise ValueError(
				f"Refusing to scrape unparsable address for host: {host!r}"
			)
		if (
			address.is_loopback
			or address.is_link_local
			or address.is_multicast
			or address.is_reserved
			or address.is_private
			or address.is_unspecified
			or address.is_global is False
		):
			raise ValueError(
				f"Refusing to scrape non-public address {address} "
				f"for host: {host!r}"
			)
	return parsed.geturl()


@tool(
	name="search_web",
	category=ToolCategory.SEARCH,
	description=(
		"Search the internet for information using DuckDuckGo. "
		"Returns top search results with titles, URLs, and snippets. "
		"Use this to find current information, websites, or answers to questions."
	),
	return_direct=False,
	requires_api=False,
	defer_loading=False,
	keywords=["internet", "google", "duckduckgo", "online", "web", "find"],
	input_examples=[
		{"query": "latest news about artificial intelligence"},
		{"query": "how to install Python on Ubuntu"},
		{"query": "weather forecast for New York"},
	],
)
def search_web(
	query: Annotated[str, "Search query to look up on the internet"],
) -> str:
	"""Search the internet for information using DuckDuckGo."""

	if not is_duckduckgo_allowed():
		logger.info("Web search disabled by privacy settings")
		return {
			"results": [],
			"summary": (
				"Web search is disabled in privacy settings. "
				"You can enable it in Preferences → Privacy & Security → "
				"External Services."
			),
		}

	try:
		_respect_search_cooldown("search")

		logger.info(
			"Searching web (%s)",
			summarize_text(query, label="query"),
		)

		ddg_results = _duckduckgo_web_results(query, num_results=10)
		logger.info("Got %d DuckDuckGo results", len(ddg_results))

		if not ddg_results:
			logger.warning("Empty DuckDuckGo results list")
			return {"results": []}

		formatted = f"Web search results for '{query}':\n\n"
		for i, result in enumerate(ddg_results[:5], 1):
			title = result.get("title", "N/A")
			link = result.get("link", "#")
			snippet = result.get("snippet", "")[:200]
			formatted += f"{i}. {title}\n"
			formatted += f"   URL: {link}\n"
			if snippet:
				formatted += f"   {snippet}...\n"
			formatted += "\n"

		formatted += "\n" + "=" * 60 + "\n"
		formatted += "📝 NEXT STEPS: You can:\n"
		formatted += (
			"- Use `scrape_website` on a URL to get full article content\n"
		)
		formatted += (
			"- Use `search_web` again with a different query for more info\n"
		)
		formatted += "- Or respond directly if you have enough information\n"
		formatted += "=" * 60 + "\n"

		logger.info("Formatted %d search results", len(ddg_results[:5]))
		return {"results": ddg_results, "summary": formatted}
	except Exception as exc:
		logger.error("Web search error: %s", exc, exc_info=True)
		return f"Error searching web: {str(exc)}"


@tool(
	name="search_news",
	category=ToolCategory.SEARCH,
	description=(
		"Search for recent news articles and current events using "
		"DuckDuckGo News. Returns news articles with titles, URLs, "
		"snippets, sources, and dates. ALWAYS use this for current events, "
		"recent decisions, breaking news, or anything time-sensitive. "
		"Better than search_web for: politics, government actions, recent "
		"appointments, etc."
	),
	return_direct=False,
	requires_api=False,
)
def search_news(
	query: Annotated[
		str,
		"News search query - focus on current events and recent information",
	],
) -> str:
	"""Search for recent news articles using DuckDuckGo News."""

	if not is_duckduckgo_allowed():
		logger.info("News search disabled by privacy settings")
		return {
			"results": [],
			"summary": (
				"Web search is disabled in privacy settings. "
				"You can enable it in Preferences → Privacy & Security → "
				"External Services."
			),
		}

	try:
		_respect_search_cooldown("news search")

		logger.info(
			"Searching news (%s)",
			summarize_text(query, label="query"),
		)

		results = _duckduckgo_news_results(query, num_results=10)

		logger.info("Got %d news results", len(results))

		if not results:
			logger.warning("No news results returned")
			return {"results": []}

		formatted = f"Recent news articles for '{query}':\n\n"
		for i, result in enumerate(results[:7], 1):
			title = result.get("title", "N/A")
			link = result.get("link", "#")
			snippet = result.get("snippet", "")[:250]
			source = result.get("source", "Unknown source")
			date = result.get("date", "")

			formatted += f"{i}. {title}\n"
			formatted += f"   Source: {source}"
			if date:
				formatted += f" | Date: {date}"
			formatted += f"\n   URL: {link}\n"
			if snippet:
				formatted += f"   {snippet}...\n"
			formatted += "\n"

		formatted += "\n" + "=" * 60 + "\n"
		formatted += "📝 NEXT STEPS: You can:\n"
		formatted += (
			"- Use `scrape_website` on a URL to get full article content\n"
		)
		formatted += (
			"- Use `search_news` again with a different query for more info\n"
		)
		formatted += "- Or respond directly if you have enough information\n"
		formatted += "=" * 60 + "\n"

		logger.info("Formatted %d news results", len(results[:7]))
		return {"results": results, "summary": formatted}
	except Exception as exc:
		logger.error("News search error: %s", exc, exc_info=True)
		return f"Error searching news: {str(exc)}"


@tool(
	name="scrape_website",
	category=ToolCategory.SEARCH,
	description=(
		"Scrape and extract clean text content from a website URL. "
		"Automatically removes boilerplate, navigation, ads, and footer "
		"elements. Returns only the main content of the page. Use this to "
		"read articles, blog posts, documentation, or any web page content."
	),
	return_direct=False,
	requires_api=False,
)
def scrape_website(
	url: Annotated[
		str,
		"Website URL to scrape content from (must include http:// or https://)",
	],
) -> dict:
	"""Scrape and extract clean content with metadata from a website."""
	logger.info(
		"Scraping website (%s)",
		fingerprint_value(url, label="url"),
	)

	try:
		safe_url = validate_scrape_url(url)
	except ValueError as exc:
		logger.warning(
			"Refusing to scrape URL (%s): %s",
			fingerprint_value(url, label="url"),
			exc,
		)
		return {"content": None, "error": str(exc)}

	try:
		from airunner_services.tools.web_content_extractor import (
			WebContentExtractor,
		)

		result = WebContentExtractor.fetch_and_extract_with_metadata(
			safe_url,
			use_cache=True,
		)

		if result and result.get("content"):
			logger.info(
				"Extracted %d characters from scraped website",
				len(result["content"]),
			)
			logger.info("Title: %s", result.get("title", "N/A"))
			result["_instructions"] = (
				"📝 IMPORTANT: Use this content to answer the user's original "
				"question. Optionally, use record_knowledge() to save key "
				"facts for future reference."
			)
			return result

		return {
			"content": None,
			"error": (
				f"Could not extract content from {url}. The page may be empty, "
				"require JavaScript, or be blocking scrapers."
			),
		}
	except Exception as exc:
		logger.error(
			"Web scraping error (%s): %s",
			fingerprint_value(url, label="url"),
			exc,
			exc_info=True,
		)
		return {"content": None, "error": f"Error scraping {url}: {str(exc)}"}