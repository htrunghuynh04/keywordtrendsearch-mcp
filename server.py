from mcp.server.fastmcp import FastMCP
from SeoKeywordResearch import SeoKeywordResearch
import uvicorn
import os

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


class BypassHostCheck:
    """
    MCP's transport_security.py rejects external Host headers (DNS rebinding protection).
    On Azure, requests arrive with the azurewebsites.net hostname which is blocked.
    This middleware rewrites the Host header to 'localhost' before MCP sees it.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = [(k, v) for k, v in scope.get("headers", []) if k.lower() != b"host"]
            headers.append((b"host", b"127.0.0.1"))
            scope = {**scope, "headers": headers}
        await self.app(scope, receive, send)


app = BypassHostCheck(mcp.sse_app())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
