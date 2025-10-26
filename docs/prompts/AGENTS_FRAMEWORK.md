# AGENT FRAMEWORK
## Restaurant Recommendations App - Complete Agent Architecture

This document defines the complete agent architecture for the restaurant recommendations system. Each agent has a specific role, clear inputs/outputs, and defined dependencies.

---

## Agent Dependency Graph

```
User Query
    ↓
[1. Planner Agent] ─────────────────────────────────────┐
    ↓                                                    ↓
    ├──→ [2. Restaurant Retrieval Agent]                ↓
    │         ↓                                          ↓
    │    [3. Data Enrichment Agent] ← web search    [10. Safety & QA Agent]
    │         ↓                                          ↑
    ├──→ [4. NL Query Interpreter Agent]                │
    │         ↓                                          │
    ├──→ [5. Menu Finder Agent]                         │
    │         ↓                                          │
    │    [6. OCR Worker Agent]                          │
    │         ↓                                          │
    │    [7. Allergen Analyzer Agent] ───────────────→  │
    │                                                    │
    ├──→ [8. Review Enricher Agent] ───────────────→    │
    │                                                    │
    ├──→ [9. Image Scraper Agent] ─────────────────→    │
    │                                                    │
    └──→ [11. Ranker Agent] ← all above data            │
              ↓                                          │
         Final Results ─────────────────────────────────┘
```

---

## 1. Planner Agent

**Role:** Central orchestrator that interprets user intent and coordinates all other agents.

**Model:** Claude Sonnet 4.5 (complex reasoning required)

**Inputs:**
- User query (natural language or structured)
- User location (lat, lon)
- Session context (previous queries, preferences)
- Available tools/agents

**Outputs:**
- Execution plan (which agents to call, in what order)
- Tool invocation sequence
- User-facing interpretation of what will be done

**Dependencies:** None (entry point)

**State Management:**
- Maintains conversation context
- Tracks which enrichment operations have been completed
- Caches recent plans for similar queries

**Key Responsibilities:**
1. Parse user intent (proximity search vs. NL search vs. detail request)
2. Determine which agents to invoke
3. Decide enrichment strategy (lazy vs. eager)
4. Handle error recovery and fallback strategies
5. Format final response for user

---

## 2. Restaurant Retrieval Agent

**Role:** Fetches raw restaurant data from OpenStreetMap via Overpass API.

**Model:** No LLM needed (pure Python logic)

**Implementation:** `helpers/restaurant_retrieval.py` (already exists)

**Inputs:**
- `latitude: float`
- `longitude: float`
- `distance: float` (miles)
- `extract_info: bool = False`

**Outputs:**
```python
{
    'status': 'success' | 'error',
    'count': int,
    'restaurants': [
        {
            'name': str,
            'latitude': float,
            'longitude': float,
            'distance_miles': float,
            'cuisine': str,
            'address': str,
            'city': str,
            'amenity_type': str
        }
    ],
    'query': {
        'latitude': float,
        'longitude': float,
        'radius_miles': float
    }
}
```

**Dependencies:** None

**Limitations:**
- Only returns OSM data (often incomplete)
- Missing: ratings, review_count, phone, hours, images, menus, allergens
- Address data may be incomplete

---

## 3. Data Enrichment Agent ⭐ NEW

**Role:** Enriches basic OSM restaurant data with web-sourced information (ratings, reviews, images, contact info).

**Model:** Claude Haiku 4.5 + Web Search

**Inputs:**
- Restaurant object from Restaurant Retrieval Agent
- Enrichment priority (what fields to prioritize)
- Force refresh flag

**Outputs:**
```python
{
    'id': str,  # generated or from OSM
    'name': str,
    'address': str,  # formatted full address
    'location': {'lat': float, 'lon': float},
    'distance_meters': int,
    'rating': float | None,  # NEW
    'review_count': int | None,  # NEW
    'phone': str | None,  # NEW
    'hours': dict | None,  # NEW
    'price_level': str | None,  # NEW ('$', '$$', '$$$', '$$$$')
    'website': str | None,  # NEW
    'menu_urls': [str],  # NEW
    'image_urls': [str],  # NEW (preview images)
    'sources': [  # NEW (provenance)
        {
            'provider': str,  # 'google', 'yelp', 'tripadvisor', etc.
            'last_updated': str,
            'confidence': float
        }
    ]
}
```

**Dependencies:**
- Restaurant Retrieval Agent (provides base data)
- Web Search (finds business info)

**Key Responsibilities:**
1. Search web for restaurant name + address/city
2. Extract ratings and review counts from search results
3. Find official website and menu URLs
4. Collect representative image URLs
5. Extract contact info and hours
6. Assign confidence scores based on source reliability
7. Cache enriched data (14-day TTL)

**Helper Functions Needed:**
- `search_restaurant_info(name, address, city)` - web search wrapper
- `extract_rating_from_snippet(text)` - parse ratings from text
- `find_menu_urls(search_results)` - extract menu links
- `validate_business_hours(hours_text)` - parse and validate hours
- `generate_cache_key(restaurant)` - for Redis caching

**Enrichment Strategy:**
- **Tier 1 (always):** rating, review_count, phone
- **Tier 2 (on-demand):** menu_urls, hours
- **Tier 3 (lazy):** images (delegated to Image Scraper Agent)

---

## 4. NL Query Interpreter Agent

**Role:** Converts natural language queries into structured filters and boosts.

**Model:** Claude Haiku 4.5

**Inputs:**
- User query (natural language)
- User location context
- Available filter dimensions

**Outputs:**
```python
{
    'filters': {
        'cuisine': [str],  # e.g., ['italian', 'pizza']
        'dietary': [str],  # e.g., ['vegan', 'gluten-free']
        'ambience': [str],  # e.g., ['cozy', 'romantic']
        'features': [str],  # e.g., ['outdoor_seating', 'live_music']
        'price_level': [str],  # e.g., ['$', '$$']
        'meal_type': [str],  # e.g., ['brunch', 'dinner']
        'distance_max_miles': float | None
    },
    'boosts': {
        'highly_rated': float,  # boost multiplier for rating >= 4.5
        'many_reviews': float,  # boost for review_count > threshold
        'open_now': float,
        'has_menu': float
    },
    'interpretation': str,  # human-readable explanation
    'confidence': float  # how confident in the interpretation
}
```

**Dependencies:**
- Planner Agent (receives query)

**Key Responsibilities:**
1. Extract cuisine preferences (explicit and implicit)
2. Identify dietary restrictions
3. Detect ambience/vibe preferences
4. Parse temporal hints ("late night", "brunch", "open now")
5. Determine distance preferences
6. Generate boost weights for ranking

**Helper Functions Needed:**
- `extract_dietary_keywords(query)` - identify diet types
- `parse_temporal_intent(query)` - extract time preferences
- `determine_price_sensitivity(query)` - infer budget
- `calculate_boost_weights(filters)` - convert filters to numeric boosts

---

## 5. Menu Finder Agent

**Role:** Locates text menus and menu images for a restaurant.

**Model:** Claude Haiku 4.5 + Web Search

**Inputs:**
- Restaurant ID
- Restaurant name
- Website URL (if available)
- Search hints (URLs from user or enrichment)

**Outputs:**
```python
{
    'restaurant_id': str,
    'menu_text_urls': [str],  # links to text/HTML menus
    'menu_image_urls': [str],  # links to menu photos
    'menu_pdf_urls': [str],  # links to PDF menus
    'instagram_menu': str | None,  # IG profile if menu in posts
    'confidence': float,
    'last_updated': str,
    'sources': [{'url': str, 'type': str}]
}
```

**Dependencies:**
- Data Enrichment Agent (provides website/hints)
- Web Search

**Key Responsibilities:**
1. Check restaurant's official website for menu
2. Search "{restaurant name} menu" on web
3. Look for common menu hosting platforms (Toast, Wix Restaurants, etc.)
4. Find social media with menu images
5. Respect robots.txt and crawl delays
6. Deduplicate URLs by content hash

**Helper Functions Needed:**
- `scrape_website_for_menu(url)` - extract menu from HTML
- `search_menu_platforms(restaurant_name)` - check aggregators
- `check_robots_txt(domain)` - verify scraping is allowed
- `hash_menu_content(content)` - for deduplication

---

## 6. OCR Worker Agent

**Role:** Extracts text from menu images using OCR.

**Model:** No LLM (OCR engine: Tesseract/EasyOCR)

**Inputs:**
- Menu image URLs
- OCR engine preference
- Language hint

**Outputs:**
```python
{
    'image_url': str,
    'extracted_text': str,
    'confidence': float,  # OCR confidence score
    'language': str,
    'processing_time_ms': int,
    'ocr_engine': str,
    'blocks': [  # structured regions
        {
            'text': str,
            'bbox': [int, int, int, int],
            'confidence': float
        }
    ]
}
```

**Dependencies:**
- Menu Finder Agent (provides image URLs)

**Key Responsibilities:**
1. Download and validate images
2. Preprocess images (deskew, enhance contrast, denoise)
3. Run OCR with specified engine
4. Post-process text (fix common OCR errors)
5. Structure output by regions (headers, items, prices)
6. Handle multi-language menus

**Helper Functions Needed:**
- `preprocess_image(image_bytes)` - enhance for OCR
- `run_ocr_engine(image, engine)` - execute OCR
- `post_process_ocr_text(text)` - clean up errors
- `detect_menu_structure(blocks)` - identify sections

---

## 7. Allergen Analyzer Agent

**Role:** Analyzes menu text/images to detect allergens with probability scores.

**Model:** Claude Haiku 4.5 (or Sonnet 4.5 for complex menus)

**Inputs:**
- Menu text (from text menus or OCR)
- Cuisine type (for cultural priors)
- Restaurant name

**Outputs:**
```python
{
    'restaurant_id': str,
    'updated_at': str,
    'summary': {  # venue-wide allergen probabilities
        'gluten': float,  # 0.0 - 1.0
        'dairy': float,
        'eggs': float,
        'soy': float,
        'peanuts': float,
        'tree_nuts': float,
        'shellfish': float,
        'fish': float,
        'sesame': float
    },
    'by_dish': [
        {
            'name': str,
            'allergens': dict,  # same keys as summary
            'evidence': [
                {
                    'type': 'text' | 'image' | 'inference',
                    'snippet': str,
                    'reasoning': str
                }
            ],
            'confidence': float
        }
    ],
    'cuisine_priors_applied': bool,
    'provenance': {
        'menu_sources': [str],
        'ocr_used': bool,
        'llm_model': str
    },
    'overall_confidence': float,
    'warnings': [str]  # e.g., "No menu available, low confidence"
}
```

**Dependencies:**
- Menu Finder Agent (provides menu text/images)
- OCR Worker Agent (if images)

**Key Responsibilities:**
1. Parse menu items and ingredients
2. Map ingredients to common allergens
3. Apply cuisine-specific priors (e.g., Asian food → high soy probability)
4. Assign dish-level allergen probabilities
5. Aggregate to venue-level summary
6. Provide evidence and reasoning for each claim
7. Flag low-confidence results

**Helper Functions Needed:**
- `parse_menu_items(text)` - extract dish names and descriptions
- `map_ingredient_to_allergens(ingredient)` - allergen database lookup
- `apply_cuisine_priors(cuisine, allergens)` - adjust probabilities
- `calculate_venue_allergen_summary(dishes)` - aggregate scores
- `generate_evidence_snippet(dish, allergen)` - cite sources

**Cuisine Priors Examples:**
```python
CUISINE_PRIORS = {
    'italian': {'gluten': 0.8, 'dairy': 0.7},
    'japanese': {'soy': 0.85, 'fish': 0.75, 'shellfish': 0.4},
    'indian': {'dairy': 0.6, 'tree_nuts': 0.5},
    'vegan': {'dairy': 0.0, 'eggs': 0.0}
}
```

---

## 8. Review Enricher Agent

**Role:** Aggregates ratings, review counts, and extracts review topics/sentiment.

**Model:** Claude Haiku 4.5

**Inputs:**
- Restaurant ID
- Restaurant name + location
- Existing rating/count (from enrichment agent)

**Outputs:**
```python
{
    'restaurant_id': str,
    'rating': float,
    'review_count': int,
    'rating_distribution': {
        '5_star': int,
        '4_star': int,
        '3_star': int,
        '2_star': int,
        '1_star': int
    },
    'topics': [
        {
            'label': str,  # e.g., 'service', 'food_quality', 'wait_time'
            'sentiment': float,  # -1.0 to 1.0
            'mention_count': int,
            'sample_snippets': [str]
        }
    ],
    'common_praise': [str],  # e.g., "excellent fries", "friendly staff"
    'common_complaints': [str],
    'provenance': [
        {
            'provider': str,
            'last_updated': str,
            'review_count': int
        }
    ],
    'updated_at': str
}
```

**Dependencies:**
- Data Enrichment Agent (provides initial ratings)
- Web Search (for review snippets)

**Key Responsibilities:**
1. Verify ratings from multiple sources
2. Extract review snippets via search
3. Identify common topics (food, service, ambience, value)
4. Perform sentiment analysis on topics
5. Summarize praise and complaints
6. Track provenance and freshness

**Helper Functions Needed:**
- `search_restaurant_reviews(name, location)` - find review snippets
- `extract_topics(review_snippets)` - cluster common themes
- `analyze_sentiment(text, topic)` - score sentiment per topic
- `aggregate_ratings(sources)` - combine multi-source ratings
- `generate_review_summary(topics)` - create human-readable summary

---

## 9. Image Scraper Agent

**Role:** Collects high-quality venue images, filters for relevance and safety.

**Model:** Claude Haiku 4.5 + Image Analysis

**Inputs:**
- Restaurant ID
- Restaurant name
- Website URL
- Image hints (from enrichment)

**Outputs:**
```python
{
    'restaurant_id': str,
    'images': [
        {
            'url': str,
            'width': int,
            'height': int,
            'source': str,  # 'website' | 'google' | 'yelp' | 'instagram'
            'type': str,  # 'exterior' | 'interior' | 'food' | 'menu'
            'relevance_score': float,
            'safe_content': bool,
            'perceptual_hash': str  # for deduplication
        }
    ],
    'total_scraped': int,
    'total_filtered': int,
    'provenance': [str],
    'last_updated': str
}
```

**Dependencies:**
- Data Enrichment Agent (provides URLs)
- Web Search

**Key Responsibilities:**
1. Scrape images from official website
2. Search for venue images online
3. Deduplicate by perceptual hash
4. Filter out logos, ads, irrelevant content
5. Remove/blur faces if required (privacy)
6. Classify image types (exterior, interior, food, menu)
7. Score relevance and quality
8. Respect copyright and usage rights

**Helper Functions Needed:**
- `scrape_images_from_url(url)` - extract images from HTML
- `calculate_perceptual_hash(image)` - for deduplication
- `classify_image_type(image_url)` - categorize image
- `detect_faces(image)` - identify faces for privacy
- `score_image_quality(image)` - assess resolution, blur, etc.
- `check_copyright(image_url)` - verify usage rights

---

## 10. Safety & QA Agent

**Role:** Validates data quality, checks scraping compliance, flags low-confidence results.

**Model:** Claude Haiku 4.5

**Inputs:**
- Complete restaurant record (all enriched data)
- Scraping metadata (domains accessed, robots.txt status)
- Confidence scores from all agents

**Outputs:**
```python
{
    'restaurant_id': str,
    'passed_qa': bool,
    'issues': [
        {
            'severity': 'error' | 'warning' | 'info',
            'category': str,  # 'scraping' | 'data_quality' | 'confidence' | 'pii'
            'message': str,
            'field': str | None,
            'recommendation': str
        }
    ],
    'confidence_flags': {
        'rating': bool,  # true if low confidence
        'allergens': bool,
        'menu': bool,
        'images': bool
    },
    'compliance': {
        'robots_txt_respected': bool,
        'rate_limits_honored': bool,
        'copyright_violations': [str]
    },
    'pii_detected': [
        {
            'field': str,
            'type': str,  # 'email' | 'phone' | 'address'
            'action_taken': str
        }
    ],
    'timestamp': str
}
```

**Dependencies:**
- All other agents (validates their outputs)

**Key Responsibilities:**
1. Check minimum evidence requirements (e.g., allergens need menu source)
2. Validate scraping compliance (robots.txt, rate limits)
3. Detect and redact PII in OCR text
4. Flag low-confidence allergen claims
5. Verify data consistency (e.g., address matches location)
6. Check for unsafe content in images
7. Recommend re-enrichment for stale data

**Helper Functions Needed:**
- `validate_allergen_evidence(allergen_report)` - check evidence quality
- `detect_pii_in_text(text)` - find personal information
- `check_scraping_compliance(domains_accessed)` - verify robots.txt
- `validate_data_consistency(restaurant)` - cross-field checks
- `calculate_overall_confidence(agent_scores)` - aggregate confidence

**QA Rules:**
```python
QA_RULES = {
    'min_allergen_evidence': 2,  # need at least 2 evidence items
    'min_rating_sources': 1,
    'max_scrape_rate_per_domain': 1,  # req/sec
    'max_data_age_days': 14,
    'min_confidence_threshold': 0.6
}
```

---

## 11. Ranker Agent

**Role:** Re-ranks restaurant results based on user query, preferences, and context.

**Model:** Claude Sonnet 4.5 (complex ranking logic)

**Inputs:**
- List of enriched restaurants
- User query interpretation (from NL Interpreter)
- User location
- Boost parameters
- Ranking strategy ('distance' | 'rating' | 'relevance' | 'hybrid')

**Outputs:**
```python
{
    'ranked_results': [
        {
            'restaurant': dict,  # full enriched restaurant object
            'rank': int,
            'score': float,
            'score_breakdown': {
                'distance': float,
                'rating': float,
                'review_count': float,
                'nl_relevance': float,
                'allergen_fit': float,
                'hours_match': float
            },
            'explanation': str  # why this ranking
        }
    ],
    'ranking_strategy': str,
    'filters_applied': dict,
    'boosts_applied': dict,
    'total_candidates': int,
    'total_returned': int
}
```

**Dependencies:**
- All enrichment agents (needs complete data)
- NL Query Interpreter (for boosts)

**Key Responsibilities:**
1. Apply hard filters (cuisine, dietary, distance)
2. Calculate base scores (distance, rating, review_count)
3. Apply NL relevance boosts
4. Factor in allergen fit for dietary restrictions
5. Boost for "open now" if temporal intent detected
6. Normalize and combine scores
7. Generate explanations for top results
8. Handle edge cases (no ratings, missing data)

**Helper Functions Needed:**
- `apply_filters(restaurants, filters)` - hard filter candidates
- `calculate_distance_score(distance_miles)` - distance decay function
- `calculate_rating_score(rating, review_count)` - rating with confidence
- `calculate_nl_relevance(restaurant, query)` - semantic matching
- `calculate_allergen_fit(allergen_summary, dietary_restrictions)` - safety score
- `normalize_scores(scores)` - min-max normalization
- `combine_scores(score_breakdown, boosts)` - weighted sum
- `generate_ranking_explanation(restaurant, score_breakdown)` - explain why

**Ranking Strategies:**
```python
RANKING_STRATEGIES = {
    'distance': {
        'distance': 0.7,
        'rating': 0.2,
        'review_count': 0.1
    },
    'rating': {
        'rating': 0.6,
        'review_count': 0.3,
        'distance': 0.1
    },
    'relevance': {
        'nl_relevance': 0.5,
        'rating': 0.3,
        'distance': 0.2
    },
    'hybrid': {
        'distance': 0.25,
        'rating': 0.25,
        'nl_relevance': 0.25,
        'review_count': 0.15,
        'allergen_fit': 0.1
    }
}
```

---

## Agent Coordination Patterns

### Pattern 1: Simple Proximity Search
```
User: "restaurants near me"
↓
Planner → Restaurant Retrieval → Data Enrichment → Ranker (distance) → Response
```

### Pattern 2: Natural Language Search
```
User: "cozy vegan brunch with outdoor seating"
↓
Planner → Restaurant Retrieval → Data Enrichment
         ↓
         NL Query Interpreter → Ranker (relevance + filters)
         ↓
         Response
```

### Pattern 3: Allergen-Focused Search
```
User: "italian restaurants, gluten-free options"
↓
Planner → Restaurant Retrieval → Data Enrichment
         ↓
         Menu Finder → OCR Worker → Allergen Analyzer
         ↓
         NL Query Interpreter → Ranker (allergen fit high weight)
         ↓
         Safety & QA (validate allergen claims)
         ↓
         Response
```

### Pattern 4: Detail View
```
User: clicks on restaurant detail page
↓
Planner → Data Enrichment (if stale)
         ↓
         Menu Finder → OCR Worker → Allergen Analyzer
         ↓
         Review Enricher
         ↓
         Image Scraper
         ↓
         Safety & QA
         ↓
         Response (full detail view)
```

---

## Data Flow

```
OSM Data (restaurant_retrieval.py)
    ↓
Data Enrichment Agent (+ web search)
    ↓
    ├─→ Menu Finder → OCR Worker → Allergen Analyzer
    ├─→ Review Enricher
    └─→ Image Scraper
    ↓
Safety & QA Agent
    ↓
Ranker Agent
    ↓
API Response (Flask)
    ↓
Frontend (Next.js)
```

---

## Caching Strategy

**Redis Keys:**
- `restaurant:osm:{osm_id}` - TTL: 7 days (OSM data)
- `restaurant:enriched:{restaurant_id}` - TTL: 14 days (enriched data)
- `allergen:report:{restaurant_id}` - TTL: 14 days (allergen analysis)
- `reviews:stats:{restaurant_id}` - TTL: 3 days (review data changes frequently)
- `images:{restaurant_id}` - TTL: 30 days (images rarely change)
- `geo:{geohash}:{radius}:{limit}` - TTL: 6 hours (proximity queries)

**Cache Invalidation:**
- Manual invalidation API endpoint for restaurant owners
- Automatic refresh if data older than TTL
- Force refresh flag in enrichment requests

---

## Error Handling

Each agent should return structured errors:

```python
{
    'status': 'success' | 'partial' | 'error',
    'data': dict | None,
    'errors': [
        {
            'code': str,
            'message': str,
            'recoverable': bool,
            'retry_after_sec': int | None
        }
    ],
    'warnings': [str]
}
```

**Common Error Codes:**
- `UPSTREAM_TIMEOUT` - external API timeout
- `RATE_LIMITED` - hit rate limit
- `NO_DATA_FOUND` - no results
- `OCR_FAILED` - OCR engine error
- `INVALID_INPUT` - bad parameters
- `SCRAPING_FORBIDDEN` - robots.txt violation

---

## Performance Targets

| Agent | Target Latency | Timeout |
|-------|----------------|---------|
| Restaurant Retrieval | < 500ms | 2s |
| Data Enrichment | < 2s | 5s |
| NL Query Interpreter | < 500ms | 2s |
| Menu Finder | < 3s | 10s |
| OCR Worker | < 2s per image | 5s |
| Allergen Analyzer | < 3s | 10s |
| Review Enricher | < 2s | 5s |
| Image Scraper | < 5s | 15s |
| Ranker | < 500ms | 2s |
| Safety & QA | < 1s | 3s |

**End-to-End Targets:**
- Simple proximity search: < 3s
- NL search with enrichment: < 8s
- Full detail view (lazy load): < 10s for initial, < 5s for each enrichment

---

## Development Priorities

**Phase 1 (MVP):**
1. Restaurant Retrieval (✅ done)
2. Data Enrichment Agent (ratings, basic info)
3. Planner Agent (basic routing)
4. Ranker Agent (distance + rating)

**Phase 2 (Core Features):**
5. NL Query Interpreter
6. Menu Finder
7. Allergen Analyzer
8. Safety & QA

**Phase 3 (Enhancements):**
9. OCR Worker
10. Review Enricher
11. Image Scraper

---

This framework provides the foundation for building each agent. Next step: detailed implementation prompts for each agent.