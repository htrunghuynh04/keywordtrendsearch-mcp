from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecurityMiddleware
from SeoKeywordResearch import SeoKeywordResearch
import uvicorn
import os

# mcp 1.26.0 uses TransportSecuritySettings with allowed_hosts=[] by default,
# which blocks ALL Host headers. Patch validate_request to allow cloud deployments
# where the Host header is the public Azure hostname.
async def _noop_validate(self, request, is_post=False):
    return None

TransportSecurityMiddleware.validate_request = _noop_validate

mcp = FastMCP("SEO Keyword Research")

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")


def _client(query: str, lang: str = "en", country: str = "us", domain: str = "google.com") -> SeoKeywordResearch:
    return SeoKeywordResearch(query=query, api_key=SERPAPI_KEY, lang=lang, country=country, domain=domain)


@mcp.tool()
def get_autocomplete(query: str, lang: str = "en", country: str = "us") -> list:
    """Get Google Autocomplete keyword suggestions for a search query."""
    return _client(query, lang, country).get_auto_complete()


@mcp.tool()
def get_related_searches(query: str, lang: str = "en", country: str = "us", domain: str = "google.com") -> list:
    """Get Google Related Searches for a query."""
    return _client(query, lang, country, domain).get_related_searches()


@mcp.tool()
def get_related_questions(query: str, depth_limit: int = 0, lang: str = "en", country: str = "us", domain: str = "google.com") -> list:
    """Get People Also Ask questions for a query. depth_limit 0-4 controls how deep to fetch nested questions."""
    return _client(query, lang, country, domain).get_related_questions(depth_limit)


@mcp.tool()
def select_target_keywords(query: str, depth_limit: int = 1, lang: str = "en", country: str = "us", domain: str = "google.com") -> dict:
    """
    Automatically select the best SEO keywords for a query.
    Returns 1 primary keyword and 3-5 secondary keywords scored by
    cross-source frequency, autocomplete position, relevance, and long-tail bonus.
    """
    client = _client(query, lang, country, domain)
    result = client.select_target_keywords(depth_limit)
    result.pop("raw_data", None)
    return result


app = mcp.sse_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
