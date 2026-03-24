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


@mcp.tool()
def get_keyword_trends(
    query: str,
    country: str = "US",
    period: str = "today 12-m",
    lang: str = "en"
) -> dict:
    """
    Get Google Trends data for a keyword showing relative popularity over time.

    Returns:
    - trend_direction: 'rising', 'declining', or 'stable'
    - average_interest: average interest score (0-100) over the period
    - peak_interest: highest interest score in the period
    - timeline: list of {date, value} data points
    - rising_queries: related queries that are trending up
    - top_queries: top related queries by volume

    period options: 'now 1-H', 'now 4-H', 'now 1-d', 'now 7-d',
                    'today 1-m', 'today 3-m', 'today 12-m', 'today 5-y'
    country: ISO country code e.g. 'US', 'VN', 'GB'
    """
    from serpapi import GoogleSearch

    # Get interest over time
    timeline_params = {
        "engine": "google_trends",
        "q": query,
        "data_type": "TIMESERIES",
        "date": period,
        "geo": country,
        "hl": lang,
        "api_key": SERPAPI_KEY,
    }
    timeline_result = GoogleSearch(timeline_params).get_dict()
    timeline_data = [
        {"date": p.get("date"), "value": p.get("value", [0])[0]}
        for p in timeline_result.get("interest_over_time", {}).get("timeline_data", [])
    ]

    # Calculate trend direction
    trend_direction = "stable"
    average_interest = 0
    peak_interest = 0
    if timeline_data:
        values = [p["value"] for p in timeline_data if p["value"] is not None]
        if values:
            average_interest = round(sum(values) / len(values), 1)
            peak_interest = max(values)
            if len(values) >= 4:
                first_half = sum(values[:len(values)//2]) / (len(values)//2)
                second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                if second_half > first_half * 1.1:
                    trend_direction = "rising"
                elif second_half < first_half * 0.9:
                    trend_direction = "declining"

    # Get related queries
    related_params = {
        "engine": "google_trends",
        "q": query,
        "data_type": "RELATED_QUERIES",
        "date": period,
        "geo": country,
        "hl": lang,
        "api_key": SERPAPI_KEY,
    }
    related_result = GoogleSearch(related_params).get_dict()
    related_queries = related_result.get("related_queries", {})
    rising = [
        {"query": q.get("query"), "value": q.get("value")}
        for q in related_queries.get("rising", [])[:10]
    ]
    top = [
        {"query": q.get("query"), "value": q.get("value")}
        for q in related_queries.get("top", [])[:10]
    ]

    return {
        "keyword": query,
        "country": country,
        "period": period,
        "trend_direction": trend_direction,
        "average_interest": average_interest,
        "peak_interest": peak_interest,
        "timeline": timeline_data,
        "rising_queries": rising,
        "top_queries": top,
    }


from starlette.applications import Starlette
from starlette.routing import Mount

# Cursor uses SSE (/sse), AgentQuinta uses streamable-http (/mcp)
app = Starlette(routes=[
    Mount("/mcp", app=mcp.streamable_http_app()),
    Mount("/", app=mcp.sse_app()),
])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
