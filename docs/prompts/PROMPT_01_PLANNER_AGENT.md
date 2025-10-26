# PROMPT 1: Planner Agent Implementation Guide

## Context
You are building the **Planner Agent**, the central orchestrator for a restaurant recommendation system. This agent interprets user intent and coordinates all other specialized agents to fulfill requests.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- LLM: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- Backend: Flask API
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The Planner Agent must:
1. **Classify user intent** - Determine what the user wants (proximity search, detailed info, allergen inquiry, etc.)
2. **Generate execution plans** - Decide which agents to call and in what order
3. **Route requests** - Coordinate calls to specialized agents
4. **Aggregate results** - Combine outputs from multiple agents
5. **Handle errors** - Implement fallback strategies when agents fail
6. **Maintain context** - Remember conversation history and user preferences

---

## 2. File Structure

**Create:** `agents/planner_agent.py`

This file should contain:

### 2.1 Intent Classification Enum
Define an enum for all possible user intents:
- `PROXIMITY_SEARCH` - "restaurants near me"
- `NL_SEARCH` - "cozy vegan brunch with patio"
- `DETAIL_REQUEST` - user clicked on specific restaurant
- `ALLERGEN_INQUIRY` - "does this have gluten?"
- `REVIEW_REQUEST` - "what do people say about this place?"
- `IMAGE_REQUEST` - "show me photos"
- `FOLLOWUP` - continuing a conversation
- `CLARIFICATION_NEEDED` - ambiguous query
- `CHAT` - general conversation

### 2.2 Enrichment Strategy Enum
Define strategies for data enrichment:
- `EAGER` - fetch everything upfront (for detail views)
- `LAZY` - minimal enrichment (for list views)
- `SELECTIVE` - enrich based on specific query needs

### 2.3 Core Classes

**PlanStep Class:**
Represents a single step in the execution plan. Should include:
- `agent_name`: str - which agent to call
- `tool_name`: str - which tool function
- `params`: Dict - parameters to pass
- `parallel_group`: int - steps with same group run in parallel
- `optional`: bool - if True, failure doesn't stop execution
- `timeout_seconds`: int - max time allowed
- `retry_count`: int - how many retries on failure

**PlannerContext Class:**
Maintains conversation and session state. Should include:
- `session_id`: str
- `user_location`: Dict[str, float] (lat, lon)
- `conversation_history`: List[Dict]
- `last_restaurant_id`: Optional[str]
- `dietary_preferences`: Optional[List[str]]
- `distance_preference_miles`: float
- `cached_results`: Optional[List[Dict]]

**PlannerAgent Class:**
Main agent implementation. Should include these methods:
- `__init__()` - Initialize Letta client, tools, API clients
- `_register_tools()` - Define all available tools
- `create_agent()` - Create Letta agent instance
- `process_query()` - Main entry point for queries
- `_execute_plan()` - Execute plan steps
- `_handle_error()` - Error recovery logic

---

## 3. Tool Registration (Critical Integration Point)

The Planner must register tools that map to other agents. Each tool represents a capability from another agent.

### 3.1 Required Tools

Define these tool schemas in `_register_tools()`:

**Tool 1: retrieve_restaurants**
- **Maps to:** Restaurant Retrieval Agent (uses `helpers/restaurant_retrieval.py`)
- **Parameters:** latitude, longitude, radius_miles, limit
- **When to use:** Always use FIRST for any location-based query
- **Returns:** List of basic restaurant data from OSM
- **Example schema:**
```json
{
  "name": "retrieve_restaurants",
  "description": "Retrieve restaurants within radius using OSM data. Always call this first for location-based queries.",
  "input_schema": {
    "type": "object",
    "properties": {
      "latitude": {"type": "number", "description": "User's latitude"},
      "longitude": {"type": "number", "description": "User's longitude"},
      "radius_miles": {"type": "number", "default": 5.0, "description": "Search radius in miles"},
      "limit": {"type": "integer", "default": 50, "description": "Max results"}
    },
    "required": ["latitude", "longitude"]
  }
}
```

**Tool 2: enrich_restaurant_data**
- **Maps to:** Data Enrichment Agent (to be built next)
- **Parameters:** restaurants (list), priority_fields (list), force_refresh (bool)
- **When to use:** After retrieve_restaurants to add ratings, reviews, contact info
- **Returns:** Enriched restaurant objects with ratings, review_count, phone, website, etc.
- **Example schema:**
```json
{
  "name": "enrich_restaurant_data",
  "description": "Enrich OSM restaurant data with ratings, reviews, and contact info from web sources",
  "input_schema": {
    "type": "object",
    "properties": {
      "restaurants": {
        "type": "array",
        "description": "List of restaurant objects from retrieve_restaurants"
      },
      "priority_fields": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Fields to prioritize: rating, review_count, phone, hours, website, menu_urls",
        "default": ["rating", "review_count"]
      },
      "force_refresh": {
        "type": "boolean",
        "description": "Force refresh even if cached",
        "default": false
      }
    },
    "required": ["restaurants"]
  }
}
```

**Tool 3: interpret_nl_query**
- **Maps to:** NL Query Interpreter Agent
- **Parameters:** query (str), user_location (dict)
- **When to use:** When user provides descriptive query like "cozy vegan brunch"
- **Returns:** Structured filters and boosts for ranking

**Tool 4: find_menu**
- **Maps to:** Menu Finder Agent
- **Parameters:** restaurant_id, restaurant_name, website
- **When to use:** When user asks about menu or allergens
- **Returns:** Menu URLs (text, image, PDF)

**Tool 5: analyze_allergens**
- **Maps to:** Allergen Analyzer Agent
- **Parameters:** restaurant_id, menu_text, cuisine_type
- **When to use:** When user asks about allergens or dietary restrictions
- **Returns:** Allergen probabilities by dish and venue

**Tool 6: enrich_reviews**
- **Maps to:** Review Enricher Agent
- **Parameters:** restaurant_id, restaurant_name, location
- **When to use:** When user wants review details or sentiment
- **Returns:** Review topics, sentiment scores, common praise/complaints

**Tool 7: scrape_images**
- **Maps to:** Image Scraper Agent
- **Parameters:** restaurant_id, restaurant_name, website
- **When to use:** When user requests photos or detail view needs images
- **Returns:** Curated venue images

**Tool 8: rank_results**
- **Maps to:** Ranker Agent
- **Parameters:** restaurants (list), filters (dict), boosts (dict), strategy (str)
- **When to use:** After enrichment, before returning results
- **Returns:** Ranked list with scores and explanations

**Tool 9: qa_check**
- **Maps to:** Safety & QA Agent
- **Parameters:** restaurant_data (dict), scraping_metadata (dict)
- **When to use:** Before returning any enriched data
- **Returns:** Validation result with issues and confidence flags

---

## 4. System Prompt Design

The system prompt for the Planner Agent should instruct Claude to:

### 4.1 Intent Recognition
Teach the agent to classify queries:
- If query contains proximity words ("near", "nearby", "around here") → PROXIMITY_SEARCH
- If query describes ambience, cuisine, features → NL_SEARCH
- If referring to specific restaurant or "this place" → DETAIL_REQUEST
- If asking about allergens, ingredients → ALLERGEN_INQUIRY
- If continuing conversation → FOLLOWUP

### 4.2 Execution Planning
Provide patterns for common scenarios:

**Pattern A: Simple Proximity**
```
User: "restaurants near me"
Plan:
1. retrieve_restaurants(lat, lon, radius=5.0, limit=20)
2. enrich_restaurant_data(restaurants, priority=['rating', 'review_count'])
3. rank_results(restaurants, strategy='distance')
```

**Pattern B: NL Search**
```
User: "cozy vegan brunch with outdoor seating"
Plan:
1. retrieve_restaurants(lat, lon, radius=5.0, limit=50)
2. interpret_nl_query(query, user_location)
3. enrich_restaurant_data(restaurants, priority=['rating', 'review_count', 'hours'])
4. rank_results(restaurants, filters=<from interpret>, strategy='relevance')
```

**Pattern C: Allergen-Focused**
```
User: "italian restaurants with gluten-free options"
Plan:
1. retrieve_restaurants(lat, lon, radius=5.0, limit=30)
2. interpret_nl_query(query) → filters: cuisine=['italian'], dietary=['gluten-free']
3. enrich_restaurant_data(restaurants, priority=['rating', 'menu_urls'])
4. find_menu(top_10_restaurants) [parallel]
5. analyze_allergens(restaurants_with_menus) [parallel]
6. rank_results(restaurants, filters, boosts={'allergen_fit': 0.4}, strategy='hybrid')
7. qa_check(results) → validate allergen confidence
```

**Pattern D: Detail View**
```
User: clicks on restaurant
Plan:
1. enrich_restaurant_data([restaurant], priority=['all'], force_refresh=maybe)
2. Parallel group 1:
   - find_menu(restaurant)
   - enrich_reviews(restaurant)
   - scrape_images(restaurant)
3. analyze_allergens(restaurant) [if menu found]
4. qa_check(restaurant)
```

### 4.3 Error Handling Instructions
Instruct the agent on recovery strategies:
- If retrieve_restaurants fails → return error, cannot proceed
- If enrich_restaurant_data fails → use OSM data only, warn user
- If interpret_nl_query fails → fall back to proximity search
- If find_menu fails → skip allergen analysis, note in response
- If analyze_allergens has low confidence → show warning banner
- If qa_check flags issues → redact problematic data, show what's available

### 4.4 Response Formatting
Guide the agent on output structure:
- Always return JSON with: `{intent, plan_executed, results, warnings, explanation}`
- For lists: include top 10, with distance, rating, allergen badges
- For details: comprehensive view with confidence indicators
- For errors: explain what failed and what data is still available

---

## 5. Helper Functions to Create

### 5.1 Tool Execution Helper
**Function:** `_execute_tool(tool_name: str, params: dict) -> dict`

**Purpose:** Makes API calls to Flask backend or direct agent calls

**Should handle:**
- Making HTTP requests to Flask endpoints
- Handling timeouts and retries
- Standardizing response format
- Logging tool calls for debugging

**Returns:**
```python
{
  "status": "success" | "error",
  "data": dict | None,
  "error": {"code": str, "message": str} | None,
  "execution_time_ms": int
}
```

### 5.2 Parallel Execution Helper
**Function:** `_execute_parallel_group(steps: List[PlanStep]) -> List[dict]`

**Purpose:** Runs multiple steps concurrently

**Should handle:**
- Using asyncio or threading
- Collecting all results
- Handling partial failures (some succeed, some fail)
- Respecting timeouts

**Returns:** List of results in same order as input steps

### 5.3 Context Management Helper
**Function:** `_update_context(context: PlannerContext, results: dict) -> PlannerContext`

**Purpose:** Updates conversation state

**Should handle:**
- Appending to conversation history
- Extracting and storing restaurant IDs from results
- Inferring dietary preferences from queries
- Caching recent results

**Returns:** Updated PlannerContext object

### 5.4 Result Aggregation Helper
**Function:** `_aggregate_results(tool_results: List[dict]) -> dict`

**Purpose:** Combines outputs from multiple agents

**Should handle:**
- Merging restaurant data from different sources
- Resolving conflicts (e.g., different ratings)
- Building final response structure
- Adding metadata (execution time, cache hits, etc.)

**Returns:** Final formatted response

### 5.5 Intent Classification Helper
**Function:** `_classify_intent(query: str, context: PlannerContext) -> UserIntent`

**Purpose:** Determines user intent (can be backup to LLM classification)

**Should use:**
- Keyword matching for simple cases
- Context awareness (if last_restaurant_id exists, might be followup)
- Heuristics (question marks → inquiry, imperatives → action)

**Returns:** UserIntent enum value

---

## 6. Integration Guardrails

### 6.1 Input Validation
Before ANY plan execution:
- ✅ Validate user_location has valid lat/lon (-90 to 90, -180 to 180)
- ✅ Check session_context for required fields
- ✅ Sanitize user query (remove SQL injection, XSS attempts)
- ✅ Verify Letta agent is initialized

### 6.2 Output Contract
Planner MUST always return this structure:
```python
{
  "status": "success" | "partial" | "error",
  "intent": str,  # UserIntent value
  "plan_executed": [str],  # list of tools called
  "results": {
    "restaurants": [...]  # or other data based on intent
  },
  "warnings": [str],  # non-critical issues
  "errors": [{"code": str, "message": str}],  # failures
  "explanation": str,  # human-readable summary
  "metadata": {
    "execution_time_ms": int,
    "agents_called": [str],
    "cache_hits": int,
    "request_id": str
  }
}
```

### 6.3 Agent Communication Protocol
- All tool calls must use standardized parameter names (latitude not lat, etc.)
- All agent responses must include `status` field
- Pass `request_id` through entire chain for tracing
- Include timeout in every tool call
- Use semantic versioning for tool schemas

### 6.4 Error Propagation
- If **critical** tool fails (retrieve_restaurants), abort and return error
- If **optional** tool fails (images), continue but add warning
- Log all errors with full context for debugging
- Never expose internal errors to user, translate to friendly messages
- Example: "Database connection failed" → "We're having trouble loading data right now"

---

## 7. Testing Strategy

Create test cases for:

### 7.1 Intent Classification Tests
```python
# Test cases
"restaurants near me" → PROXIMITY_SEARCH
"vegan thai food" → NL_SEARCH
"does this have peanuts?" → ALLERGEN_INQUIRY (requires context)
"show me photos" → IMAGE_REQUEST (requires context)
"what's good here?" → FOLLOWUP or CHAT
"find me dinner" → CLARIFICATION_NEEDED (missing details)
```

### 7.2 Plan Generation Tests
```python
# Verify correct tool sequence for each intent
PROXIMITY_SEARCH → [retrieve, enrich, rank]
NL_SEARCH → [retrieve, interpret, enrich, rank]
ALLERGEN_INQUIRY → [find_menu, analyze_allergens]
DETAIL_REQUEST → [enrich(eager), parallel(menu,reviews,images), qa]
```

### 7.3 Error Handling Tests
```python
# Simulate failures
- retrieve_restaurants timeout → verify graceful error
- partial enrichment failure → verify partial results returned
- all enrichment failures → verify OSM data still returned
- invalid location → verify validation error
```

### 7.4 Integration Tests
```python
# End-to-end flows
- Complete proximity search with enrichment
- NL search with filtering and ranking
- Allergen analysis with menu finding
- Followup query using cached context
- Error recovery and fallback
```

---

## 8. Performance Considerations

### 8.1 Timeout Management
Set aggressive timeouts:
- retrieve_restaurants: 2s
- enrich_restaurant_data: 5s
- interpret_nl_query: 2s
- find_menu: 10s
- analyze_allergens: 10s
- rank_results: 2s

Total target: <8s for NL search, <3s for proximity

### 8.2 Caching Strategy
Use Redis with these keys:
- `planner:plan:{query_hash}` - cache execution plans (TTL: 1 hour)
- `planner:context:{session_id}` - session context (TTL: 24 hours)
- Check cache before generating new plans for similar queries

### 8.3 Parallel Execution
These agents can run in parallel:
- find_menu + enrich_reviews + scrape_images (for detail views)
- enrich_restaurant_data on batches of restaurants

Sequential dependencies:
- retrieve must complete before enrich
- menu must complete before allergen analysis
- all enrichment before ranking

### 8.4 Lazy Loading
Don't enrich all 50 restaurants:
1. Retrieve 50 candidates
2. Do initial rank by distance (cheap)
3. Enrich only top 15
4. Re-rank with full data
5. Return top 10

---

## 9. Example Conversation Flows

### Flow 1: First-time proximity search
```
User: "restaurants near me"

Planner Analysis:
- Intent: PROXIMITY_SEARCH (contains "near me")
- Context: First query, no history
- Strategy: LAZY enrichment

Execution Plan:
1. retrieve_restaurants(lat=37.8716, lon=-122.2727, radius=5, limit=20)
   → Returns 18 restaurants from OSM
2. enrich_restaurant_data(restaurants, priority=['rating', 'review_count'])
   → Adds ratings for 15/18 (3 failed)
3. rank_results(restaurants, strategy='distance')
   → Sorts by distance

Response:
- Status: success
- Results: Top 10 restaurants with distance, rating, review_count
- Warnings: ["3 restaurants missing ratings"]
- Explanation: "Found 18 restaurants within 5 miles, sorted by distance"
```

### Flow 2: NL search with dietary restriction
```
User: "gluten-free italian near downtown"

Planner Analysis:
- Intent: NL_SEARCH (descriptive preferences)
- Context: First query
- Strategy: SELECTIVE (need menus for allergens)

Execution Plan:
1. retrieve_restaurants(lat, lon, radius=3, limit=30)
   → Returns 28 Italian restaurants
2. interpret_nl_query("gluten-free italian near downtown")
   → Returns: 
      filters={cuisine:['italian'], dietary:['gluten-free']}
      boosts={allergen_fit: 0.4, rating: 0.3, distance: 0.3}
3. enrich_restaurant_data(restaurants, priority=['rating', 'menu_urls'])
   → Adds ratings + menu hints
4. rank_results(restaurants, filters, boosts, strategy='relevance')
   → Pre-ranks by relevance, gets top 10
5. find_menu(top_10) [parallel]
   → Finds menus for 7/10
6. analyze_allergens(7_with_menus) [parallel]
   → Analyzes gluten probability
7. rank_results(enriched, boosts, strategy='hybrid')
   → Final ranking with allergen fit
8. qa_check(results)
   → Flags 2 with low confidence

Response:
- Status: partial
- Results: 10 restaurants ranked by relevance + allergen fit
- Warnings: ["2 restaurants have low-confidence allergen data", "3 restaurants missing menus"]
- Explanation: "Found 10 Italian restaurants with gluten-free info. 2 have unverified allergen data."
```

### Flow 3: Followup question
```
Previous: User saw list of restaurants
User: "what about the third one?"

Planner Analysis:
- Intent: FOLLOWUP (refers to "the third one")
- Context: Retrieved from cached_results[2]
- Strategy: EAGER (detail view)

Execution Plan:
1. Retrieve restaurant_id from context.cached_results[2]
2. enrich_restaurant_data([restaurant], priority=['all'], force=True)
3. Parallel Group 1:
   - find_menu(restaurant) → 2s
   - enrich_reviews(restaurant) → 3s
   - scrape_images(restaurant) → 4s
4. If menu found: analyze_allergens(restaurant) → 3s
5. qa_check(restaurant) → 1s

Response:
- Status: success
- Results: Full restaurant detail with menu, reviews, images, allergens
- Explanation: "Here's everything about [Restaurant Name]"
```

---

## 10. Key Decisions and Trade-offs

### When to Enrich
- **List views:** LAZY (only rating + review_count)
  - Rationale: Fast response, good enough for browsing
- **Detail views:** EAGER (all fields)
  - Rationale: User wants comprehensive info
- **Allergen queries:** SELECTIVE (rating + menus only)
  - Rationale: Menu needed for analysis, other data less critical

### Caching Strategy
- **Enriched data:** 14 days
  - Rationale: Ratings/menus change slowly
- **Execution plans:** 1 hour
  - Rationale: Same queries repeat within sessions
- **Session context:** 24 hours
  - Rationale: User might return same day

### Parallelization
These agents can run concurrently:
- ✅ find_menu + enrich_reviews + scrape_images (independent data sources)
- ✅ enrich_restaurant_data on restaurant batches (I/O bound)

Must be sequential:
- ❌ retrieve → enrich (need base data first)
- ❌ find_menu → analyze_allergens (allergens need menu)
- ❌ enrich → rank (ranking needs enriched data)

---

## 11. Common Pitfalls to Avoid

1. **❌ Don't call tools unnecessarily**
   - If user just wants list, don't scrape images
   - If no allergen mention, don't analyze allergens

2. **❌ Don't block on optional data**
   - Images failing shouldn't stop response
   - Missing menus → show other data, note menu unavailable

3. **❌ Don't lose context**
   - Always pass session_id through entire chain
   - Save restaurant IDs for followup queries
   - Track dietary preferences across conversation

4. **❌ Don't expose raw errors**
   - Transform: "ConnectionTimeout" → "Having trouble reaching that site"
   - Never show stack traces or API keys

5. **❌ Don't skip QA**
   - Always run safety check before returning enriched data
   - Validate allergen confidence meets thresholds
   - Check scraping compliance

6. **❌ Don't assume data exists**
   - Handle missing ratings gracefully
   - Show partial results when some enrichment fails
   - Provide fallback values (rating=None, not rating=0)

7. **❌ Don't over-enrich**
   - For "restaurants near me", don't scrape images for all 50
   - Enrich incrementally: retrieve 50 → rank → enrich top 10

---

## 12. Success Criteria

The Planner Agent is complete when it:
- ✅ Correctly classifies 95%+ of test queries
- ✅ Generates appropriate plans for all 9 intent types
- ✅ Handles at least 3 types of errors gracefully (timeout, API failure, invalid input)
- ✅ Maintains context across 5+ turn conversations
- ✅ Completes proximity searches in <3 seconds
- ✅ Completes NL searches in <8 seconds
- ✅ Returns partial results when enrichment fails
- ✅ Passes all integration tests
- ✅ Logs all tool calls with request_id for debugging
- ✅ Never exposes internal errors to users

---

## 13. Integration Checklist

Before moving to next agent, verify:
- [ ] Planner can call `helpers/restaurant_retrieval.py` successfully
- [ ] Tool schemas match expected input format
- [ ] Output format matches documented contract
- [ ] Error responses include friendly user messages
- [ ] Request IDs propagate through all tool calls
- [ ] Logging captures all decisions and tool executions
- [ ] Tests cover happy path + 3 error scenarios
- [ ] Documentation includes example API calls

---

## 14. Next Steps

Once Planner Agent is implemented:
1. Test with `helpers/restaurant_retrieval.py` alone (no other agents yet)
2. Verify intent classification with 20 test queries
3. Verify plan generation for each intent type
4. Implement error handling for retrieve_restaurants failures
5. Add logging and request tracing

Then proceed to: **Data Enrichment Agent** (the next most critical agent)

---

**Remember:** This is the FOUNDATION agent. All other agents depend on it routing requests correctly. Take time to get this right before building downstream agents.