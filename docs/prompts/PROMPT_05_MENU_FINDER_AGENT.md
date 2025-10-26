# PROMPT 5: Menu Finder Agent Implementation Guide

## Context
You are building the **Menu Finder Agent**, which locates menu URLs (text, PDF, and images) for restaurants. This agent is critical for the allergen analysis pipeline, as it provides the source material for the OCR Worker and Allergen Analyzer agents.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- LLM: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) for menu URL validation
- Web Search: Claude's web search capability
- Backend: Flask API
- Caching: Redis (7-day TTL for menu URLs)
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The Menu Finder Agent must:
1. **Search for menus** - Find menu URLs from multiple sources
2. **Validate URLs** - Verify links actually contain menu content
3. **Categorize menu types** - Classify as text/HTML, PDF, or image
4. **Check menu platforms** - Search Toast, Grubhub, DoorDash, etc.
5. **Scrape official websites** - Find menus on restaurant's own site
6. **Find social media menus** - Check Instagram, Facebook for menu posts
7. **Deduplicate results** - Avoid returning duplicate menus
8. **Respect robots.txt** - Follow scraping rules and rate limits
9. **Cache results** - Store found menus to avoid redundant searches
10. **Track provenance** - Record where each menu was found

---

## 2. File Structure

**Create:** `agents/menu_finder_agent.py`

This file should contain:

### 2.1 Menu Type Enum
Define types of menus:
- `TEXT_HTML` - Text-based web menu
- `PDF` - PDF document menu
- `IMAGE` - Menu in image format (JPG, PNG)
- `EMBEDDED_PDF` - PDF embedded in webpage
- `SOCIAL_MEDIA` - Menu posted on social platform

### 2.2 Menu Source Enum
Define where menus are found:
- `OFFICIAL_WEBSITE` - Restaurant's own website
- `TOAST` - Toast POS menu platform
- `GRUBHUB` - Grubhub menu
- `DOORDASH` - DoorDash menu
- `UBEREATS` - UberEats menu
- `YELP` - Yelp menu section
- `GOOGLE` - Google Business menu
- `INSTAGRAM` - Instagram menu posts
- `FACEBOOK` - Facebook menu
- `OPENTABLE` - OpenTable menu
- `WEBSITE_EMBED` - Third-party embed on website
- `OTHER` - Other sources

### 2.3 Validation Status Enum
Define URL validation states:
- `VALID` - URL confirmed to contain menu
- `LIKELY_VALID` - URL looks like menu but not fully verified
- `INVALID` - URL doesn't contain menu
- `INACCESSIBLE` - URL returns error (404, 403, timeout)
- `NEEDS_LOGIN` - Menu behind authentication
- `ROBOTS_BLOCKED` - robots.txt prevents access

### 2.4 Core Classes

**MenuSearchRequest Class:**
Represents a menu search job. Should include:
- `restaurant_id`: str - Unique identifier
- `restaurant_name`: str - Name for search queries
- `address`: Optional[str] - Full address if available
- `city`: str - City for context
- `state`: Optional[str] - State for context
- `website`: Optional[str] - Official website hint
- `cuisine`: Optional[str] - Cuisine type (helps validate menus)
- `user_hints`: List[str] - URLs user suggested
- `force_refresh`: bool - Bypass cache

**MenuURL Class:**
Represents a found menu URL. Should include:
- `url`: str - Full URL to menu
- `menu_type`: MenuType - Text, PDF, or image
- `source`: MenuSource - Where it was found
- `validation_status`: ValidationStatus - Verified or not
- `confidence`: float - How confident this is a menu (0.0-1.0)
- `content_preview`: Optional[str] - First 200 chars of content
- `file_size_bytes`: Optional[int] - For PDFs/images
- `last_checked`: str - ISO timestamp
- `metadata`: Dict - Additional info (dimensions for images, page count for PDFs)

**MenuSearchResult Class:**
Complete search results. Should include:
- `restaurant_id`: str
- `restaurant_name`: str
- `menu_text_urls`: List[MenuURL] - Text/HTML menus
- `menu_pdf_urls`: List[MenuURL] - PDF menus
- `menu_image_urls`: List[MenuURL] - Image menus
- `social_media_menus`: List[MenuURL] - Social media posts
- `total_found`: int - Total menus discovered
- `search_queries_used`: List[str] - Queries that found results
- `sources_checked`: List[str] - All sources searched
- `cache_hit`: bool - Whether results from cache
- `provenance`: Dict - Detailed source tracking
- `confidence`: float - Overall confidence in results
- `warnings`: List[str] - Issues encountered

**MenuFinderAgent Class:**
Main agent implementation. Should include methods:
- `__init__()` - Initialize clients, cache, rate limiters
- `find_menus()` - Main entry point
- `_search_official_website()` - Check restaurant's website
- `_search_menu_platforms()` - Check Toast, Grubhub, etc.
- `_search_social_media()` - Check Instagram, Facebook
- `_web_search_for_menus()` - General web search
- `_validate_menu_url()` - Verify URL contains menu
- `_classify_menu_type()` - Determine if text, PDF, or image
- `_check_robots_txt()` - Verify scraping allowed
- `_deduplicate_menus()` - Remove duplicates
- `_calculate_confidence()` - Score result quality
- `_get_from_cache()` - Check Redis cache
- `_save_to_cache()` - Store results

---

## 3. Input/Output Contracts

### 3.1 Input Format (from Planner Agent)
Receives menu search requests in this format:
```python
{
    'restaurant_id': 'rest_123',
    'restaurant_name': 'Super Duper Burger',
    'address': '2304 Shattuck Ave, Berkeley, CA 94704',
    'city': 'Berkeley',
    'state': 'CA',
    'website': 'https://superduperburger.com',  # from enrichment agent
    'cuisine': 'burger',
    'user_hints': [
        'https://instagram.com/superduperburger',
        'https://example.com/menu'
    ],
    'force_refresh': False
}
```

### 3.2 Output Format (to OCR Worker & Allergen Analyzer)
Must return menu search results in this format:
```python
{
    'status': 'success' | 'partial' | 'no_menus_found' | 'error',
    
    'restaurant_id': 'rest_123',
    'restaurant_name': 'Super Duper Burger',
    
    'menu_text_urls': [
        {
            'url': 'https://superduperburger.com/menu',
            'menu_type': 'TEXT_HTML',
            'source': 'OFFICIAL_WEBSITE',
            'validation_status': 'VALID',
            'confidence': 0.95,
            'content_preview': 'MENU\nBurgers\nSuper Duper Burger...',
            'file_size_bytes': None,
            'last_checked': '2025-10-26T10:30:00Z',
            'metadata': {
                'has_prices': True,
                'language': 'en',
                'sections': ['burgers', 'sides', 'drinks']
            }
        }
    ],
    
    'menu_pdf_urls': [
        {
            'url': 'https://superduperburger.com/menu.pdf',
            'menu_type': 'PDF',
            'source': 'OFFICIAL_WEBSITE',
            'validation_status': 'VALID',
            'confidence': 0.98,
            'content_preview': None,
            'file_size_bytes': 245678,
            'last_checked': '2025-10-26T10:30:05Z',
            'metadata': {
                'pages': 2,
                'pdf_version': '1.4'
            }
        }
    ],
    
    'menu_image_urls': [
        {
            'url': 'https://instagram.com/p/xyz/menu.jpg',
            'menu_type': 'IMAGE',
            'source': 'INSTAGRAM',
            'validation_status': 'LIKELY_VALID',
            'confidence': 0.75,
            'content_preview': None,
            'file_size_bytes': 342156,
            'last_checked': '2025-10-26T10:30:10Z',
            'metadata': {
                'width': 1080,
                'height': 1920,
                'format': 'JPEG'
            }
        }
    ],
    
    'social_media_menus': [
        {
            'url': 'https://instagram.com/superduperburger',
            'menu_type': 'IMAGE',
            'source': 'INSTAGRAM',
            'validation_status': 'LIKELY_VALID',
            'confidence': 0.70,
            'last_checked': '2025-10-26T10:30:10Z',
            'metadata': {
                'platform': 'instagram',
                'post_count': 3  # menu images found
            }
        }
    ],
    
    'total_found': 4,
    
    'search_queries_used': [
        'Super Duper Burger Berkeley menu',
        'Super Duper Burger online menu',
        'site:superduperburger.com menu'
    ],
    
    'sources_checked': [
        'OFFICIAL_WEBSITE',
        'TOAST',
        'GRUBHUB',
        'INSTAGRAM'
    ],
    
    'cache_hit': False,
    
    'provenance': {
        'official_website_checked': True,
        'official_website_found': True,
        'menu_platforms_checked': ['TOAST', 'GRUBHUB', 'DOORDASH'],
        'menu_platforms_found': [],
        'social_media_checked': ['INSTAGRAM'],
        'social_media_found': ['INSTAGRAM']
    },
    
    'confidence': 0.88,  # overall confidence
    
    'warnings': [
        'Instagram menu images may require manual verification',
        'Some menu platforms returned no results'
    ],
    
    'metadata': {
        'search_time_ms': 3245,
        'urls_checked': 12,
        'urls_validated': 4,
        'cache_key': 'menu:rest_123:abc...',
        'robots_violations': 0
    }
}
```

---

## 4. Menu Search Strategies

### 4.1 Official Website Search

**Strategy:**
```
1. If website URL provided:
   - Fetch homepage
   - Look for "menu" links in navigation
   - Check common menu paths: /menu, /food-menu, /our-menu
   - Check for menu PDF links
   
2. Parse HTML for menu content:
   - Look for <div> or <section> with class/id containing "menu"
   - Look for text patterns: "MENU", "Food Menu", "Our Menu"
   - Identify food items (prices with $, dish descriptions)
   
3. Common URL patterns to try:
   - https://restaurant.com/menu
   - https://restaurant.com/food
   - https://restaurant.com/menu.pdf
   - https://restaurant.com/menus
   - https://restaurant.com/our-menu
```

**Validation:**
```
URL is valid menu if:
- Contains food-related keywords (burger, pasta, chicken, etc.)
- Has prices ($5, $10.99, etc.)
- Has section headers (Appetizers, Entrees, Desserts)
- Has multiple food items listed
```

### 4.2 Menu Platform Search

**Platforms to Check:**
```
1. Toast (toast.com)
   - Search: "restaurant_name toast menu"
   - URL pattern: toast.com/menus/restaurant-slug
   
2. Grubhub (grubhub.com)
   - Search: "restaurant_name grubhub"
   - URL pattern: grubhub.com/restaurant/restaurant-slug
   
3. DoorDash (doordash.com)
   - Search: "restaurant_name doordash"
   - URL pattern: doordash.com/store/restaurant-slug
   
4. UberEats (ubereats.com)
   - Search: "restaurant_name ubereats"
   - URL pattern: ubereats.com/store/restaurant-slug
   
5. Yelp (yelp.com)
   - Search: "restaurant_name yelp menu"
   - URL pattern: yelp.com/biz/restaurant-slug
   - Check "Menu" tab
   
6. OpenTable (opentable.com)
   - Search: "restaurant_name opentable"
   - May have menu in reservation page
```

**Search Query Template:**
```
"{restaurant_name} {platform_name} menu {city}"
Example: "Super Duper Burger toast menu Berkeley"
```

### 4.3 Social Media Search

**Instagram:**
```
Search: "instagram.com/restaurant_name" or "restaurant_name instagram menu"

Look for:
- Restaurant profile page
- Highlighted stories with "Menu" label
- Posts with menu images (check last 20 posts)
- Menu in bio link

Validation:
- Image contains text (likely menu)
- Caption mentions "menu", "check out our menu"
- Multiple items visible in image
```

**Facebook:**
```
Search: "facebook.com/restaurant_name" or "restaurant_name facebook menu"

Look for:
- Menu tab on business page
- Pinned menu posts
- Photo albums named "Menu"

Validation:
- Page is verified business
- Menu section populated
```

### 4.4 General Web Search

**Primary Query:**
```
"{restaurant_name} {city} menu"
Example: "Super Duper Burger Berkeley menu"
```

**Refinement Queries:**
```
1. "{restaurant_name} online menu {city}"
2. "{restaurant_name} food menu"
3. "site:{website_domain} menu"
4. "{restaurant_name} menu pdf"
```

**Result Filtering:**
```
Include URLs that:
- Come from restaurant's domain
- Come from known menu platforms
- Have "menu" in URL path
- Return HTML with menu content
- Return PDF files

Exclude URLs that:
- Are review sites (unless they have menu section)
- Are job posting sites
- Are news articles
- Are unrelated businesses
```

---

## 5. URL Validation Methods

### 5.1 Content-Based Validation

**Text/HTML Menus:**
```
Validation criteria:
1. Content length: 500-50,000 characters (too short or too long unlikely to be menu)
2. Food keyword density: At least 5% of words are food-related
3. Price indicators: Contains $ symbols or "price" mentions
4. Section headers: Contains words like "appetizers", "entrees", "sides", "desserts"
5. Item format: Lines with item name followed by price

Confidence scoring:
- 0.9+: All criteria met, clear menu structure
- 0.7-0.89: Most criteria met, likely menu
- 0.5-0.69: Some criteria met, possible menu
- <0.5: Few criteria met, probably not menu
```

**PDF Menus:**
```
Validation criteria:
1. File size: 50KB - 10MB (within reasonable range)
2. Page count: 1-20 pages (too many pages unlikely to be menu)
3. File name: Contains "menu" keyword
4. PDF metadata: Title contains restaurant name or "menu"

Confidence scoring:
- 0.95+: Filename is "menu.pdf" from official site
- 0.8-0.94: PDF from official site, reasonable size
- 0.6-0.79: PDF from third-party, reasonable attributes
- <0.6: PDF questionable (too large, generic name)
```

**Image Menus:**
```
Validation criteria:
1. Image dimensions: Width > 400px, Height > 600px (large enough to read)
2. Aspect ratio: Portrait (menus are typically vertical)
3. File size: > 50KB (high enough resolution)
4. Source: From social media or official site
5. Image contains text (requires light OCR or Claude vision)

Confidence scoring:
- 0.9+: Clear menu image from official source
- 0.7-0.89: Likely menu from social media
- 0.5-0.69: Possible menu, needs verification
- <0.5: Image unclear or not menu
```

### 5.2 Claude-Based Validation

Use Claude Haiku to validate ambiguous URLs:

**Validation Prompt:**
```
System: You are a menu validation assistant. Determine if the given content is a restaurant menu.

User: Is this a restaurant menu?

Restaurant: {restaurant_name}
Cuisine: {cuisine}

Content preview:
{first_500_chars}

URL: {url}

Analyze and return JSON:
{
  "is_menu": bool,
  "confidence": float,  // 0.0-1.0
  "reasoning": string,
  "menu_sections_found": [string],  // e.g., ["Appetizers", "Entrees"]
  "has_prices": bool,
  "language": string
}

Consider:
1. Does it list food items?
2. Does it have prices?
3. Does it have section headers?
4. Is it relevant to the restaurant and cuisine?
5. Is it current (not old menu from different restaurant)?
```

---

## 6. Helper Functions to Create

### 6.1 Website Menu Finder Helper
**Function:** `_search_official_website(website: str, restaurant_name: str) -> List[MenuURL]`

**Purpose:** Find menus on restaurant's official website

**Should try:**
- Homepage parsing for menu links
- Common menu URL paths (/menu, /food-menu, /our-menu)
- PDF links in navigation
- Menu embedded in different pages

**Should handle:**
- JavaScript-rendered menus (may need to note "requires browser rendering")
- Menu behind "View Menu" buttons
- Multi-page menus (separate pages for lunch/dinner)
- Franchise sites with location-specific menus

**Returns:** List of MenuURL objects found on website

### 6.2 Menu Platform Searcher Helper
**Function:** `_search_menu_platforms(restaurant_name: str, city: str) -> List[MenuURL]`

**Purpose:** Search known menu platforms

**Should check:**
- Toast, Grubhub, DoorDash, UberEats
- Construct platform-specific search queries
- Parse platform-specific URL patterns
- Validate menu is for correct restaurant

**Should handle:**
- Multiple locations (filter by city)
- Chain restaurants (ensure correct location)
- Platform requires login (mark as NEEDS_LOGIN)

**Returns:** List of MenuURL objects from platforms

### 6.3 Social Media Menu Finder Helper
**Function:** `_search_social_media(restaurant_name: str, user_hints: List[str]) -> List[MenuURL]`

**Purpose:** Find menu images on social media

**Should check:**
- Instagram profile and posts
- Facebook business page
- User-provided social media hints

**Should look for:**
- "Menu" highlight on Instagram
- Posts with #menu hashtag
- Images that look like menus (text-heavy, vertical layout)

**Should handle:**
- Authentication requirements
- Rate limiting on social platforms
- Privacy settings (private profiles)

**Returns:** List of MenuURL objects from social media

### 6.4 Web Search Helper
**Function:** `_web_search_for_menus(restaurant_name: str, city: str, cuisine: str) -> List[str]`

**Purpose:** General web search for menu URLs

**Should perform:**
- Primary search: "{name} {city} menu"
- Refinement searches if needed
- Site-specific search if website known

**Should extract:**
- URLs from search results
- Snippets mentioning "menu"
- Direct menu links

**Returns:** List of candidate URLs

### 6.5 URL Validator Helper
**Function:** `_validate_menu_url(url: str, restaurant_name: str, cuisine: str) -> Tuple[ValidationStatus, float]`

**Purpose:** Verify URL contains actual menu content

**Should perform:**
- HEAD request (check content-type, size)
- GET request (fetch content)
- Content analysis (food keywords, prices, structure)
- Claude validation if ambiguous

**Should check:**
- robots.txt compliance
- Content type (text/html, application/pdf, image/jpeg)
- Response status (200 OK)
- Content relevance to restaurant

**Returns:** (ValidationStatus, confidence_score)

### 6.6 Menu Type Classifier Helper
**Function:** `_classify_menu_type(url: str, content_type: str) -> MenuType`

**Purpose:** Determine if menu is text, PDF, or image

**Should classify based on:**
- URL extension (.pdf, .jpg, .png)
- Content-Type header
- Actual content inspection

**Logic:**
```
If content_type == 'application/pdf' or url.endswith('.pdf'):
  → PDF
Elif content_type in ['image/jpeg', 'image/png', 'image/webp']:
  → IMAGE
Elif content_type == 'text/html':
  If embedded PDF detected:
    → EMBEDDED_PDF
  Else:
    → TEXT_HTML
```

**Returns:** MenuType enum value

### 6.7 Robots.txt Checker Helper
**Function:** `_check_robots_txt(url: str, user_agent: str) -> Tuple[bool, Optional[int]]`

**Purpose:** Verify scraping is allowed and get crawl delay

**Should:**
- Fetch robots.txt from domain
- Parse User-agent rules
- Check if URL path is disallowed
- Extract Crawl-delay if present

**Returns:** (is_allowed: bool, crawl_delay_seconds: Optional[int])

**Example:**
```
URL: https://example.com/menu
robots.txt has:
  User-agent: *
  Disallow: /admin
  Crawl-delay: 2

→ Returns: (True, 2)  # allowed, wait 2 seconds between requests
```

### 6.8 Deduplication Helper
**Function:** `_deduplicate_menus(menus: List[MenuURL]) -> List[MenuURL]`

**Purpose:** Remove duplicate menus

**Should deduplicate by:**
- Exact URL match
- URL normalization (remove tracking params)
- Content hash (if content fetched)
- Domain + path similarity

**Should prioritize:**
- Official website over third-party
- VALID over LIKELY_VALID
- Higher confidence scores
- Text/PDF over images (easier to parse)

**Returns:** Deduplicated list of MenuURL objects

### 6.9 Confidence Calculator Helper
**Function:** `_calculate_confidence(menu_url: MenuURL, validation_result: Dict) -> float`

**Purpose:** Assign confidence score to menu URL

**Should consider:**
- Validation status (VALID > LIKELY_VALID)
- Source reliability (OFFICIAL_WEBSITE > other)
- Content quality (has prices, sections, items)
- URL credibility (clean URL, not suspicious)

**Formula suggestion:**
```
base_confidence = {
  'VALID': 0.9,
  'LIKELY_VALID': 0.7,
  'INVALID': 0.0,
  'INACCESSIBLE': 0.0,
  'NEEDS_LOGIN': 0.3,
  'ROBOTS_BLOCKED': 0.0
}

source_multiplier = {
  'OFFICIAL_WEBSITE': 1.0,
  'TOAST': 0.95,
  'GRUBHUB': 0.9,
  'INSTAGRAM': 0.75,
  'OTHER': 0.6
}

final_confidence = base_confidence * source_multiplier * content_quality_score
```

**Returns:** Confidence score (0.0-1.0)

### 6.10 Cache Management Helpers

**Function:** `_generate_cache_key(restaurant_id: str) -> str`

**Purpose:** Generate unique cache key for restaurant menus

**Format:** `menu:{restaurant_id}`

**Function:** `_get_from_cache(cache_key: str) -> Optional[MenuSearchResult]`

**Purpose:** Check Redis for cached menu results

**Should:**
- Deserialize cached JSON
- Check if cache is stale (> 7 days)
- Validate cached URLs still accessible

**Function:** `_save_to_cache(cache_key: str, result: MenuSearchResult, ttl: int = 604800)`

**Purpose:** Save menu results to Redis (7 days = 604800 seconds)

**Should:**
- Serialize to JSON
- Set TTL appropriately
- Include timestamp for freshness tracking

---

## 7. Integration Guardrails

### 7.1 Input Validation
Before searching:
- ✅ Validate restaurant_name is non-empty
- ✅ Validate city is provided (required for search context)
- ✅ Validate website URL format if provided
- ✅ Validate user_hints are valid URLs

### 7.2 Output Contract Compliance
MUST return exact format expected by OCR Worker/Allergen Analyzer:
- ✅ Separate arrays for text, PDF, and image menus
- ✅ Each MenuURL has all required fields
- ✅ Validation status is valid enum value
- ✅ Confidence scores are 0.0-1.0
- ✅ Provenance tracks all sources checked
- ✅ Metadata includes search statistics

### 7.3 Rate Limiting and Robots.txt
MUST respect web scraping etiquette:
- ✅ Check robots.txt before scraping any domain
- ✅ Honor Crawl-delay directives
- ✅ Limit to 1 request/second per domain (default)
- ✅ Set proper User-Agent header
- ✅ Handle 429 (Too Many Requests) gracefully
- ✅ Log all robots.txt violations

### 7.4 Error Handling Strategy
```
Critical Errors (return status='error'):
- No restaurant name provided
- All web requests fail (network down)

Recoverable Errors (return status='partial'):
- Some sources inaccessible (timeout, 404)
- robots.txt blocks some URLs
- Validation fails for some URLs

Non-Fatal Warnings:
- No PDF menus found
- Social media requires login
- Some menu platforms returned no results
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test: Official Website Menu Finding**
```
Input: {website: 'https://example.com', name: 'Test Restaurant'}
Mock: Website has /menu page with valid menu content
Expected: Returns MenuURL with url='/menu', type=TEXT_HTML, confidence>0.8
```

**Test: PDF Detection**
```
Input: URL ending in .pdf
Mock: Content-Type is application/pdf, size is 500KB
Expected: MenuType=PDF, validation=VALID
```

**Test: Menu Content Validation**
```
Input: HTML content with food items, prices, sections
Expected: validation=VALID, confidence>0.8

Input: HTML content that's actually a blog post
Expected: validation=INVALID, confidence<0.3
```

**Test: Robots.txt Compliance**
```
Mock: robots.txt disallows /menu
Expected: Returns validation=ROBOTS_BLOCKED, doesn't attempt to scrape
```

**Test: Deduplication**
```
Input: [url1, url2 (same as url1 with tracking params), url3]
Expected: Returns [url1, url3] (url2 removed as duplicate)
```

### 8.2 Integration Tests

**Test: End-to-End Menu Search**
```
Input: Restaurant with known website
Process: Check website → check platforms → validate
Verify:
- At least 1 menu URL found
- All URLs validated
- Confidence scores assigned
- Provenance tracked
```

**Test: Multi-Source Search**
```
Input: Restaurant on Toast and Instagram
Verify:
- Both sources checked
- Both menus found
- Deduplicated if same content
- Sources tracked in provenance
```

**Test: Cache Hit/Miss**
```
First call: Cache miss, performs search, saves to cache
Second call: Cache hit, returns cached results
Verify: cache_hit flag correct in both cases
```

**Test: No Menus Found**
```
Input: Restaurant with no online menu
Expected: status='no_menus_found', warnings about checked sources
```

### 8.3 Edge Case Tests

**Test: Website Behind Cloudflare**
```
Input: Restaurant website with bot protection
Expected: Graceful handling, mark as INACCESSIBLE
```

**Test: Menu Requires JavaScript**
```
Input: Single-page app with JS-rendered menu
Expected: Note in warnings that JS rendering needed
```

**Test: Multiple Menu PDFs**
```
Input: Restaurant with lunch.pdf, dinner.pdf, drinks.pdf
Expected: All three found and categorized
```

**Test: Franchise with Multiple Locations**
```
Input: Chain restaurant, search for specific location
Expected: Only menus for that location returned
```

---

## 9. Example Menu Finding Flows

### Example 1: Successful Official Website Find
```
Input:
{
  'restaurant_name': 'Super Duper Burger',
  'website': 'https://superduperburger.com',
  'city': 'Berkeley'
}

Processing:
1. Check cache: MISS
2. Check robots.txt for superduperburger.com: Allowed
3. Fetch homepage: Success
4. Find menu link: <a href="/menu">Menu</a>
5. Fetch /menu page: Success
6. Validate content: Contains food items, prices, sections
7. Classify: TEXT_HTML
8. Confidence: 0.95 (official site, clear menu)
9. Save to cache

Output:
{
  'status': 'success',
  'menu_text_urls': [
    {
      'url': 'https://superduperburger.com/menu',
      'menu_type': 'TEXT_HTML',
      'source': 'OFFICIAL_WEBSITE',
      'validation_status': 'VALID',
      'confidence': 0.95
    }
  ],
  'menu_pdf_urls': [],
  'menu_image_urls': [],
  'total_found': 1,
  'cache_hit': False,
  'confidence': 0.95
}
```

### Example 2: Multi-Source Find with PDF and Images
```
Input:
{
  'restaurant_name': 'Italian Kitchen',
  'website': 'https://italiankitchen.com',
  'city': 'San Francisco',
  'user_hints': ['https://instagram.com/italiankitchen']
}

Processing:
1. Check official website:
   - Find https://italiankitchen.com/menu.pdf
   - Validate: PDF, 3 pages, 1.2MB
   - Confidence: 0.98

2. Check Toast:
   - Find https://toast.com/menus/italian-kitchen-sf
   - Validate: HTML menu with items and prices
   - Confidence: 0.85

3. Check Instagram (from user hint):
   - Find profile with menu in highlights
   - 3 menu image posts found
   - Confidence: 0.70 (requires verification)

4. Deduplicate:
   - Toast menu is duplicate of website menu (same items)
   - Keep website version (higher confidence)

5. Save to cache

Output:
{
  'status': 'success',
  'menu_text_urls': [],
  'menu_pdf_urls': [
    {
      'url': 'https://italiankitchen.com/menu.pdf',
      'menu_type': 'PDF',
      'source': 'OFFICIAL_WEBSITE',
      'validation_status': 'VALID',
      'confidence': 0.98,
      'metadata': {'pages': 3, 'file_size_bytes': 1228800}
    }
  ],
  'menu_image_urls': [
    {
      'url': 'https://instagram.com/p/xyz123',
      'menu_type': 'IMAGE',
      'source': 'INSTAGRAM',
      'validation_status': 'LIKELY_VALID',
      'confidence': 0.70
    }
  ],
  'total_found': 2,
  'confidence': 0.84,
  'warnings': ['Instagram menu images may need verification']
}
```

### Example 3: No Menus Found
```
Input:
{
  'restaurant_name': 'Small Local Cafe',
  'city': 'Berkeley',
  'website': None
}

Processing:
1. No website provided
2. Web search: "Small Local Cafe Berkeley menu"
   - Results: Review sites, no menu links
3. Check menu platforms:
   - Toast: Not found
   - Grubhub: Not found
   - DoorDash: Not found
4. Check social media:
   - Instagram: Account not found
   - Facebook: Page exists but no menu

Output:
{
  'status': 'no_menus_found',
  'menu_text_urls': [],
  'menu_pdf_urls': [],
  'menu_image_urls': [],
  'total_found': 0,
  'sources_checked': ['WEB_SEARCH', 'TOAST', 'GRUBHUB', 'DOORDASH', 'INSTAGRAM', 'FACEBOOK'],
  'confidence': 0.0,
  'warnings': [
    'No official website found',
    'Not listed on major menu platforms',
    'No social media menu found',
    'Manual menu entry may be required'
  ]
}
```

### Example 4: Partial Success with Blocked Access
```
Input:
{
  'restaurant_name': 'Private Club Restaurant',
  'website': 'https://privateclub.com'
}

Processing:
1. Check robots.txt: Disallows /menu
2. Web search: Find Yelp page
3. Check Yelp: Menu section exists but requires login
4. Check Instagram: Found menu images

Output:
{
  'status': 'partial',
  'menu_text_urls': [],
  'menu_pdf_urls': [],
  'menu_image_urls': [
    {
      'url': 'https://instagram.com/p/menu123',
      'menu_type': 'IMAGE',
      'source': 'INSTAGRAM',
      'validation_status': 'LIKELY_VALID',
      'confidence': 0.65
    }
  ],
  'total_found': 1,
  'warnings': [
    'Official website menu blocked by robots.txt',
    'Yelp menu requires login',
    'Only social media menu available'
  ],
  'confidence': 0.65
}
```

---

## 10. Common Pitfalls to Avoid

1. **❌ Don't ignore robots.txt**
   - Always check before scraping
   - Mark URLs as ROBOTS_BLOCKED if disallowed
   - Respect Crawl-delay directives

2. **❌ Don't scrape without rate limiting**
   - Default to 1 request/second per domain
   - Implement exponential backoff on errors
   - Track per-domain request counts

3. **❌ Don't assume URL is menu**
   - Validate content before adding to results
   - Use Claude for ambiguous cases
   - Set appropriate confidence scores

4. **❌ Don't return outdated menus**
   - Check cache freshness
   - Validate URLs still accessible
   - Note last_checked timestamp

5. **❌ Don't miss PDF menus**
   - Check for .pdf links explicitly
   - Look for "download menu" buttons
   - Check common PDF paths

6. **❌ Don't ignore social media**
   - Many restaurants post menus on Instagram
   - Check Facebook business pages
   - Look for menu in bio links

7. **❌ Don't fail on authentication**
   - Mark as NEEDS_LOGIN instead of error
   - Note in warnings
   - Try alternative sources

8. **❌ Don't return duplicates**
   - Deduplicate by URL normalization
   - Check content similarity
   - Prefer official sources

9. **❌ Don't block on slow sources**
   - Set timeouts (3-5 seconds per source)
   - Continue searching other sources if one fails
   - Return partial results

10. **❌ Don't expose errors to user**
    - Log technical errors
    - Show friendly warnings
    - Suggest alternatives

---

## 11. Success Criteria

The Menu Finder Agent is complete when it:
- ✅ Finds menus from official websites 80%+ of time
- ✅ Checks all major menu platforms (Toast, Grubhub, etc.)
- ✅ Validates menu URLs accurately (>90% precision)
- ✅ Respects robots.txt 100% of time
- ✅ Deduplicates results correctly
- ✅ Completes search in <5 seconds
- ✅ Returns output in exact contract format
- ✅ Handles no menus found gracefully
- ✅ Caches results to avoid redundant searches
- ✅ Tracks provenance for all menu sources
- ✅ Passes all unit and integration tests

---

## 12. Integration Checklist

Before marking complete, verify:
- [ ] Receives restaurant data from Planner/Data Enrichment
- [ ] Web search integration working
- [ ] Robots.txt checker functioning
- [ ] URL validation accurate
- [ ] Menu type classification correct
- [ ] Deduplication logic sound
- [ ] Cache saves and retrieves properly
- [ ] Output format matches OCR Worker expectations
- [ ] Rate limiting prevents abuse
- [ ] Error handling covers all failure modes
- [ ] Tests cover happy path + edge cases
- [ ] Documentation includes example searches

---

## 13. Next Steps

Once Menu Finder Agent is complete:
1. Test with 100 diverse restaurants (chains, local, various cuisines)
2. Measure menu find rate (% of restaurants with menus found)
3. Validate URL accuracy (manual spot-checking)
4. Test robots.txt compliance
5. Optimize search query performance

Then proceed to: **OCR Worker Agent** (extracts text from menu images found by this agent)

---

**Remember:** This agent is CRITICAL for allergen analysis. If menus can't be found, allergen detection fails. Prioritize recall (finding menus) over precision (perfect validation). It's better to pass a questionable menu to OCR/Allergen Analyzer than to miss a valid menu entirely.