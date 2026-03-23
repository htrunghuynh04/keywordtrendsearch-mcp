from SeoKeywordResearch import SeoKeywordResearch

keyword_research = SeoKeywordResearch(
    query='starbucks coffee',
    api_key='729d5a560a90f657e0bdeb6ce7da083cb525db5867b879260c0ce529f1b4794d',
    lang='en',
    country='us',
    domain='google.com'
)

# Select 1 primary keyword + 3-5 secondary keywords automatically
result = keyword_research.select_target_keywords(depth_limit=1)

print(f"Seed Query: {result['seed_query']}\n")

primary = result['primary_keyword']
if primary is None:
    print("No keywords found. Check your API key and query.")
else:
    print("=== PRIMARY KEYWORD ===")
    print(f"  {primary['keyword']} (score: {primary['score']}, type: {primary['type']}, sources: {primary['sources']})")

    print("\n=== SECONDARY KEYWORDS ===")
    for kw in result['secondary_keywords']:
        print(f"  {kw['keyword']} (score: {kw['score']}, type: {kw['type']}, sources: {kw['sources']})")

    print(f"\n=== ALL CANDIDATES ({len(result['all_candidates'])}) ===")
    for kw in result['all_candidates']:
        print(f"  {kw['keyword']:40s} score={kw['score']:5.1f}  type={kw['type']:10s}  sources={kw['sources']}")

    # Save full results to JSON
    keyword_research.save_to_json(result['raw_data'])
