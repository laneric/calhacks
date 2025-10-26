# PROMPT 3: NL Query Interpreter Agent Implementation Guide

## Context
You are building the **NL Query Interpreter Agent**, which converts natural language queries into structured filters and ranking boosts. This agent enables users to search with phrases like "cozy vegan brunch with outdoor seating" instead of filling out forms.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- LLM: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) for semantic understanding
- Backend: Flask API
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The NL Query Interpreter Agent must:
1. **Parse natural language** - Extract intent from conversational queries
2. **Identify filters** - Detect cuisine, dietary restrictions, ambience, features
3. **Determine boosts** - Calculate ranking weight adjustments
4. **Handle temporal context** - Understand "late night", "brunch", "open now"
5. **Detect distance preferences** - Parse "nearby", "within walking distance"
6. **Provide explanations** - Explain how the query was interpreted
7. **Handle ambiguity** - Request clarification when needed
8. **Learn from context** - Use conversation history to refine interpretation

---

## 2. File Structure

**Create:** `agents/nl_query_interpreter_agent.py`

This file should contain:

### 2.1 Filter Category Enums

**CuisineType Enum:**
Define common cuisine types:
- `ITALIAN`, `CHINESE`, `JAPANESE`, `MEXICAN`, `INDIAN`, `THAI`, `VIETNAMESE`, `KOREAN`, `FRENCH`, `MEDITERRANEAN`, `AMERICAN`, `BURGER`, `PIZZA`, `SEAFOOD`, `STEAKHOUSE`, `BBQ`, `VEGAN`, `VEGETARIAN`, `CAFE`, `BAKERY`, `DESSERT`

**DietaryRestriction Enum:**
Define dietary preferences:
- `VEGAN`, `VEGETARIAN`, `GLUTEN_FREE`, `DAIRY_FREE`, `NUT_FREE`, `KOSHER`, `HALAL`, `KETO`, `PALEO`, `LOW_CARB`

**AmbienceType Enum:**
Define atmosphere preferences:
- `COZY`, `ROMANTIC`, `CASUAL`, `UPSCALE`, `FAMILY_FRIENDLY`, `DATE_NIGHT`, `TRENDY`, `QUIET`, `LIVELY`, `ELEGANT`

**FeatureType Enum:**
Define restaurant features:
- `OUTDOOR_SEATING`, `WIFI`, `PARKING`, `RESERVATIONS`, `DELIVERY`, `TAKEOUT`, `LIVE_MUSIC`, `GOOD_FOR_GROUPS`, `WHEELCHAIR_ACCESSIBLE`, `PET_FRIENDLY`, `BAR`, `HAPPY_HOUR`

**MealType Enum:**
Define meal occasions:
- `BREAKFAST`, `BRUNCH`, `LUNCH`, `DINNER`, `LATE_NIGHT`, `DESSERT`, `DRINKS`, `COFFEE`

**PriceLevel Enum:**
Define price ranges:
- `BUDGET` ($), `MODERATE` ($$), `UPSCALE` ($$$), `FINE_DINING` ($$$$)

### 2.2 Core Classes

**QueryIntent Class:**
Represents parsed user intent. Should include:
- `original_query`: str - Raw user input
- `normalized_query`: str - Cleaned version
- `primary_intent`: str - Main goal (cuisine, ambience, dietary, proximity)
- `confidence`: float - How confident in interpretation (0.0-1.0)

**StructuredFilters Class:**
Hard filters that restaurants must match. Should include:
- `cuisine`: List[str] - Required cuisine types
- `dietary`: List[str] - Required dietary accommodations
- `features`: List[str] - Required features (outdoor seating, etc.)
- `price_level`: Optional[List[str]] - Acceptable price ranges
- `meal_type`: Optional[str] - Meal occasion
- `distance_max_miles`: Optional[float] - Maximum distance
- `open_now`: bool - Must be open currently
- `open_at_time`: Optional[str] - Must be open at specific time

**RankingBoosts Class:**
Soft preferences that adjust ranking scores. Should include:
- `highly_rated`: float - Boost weight for rating >= 4.5 (0.0-1.0)
- `many_reviews`: float - Boost for review_count > threshold
- `exact_cuisine_match`: float - Boost for exact cuisine match vs similar
- `ambience_match`: float - Boost for matching ambience descriptors
- `has_menu_online`: float - Boost for available menu
- `allergen_safe`: float - Boost for dietary restriction safety
- `open_now`: float - Boost if currently open
- `distance_preference`: float - How much to weight proximity

**InterpretationResult Class:**
Complete interpretation output. Should include:
- `intent`: QueryIntent
- `filters`: StructuredFilters
- `boosts`: RankingBoosts
- `explanation`: str - Human-readable interpretation
- `clarifications_needed`: List[str] - Questions to ask user
- `alternative_interpretations`: List[Dict] - Other possible meanings
- `keywords_extracted`: List[str] - Key terms identified
- `context_used`: Dict - Info from conversation history

**NLQueryInterpreterAgent Class:**
Main agent implementation. Should include methods:
- `__init__()` - Initialize Claude client, keyword mappings
- `interpret_query()` - Main entry point
- `_preprocess_query()` - Clean and normalize text
- `_extract_keywords()` - Find relevant terms
- `_classify_intent()` - Determine primary goal
- `_extract_filters()` - Identify hard requirements
- `_calculate_boosts()` - Determine ranking adjustments
- `_generate_explanation()` - Create user-friendly summary
- `_detect_ambiguity()` - Identify unclear intent
- `_use_context()` - Incorporate conversation history

---

## 3. Input/Output Contracts

### 3.1 Input Format (from Planner Agent)
Receives queries in this format:
```python
{
    'query': str,  # "cozy vegan brunch with outdoor seating"
    'user_location': {
        'lat': float,
        'lon': float,
        'city': str  # optional
    },
    'context': {
        'conversation_history': List[Dict],  # previous queries
        'last_restaurant_id': Optional[str],
        'dietary_preferences': Optional[List[str]],  # learned preferences
        'distance_preference_miles': Optional[float]
    },
    'current_time': str,  # ISO timestamp for "open now" queries
    'clarification_mode': bool  # True if asking for clarification
}
```

### 3.2 Output Format (to Planner Agent → Ranker Agent)
Must return interpretation in this format:
```python
{
    'status': 'success' | 'needs_clarification' | 'error',
    
    'intent': {
        'original_query': 'cozy vegan brunch with outdoor seating',
        'normalized_query': 'cozy vegan brunch outdoor seating',
        'primary_intent': 'dietary_ambience_feature',  # combined intent
        'confidence': 0.87
    },
    
    'filters': {
        'cuisine': [],  # empty = no cuisine requirement
        'dietary': ['vegan'],
        'features': ['outdoor_seating'],
        'price_level': None,  # no price mentioned
        'meal_type': 'brunch',
        'distance_max_miles': None,  # no distance mentioned
        'open_now': False,  # not explicitly mentioned
        'open_at_time': None
    },
    
    'boosts': {
        'highly_rated': 0.3,  # standard boost for quality
        'many_reviews': 0.2,
        'exact_cuisine_match': 0.0,  # no cuisine specified
        'ambience_match': 0.4,  # "cozy" is important
        'has_menu_online': 0.2,  # helpful to verify vegan options
        'allergen_safe': 0.5,  # HIGH - dietary restriction is critical
        'open_now': 0.1,  # slight boost if open
        'distance_preference': 0.3  # moderate distance preference
    },
    
    'explanation': 'Looking for vegan-friendly brunch spots with a cozy atmosphere and outdoor seating. I'll prioritize places that can accommodate dietary restrictions.',
    
    'clarifications_needed': [],  # none needed
    
    'alternative_interpretations': [
        {
            'interpretation': 'vegetarian (not vegan) brunch',
            'confidence': 0.15,
            'reason': 'vegan can be confused with vegetarian'
        }
    ],
    
    'keywords_extracted': ['cozy', 'vegan', 'brunch', 'outdoor seating'],
    
    'context_used': {
        'previous_dietary_preference': None,
        'learned_distance_preference': None,
        'time_of_day_inferred': 'morning'  # from "brunch"
    },
    
    'metadata': {
        'processing_time_ms': 450,
        'llm_calls': 1,
        'keyword_matches': 4,
        'ambiguity_score': 0.13  # low = clear query
    }
}
```

### 3.3 Clarification Response Format
When interpretation is ambiguous:
```python
{
    'status': 'needs_clarification',
    'intent': {...},  # partial interpretation
    'filters': {...},  # best guess
    'boosts': {...},  # default weights
    'clarifications_needed': [
        {
            'question': 'Did you mean vegan or vegetarian?',
            'options': ['vegan', 'vegetarian', 'either is fine'],
            'field': 'dietary',
            'importance': 'high'
        },
        {
            'question': 'How far are you willing to travel?',
            'options': ['walking distance (<1 mi)', 'nearby (<3 mi)', 'anywhere in city'],
            'field': 'distance_max_miles',
            'importance': 'medium'
        }
    ],
    'explanation': 'I found vegan brunch spots with outdoor seating, but I have a few questions to refine the results...'
}
```

---

## 4. Claude Haiku Integration

### 4.1 Interpretation Prompt Template

Use Claude Haiku to convert NL queries into structured output:

**System Prompt:**
```
You are a query interpretation assistant for a restaurant recommendation system. Your job is to parse natural language queries into structured filters and ranking boosts.

You must extract:
1. Cuisine preferences (Italian, Chinese, etc.)
2. Dietary restrictions (vegan, gluten-free, etc.)
3. Ambience preferences (cozy, romantic, etc.)
4. Features (outdoor seating, parking, etc.)
5. Meal type (breakfast, brunch, lunch, dinner, late night)
6. Price preferences ($, $$, $$$, $$$$)
7. Distance preferences (nearby, walking distance, etc.)
8. Temporal preferences (open now, open at 8pm, etc.)

Output strict JSON format with filters (hard requirements) and boosts (soft preferences).

Rules:
1. Be conservative with filters - only include explicit requirements
2. Use boosts for implicit preferences
3. Flag ambiguous terms for clarification
4. Consider context from conversation history
5. Explain your interpretation in plain English
```

**User Prompt Template:**
```
Parse this restaurant query:

Query: "{query}"

User Context:
- Location: {city}, {state}
- Time: {current_time}
- Previous queries: {conversation_history}
- Known preferences: {dietary_preferences}

Extract and return JSON:
{
  "primary_intent": string,  // cuisine, dietary, ambience, feature, proximity, or combined
  "confidence": float,  // 0.0-1.0
  
  "filters": {
    "cuisine": [string],  // only if explicitly mentioned
    "dietary": [string],  // vegan, gluten-free, etc.
    "features": [string],  // outdoor_seating, parking, etc.
    "price_level": [string] or null,  // "$", "$$", "$$$", "$$$$"
    "meal_type": string or null,  // breakfast, brunch, lunch, dinner, late_night
    "distance_max_miles": float or null,
    "open_now": bool,
    "open_at_time": string or null  // "20:00" format
  },
  
  "boosts": {
    "highly_rated": float,  // 0.0-1.0, how much to boost high ratings
    "many_reviews": float,
    "exact_cuisine_match": float,
    "ambience_match": float,  // how much "cozy" or "romantic" matters
    "has_menu_online": float,
    "allergen_safe": float,  // high if dietary restrictions present
    "open_now": float,
    "distance_preference": float  // 0.0=anywhere, 1.0=very close only
  },
  
  "explanation": string,  // user-friendly interpretation
  "ambiguous_terms": [string],  // terms that need clarification
  "keywords": [string]  // key terms extracted
}

Examples:

Query: "italian restaurants nearby"
→ primary_intent: "cuisine_proximity"
→ filters: {cuisine: ["italian"], distance_max_miles: 3.0}
→ boosts: {distance_preference: 0.7}

Query: "cozy vegan brunch with outdoor seating"
→ primary_intent: "dietary_ambience_feature"
→ filters: {dietary: ["vegan"], features: ["outdoor_seating"], meal_type: "brunch"}
→ boosts: {ambience_match: 0.5, allergen_safe: 0.6}

Query: "cheap eats open late"
→ primary_intent: "price_temporal"
→ filters: {price_level: ["$"], meal_type: "late_night"}
→ boosts: {open_now: 0.8, distance_preference: 0.4}

Now parse the user's query.
```

### 4.2 Ambiguity Detection Prompt

Use a second Claude call if interpretation confidence < 0.7:

**Prompt Template:**
```
This restaurant query is ambiguous:

Query: "{query}"

Initial interpretation:
{initial_interpretation}

What clarification questions should I ask the user? Consider:
1. Ambiguous terms (vegan vs vegetarian)
2. Missing context (distance, price, time)
3. Multiple possible meanings

Return JSON:
{
  "needs_clarification": bool,
  "questions": [
    {
      "question": string,
      "options": [string],
      "field": string,  // which filter/boost this affects
      "importance": "high" | "medium" | "low"
    }
  ],
  "recommended_default": string  // if user skips clarification
}

Only ask high-importance questions (max 2).
```

---

## 5. Keyword Mapping Strategy

### 5.1 Cuisine Keywords Dictionary

Create mappings from natural language to standardized cuisine types:

```python
CUISINE_KEYWORDS = {
    'italian': ['italian', 'pasta', 'pizza', 'trattoria', 'osteria'],
    'chinese': ['chinese', 'dim sum', 'szechuan', 'cantonese', 'mandarin'],
    'japanese': ['japanese', 'sushi', 'ramen', 'izakaya', 'yakitori'],
    'mexican': ['mexican', 'taco', 'burrito', 'taqueria', 'mexican food'],
    'indian': ['indian', 'curry', 'tandoori', 'biryani', 'dosa'],
    'thai': ['thai', 'pad thai', 'tom yum', 'thai food'],
    'vietnamese': ['vietnamese', 'pho', 'banh mi', 'vietnamese food'],
    'american': ['american', 'diner', 'comfort food'],
    'burger': ['burger', 'burgers', 'hamburger'],
    'pizza': ['pizza', 'pizzeria', 'pie'],
    'vegan': ['vegan', 'plant-based', 'vegan restaurant'],
    'vegetarian': ['vegetarian', 'veggie'],
    # ... more mappings
}
```

### 5.2 Dietary Keywords Dictionary

```python
DIETARY_KEYWORDS = {
    'vegan': ['vegan', 'plant-based', 'no animal products'],
    'vegetarian': ['vegetarian', 'veggie', 'no meat'],
    'gluten_free': ['gluten free', 'gluten-free', 'gf', 'celiac', 'no gluten'],
    'dairy_free': ['dairy free', 'dairy-free', 'no dairy', 'lactose free'],
    'nut_free': ['nut free', 'nut-free', 'no nuts', 'nut allergy'],
    'kosher': ['kosher', 'kosher food'],
    'halal': ['halal', 'halal food'],
    'keto': ['keto', 'ketogenic', 'low carb'],
    # ... more mappings
}
```

### 5.3 Ambience Keywords Dictionary

```python
AMBIENCE_KEYWORDS = {
    'cozy': ['cozy', 'intimate', 'warm', 'homey', 'comfortable'],
    'romantic': ['romantic', 'date night', 'couples', 'candlelit'],
    'casual': ['casual', 'laid back', 'relaxed', 'informal'],
    'upscale': ['upscale', 'fancy', 'fine dining', 'elegant', 'sophisticated'],
    'family_friendly': ['family friendly', 'kids friendly', 'good for families', 'family restaurant'],
    'trendy': ['trendy', 'hip', 'modern', 'popular'],
    'quiet': ['quiet', 'peaceful', 'calm'],
    'lively': ['lively', 'energetic', 'vibrant', 'bustling'],
    # ... more mappings
}
```

### 5.4 Feature Keywords Dictionary

```python
FEATURE_KEYWORDS = {
    'outdoor_seating': ['outdoor seating', 'patio', 'outdoor dining', 'terrace', 'sidewalk seating', 'alfresco'],
    'parking': ['parking', 'parking lot', 'free parking', 'valet'],
    'wifi': ['wifi', 'wi-fi', 'internet'],
    'reservations': ['reservations', 'book ahead', 'reserve'],
    'delivery': ['delivery', 'delivers'],
    'takeout': ['takeout', 'take out', 'to go', 'carry out'],
    'live_music': ['live music', 'music', 'entertainment'],
    'bar': ['bar', 'drinks', 'cocktails', 'happy hour'],
    # ... more mappings
}
```

### 5.5 Distance Keywords Dictionary

```python
DISTANCE_KEYWORDS = {
    0.5: ['walking distance', 'very close', 'right here'],
    1.0: ['nearby', 'close', 'near me'],
    3.0: ['around here', 'in the area'],
    5.0: ['not too far', 'within driving distance'],
    None: ['anywhere', 'don\'t care about distance']  # no distance filter
}
```

### 5.6 Temporal Keywords Dictionary

```python
TEMPORAL_KEYWORDS = {
    'open_now': ['open now', 'open right now', 'currently open'],
    'breakfast': ['breakfast', 'morning', 'am'],
    'brunch': ['brunch', 'late morning'],
    'lunch': ['lunch', 'midday', 'noon'],
    'dinner': ['dinner', 'evening', 'supper'],
    'late_night': ['late night', 'open late', 'late', 'after midnight']
}
```

---

## 6. Helper Functions to Create

### 6.1 Query Preprocessing Helper
**Function:** `_preprocess_query(query: str) -> str`

**Purpose:** Clean and normalize query text

**Should handle:**
- Convert to lowercase
- Remove punctuation (except meaningful ones like $)
- Handle common misspellings
- Expand contractions ("can't" → "cannot")
- Remove filler words ("um", "uh", "like")
- Normalize whitespace

**Returns:** Cleaned query string

**Example:**
```
Input: "  Umm, I'm looking for some really COZY vegan places... "
Output: "looking for cozy vegan places"
```

### 6.2 Keyword Extraction Helper
**Function:** `_extract_keywords(query: str, keyword_dicts: List[Dict]) -> Dict`

**Purpose:** Find relevant keywords from dictionaries

**Should handle:**
- Match multi-word phrases first ("gluten free" before "free")
- Handle variations ("italian" matches "italiana")
- Track which category each keyword belongs to
- Calculate match confidence

**Returns:**
```python
{
    'cuisine': [('italian', 0.95)],
    'dietary': [('vegan', 0.98)],
    'ambience': [('cozy', 0.92)],
    'features': [('outdoor_seating', 0.88)],
    'unmatched': ['some', 'other', 'words']
}
```

### 6.3 Intent Classification Helper
**Function:** `_classify_intent(keywords: Dict, query: str) -> str`

**Purpose:** Determine primary intent from extracted keywords

**Strategy:**
```
If cuisine keywords present: "cuisine" or "cuisine_X"
If dietary keywords present: "dietary" or "dietary_X"
If ambience keywords: "ambience" or "ambience_X"
If feature keywords: "feature" or "feature_X"
If distance words: "proximity"
If multiple categories: "combined" (e.g., "dietary_ambience_feature")
If none: "general" or "clarification_needed"
```

**Returns:** Intent string and confidence score

### 6.4 Filter Extraction Helper
**Function:** `_extract_filters(keywords: Dict, context: Dict) -> StructuredFilters`

**Purpose:** Build hard filter requirements

**Rules:**
- Only include as filters if explicitly stated
- Use "must have", "need", "require" as signals
- Be conservative - prefer boosts over filters

**Example Logic:**
```
"vegan brunch" → filters: {dietary: ['vegan'], meal_type: 'brunch'}
"italian or chinese" → filters: {cuisine: ['italian', 'chinese']}  # OR logic
"cozy italian" → filters: {cuisine: ['italian']}, boosts: {ambience_match: 0.5}  # cozy is preference, not requirement
```

### 6.5 Boost Calculation Helper
**Function:** `_calculate_boosts(keywords: Dict, filters: StructuredFilters) -> RankingBoosts`

**Purpose:** Assign ranking boost weights

**Strategy:**
```
Base boosts:
- highly_rated: 0.3 (always value quality)
- many_reviews: 0.2 (more data = more reliable)

Adjust based on query:
- If dietary restrictions: allergen_safe = 0.5-0.7 (high priority)
- If ambience mentioned: ambience_match = 0.4-0.6
- If "nearby" or distance: distance_preference = 0.6-0.8
- If "open now": open_now = 0.7-0.9
- If cuisine specified: exact_cuisine_match = 0.4
```

**Returns:** RankingBoosts object with calculated weights

### 6.6 Distance Parser Helper
**Function:** `_parse_distance_preference(query: str) -> Optional[float]`

**Purpose:** Extract distance limit from natural language

**Should handle:**
```
"walking distance" → 0.5 miles
"nearby" → 1.0 miles
"close" → 1.0 miles
"around here" → 3.0 miles
"within 2 miles" → 2.0 miles
"not too far" → 5.0 miles
no mention → None (no limit)
```

**Returns:** Distance in miles or None

### 6.7 Temporal Parser Helper
**Function:** `_parse_temporal_context(query: str, current_time: str) -> Dict`

**Purpose:** Extract time-related preferences

**Should detect:**
```
"open now" → {open_now: True}
"late night" → {meal_type: 'late_night', open_at_time: '23:00'}
"brunch" → {meal_type: 'brunch', open_at_time: '10:00'}
"dinner at 8pm" → {meal_type: 'dinner', open_at_time: '20:00'}
```

**Returns:**
```python
{
    'open_now': bool,
    'open_at_time': Optional[str],  # "HH:MM" format
    'meal_type': Optional[str]
}
```

### 6.8 Explanation Generator Helper
**Function:** `_generate_explanation(filters: StructuredFilters, boosts: RankingBoosts) -> str`

**Purpose:** Create human-readable interpretation

**Template:**
```
"Looking for {meal_type} {cuisine} restaurants {dietary_note} {distance_note}. 
I'll prioritize {top_3_boost_factors}."

Examples:
"Looking for vegan brunch spots with outdoor seating. I'll prioritize places with good ratings and dietary-safe options."

"Looking for Italian restaurants nearby. I'll prioritize highly-rated places that are close to you."

"Looking for budget-friendly late-night options. I'll prioritize places that are currently open."
```

### 6.9 Ambiguity Detector Helper
**Function:** `_detect_ambiguity(interpretation: Dict) -> List[Dict]`

**Purpose:** Identify unclear aspects that need clarification

**Should flag:**
- Confidence < 0.7
- Multiple possible cuisines ("asian" → Chinese, Japanese, Thai?)
- Vague dietary terms ("healthy" → vegan, vegetarian, low-cal?)
- Unclear distance ("nearby" without context)
- Conflicting signals ("cheap" + "fine dining")

**Returns:** List of clarification questions

### 6.10 Context Integration Helper
**Function:** `_use_context(interpretation: Dict, context: Dict) -> Dict`

**Purpose:** Enhance interpretation with conversation history

**Should:**
- Fill in missing dietary preferences from history
- Infer distance preference from past queries
- Remember previous cuisine preferences
- Track time-of-day patterns

**Example:**
```
Current query: "find me something"
Previous query: "italian restaurants"
Context: User prefers vegan
→ Interpret as: "vegan italian restaurants nearby"
```

---

## 7. Integration Guardrails

### 7.1 Input Validation
Before interpretation:
- ✅ Validate query is non-empty string
- ✅ Check query length (min: 3 chars, max: 500 chars)
- ✅ Validate user_location has lat/lon
- ✅ Validate current_time is valid ISO timestamp
- ✅ Sanitize query (remove SQL injection attempts, XSS)

### 7.2 Output Contract Compliance
MUST return exact format expected by Planner/Ranker:
- ✅ `status` is one of: 'success', 'needs_clarification', 'error'
- ✅ `filters` object has all required keys (even if null/empty)
- ✅ `boosts` object has all boost fields (0.0-1.0 range)
- ✅ `explanation` is human-readable string
- ✅ All distance values in miles (not km)
- ✅ All time values in "HH:MM" 24-hour format

### 7.3 Filter vs Boost Decision Rules
```
Use FILTERS (hard requirements) when:
- User says "must", "need", "require", "only"
- Dietary restrictions mentioned (safety critical)
- Explicit negatives ("no meat", "not spicy")

Use BOOSTS (soft preferences) when:
- User says "prefer", "like", "want", "looking for"
- Ambience descriptors ("cozy", "romantic")
- General quality signals ("good", "best")
- No explicit requirement language
```

### 7.4 Confidence Scoring
Assign confidence based on:
```
HIGH (0.8-1.0):
- Clear, specific query
- Well-known keywords matched
- No ambiguous terms
- Single clear intent

MEDIUM (0.6-0.79):
- Some ambiguity
- Multiple possible intents
- Vague terms used
- Missing context

LOW (0.0-0.59):
- Very ambiguous
- Unknown terms
- Conflicting signals
- Requires clarification
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test: Cuisine Extraction**
```
Query: "italian restaurants"
Expected: filters.cuisine = ['italian'], confidence > 0.9

Query: "italian or chinese"
Expected: filters.cuisine = ['italian', 'chinese']

Query: "asian food"
Expected: clarifications_needed (ambiguous - which asian?)
```

**Test: Dietary Extraction**
```
Query: "vegan brunch"
Expected: filters.dietary = ['vegan'], filters.meal_type = 'brunch'

Query: "gluten-free italian"
Expected: filters.dietary = ['gluten_free'], filters.cuisine = ['italian']

Query: "healthy options"
Expected: boosts.highly_rated += 0.2, clarification about "healthy"
```

**Test: Ambience Extraction**
```
Query: "cozy romantic dinner"
Expected: 
  filters.meal_type = 'dinner'
  boosts.ambience_match = 0.5-0.6
  keywords = ['cozy', 'romantic']
```

**Test: Feature Extraction**
```
Query: "outdoor seating"
Expected: filters.features = ['outdoor_seating']

Query: "with parking and wifi"
Expected: filters.features = ['parking', 'wifi']
```

**Test: Distance Parsing**
```
Query: "nearby italian"
Expected: filters.distance_max_miles = 1.0

Query: "walking distance"
Expected: filters.distance_max_miles = 0.5

Query: "italian restaurants"  # no distance mention
Expected: filters.distance_max_miles = None, boosts.distance_preference = 0.3
```

**Test: Temporal Parsing**
```
Query: "open now"
Expected: filters.open_now = True

Query: "late night pizza"
Expected: filters.meal_type = 'late_night', filters.cuisine = ['pizza']

Query: "brunch tomorrow"
Expected: filters.meal_type = 'brunch', clarification about specific time
```

### 8.2 Integration Tests

**Test: End-to-End Interpretation**
```
Query: "cozy vegan brunch with outdoor seating"
Expected output matches contract exactly
Verify: filters, boosts, explanation all populated
```

**Test: Context Integration**
```
First query: "italian restaurants"
Second query: "show me more"
Expected: Remembers cuisine = 'italian' from context
```

**Test: Ambiguity Handling**
```
Query: "good food"  # extremely vague
Expected: status = 'needs_clarification'
Expected: At least 1 clarification question
```

**Test: Multi-Constraint Query**
```
Query: "cheap vegan italian near me open now"
Expected:
  filters.cuisine = ['italian']
  filters.dietary = ['vegan']
  filters.price_level = ['$']
  filters.distance_max_miles = 1.0
  filters.open_now = True
```

### 8.3 Edge Case Tests

**Test: Conflicting Signals**
```
Query: "cheap fine dining"  # contradiction
Expected: clarification or default to one interpretation
```

**Test: Unknown Terms**
```
Query: "fleebengibbet restaurant"  # nonsense word
Expected: Ignore unknown term, interpret rest of query
```

**Test: Extremely Long Query**
```
Query: 500+ character rambling query
Expected: Extract key intent, ignore filler
```

**Test: Non-English Query**
```
Query: "restaurante italiano"  # Spanish
Expected: Detect "italiano", interpret as Italian cuisine
Or: Request clarification
```

---

## 9. Example Interpretation Flows

### Example 1: Simple Cuisine Query
```
Input:
{
  'query': 'italian restaurants',
  'user_location': {'lat': 37.7749, 'lon': -122.4194},
  'context': {},
  'current_time': '2025-10-26T18:00:00Z'
}

Processing:
1. Preprocess: "italian restaurants" (already clean)
2. Extract keywords: cuisine=['italian']
3. Classify intent: "cuisine" (confidence: 0.95)
4. Extract filters: {cuisine: ['italian']}
5. Calculate boosts: default boosts
6. Generate explanation: "Looking for Italian restaurants"

Output:
{
  'status': 'success',
  'intent': {
    'primary_intent': 'cuisine',
    'confidence': 0.95
  },
  'filters': {
    'cuisine': ['italian'],
    'dietary': [],
    'features': [],
    'price_level': None,
    'meal_type': None,
    'distance_max_miles': None,
    'open_now': False
  },
  'boosts': {
    'highly_rated': 0.3,
    'many_reviews': 0.2,
    'exact_cuisine_match': 0.4,
    'ambience_match': 0.0,
    'has_menu_online': 0.1,
    'allergen_safe': 0.0,
    'open_now': 0.0,
    'distance_preference': 0.3
  },
  'explanation': 'Looking for Italian restaurants. I'll prioritize highly-rated places.',
  'keywords_extracted': ['italian']
}
```

### Example 2: Complex Multi-Constraint Query
```
Input:
{
  'query': 'cozy vegan brunch with outdoor seating',
  'user_location': {'lat': 37.7749, 'lon': -122.4194},
  'context': {},
  'current_time': '2025-10-26T10:30:00Z'
}

Processing:
1. Preprocess: "cozy vegan brunch outdoor seating"
2. Extract keywords:
   - ambience: ['cozy']
   - dietary: ['vegan']
   - meal_type: ['brunch']
   - features: ['outdoor_seating']
3. Classify intent: "dietary_ambience_feature" (confidence: 0.87)
4. Extract filters:
   - dietary: ['vegan'] (hard requirement)
   - features: ['outdoor_seating'] (explicit "with")
   - meal_type: 'brunch'
5. Calculate boosts:
   - ambience_match: 0.5 (cozy is preference)
   - allergen_safe: 0.6 (vegan = dietary restriction)
   - has_menu_online: 0.3 (helpful to verify vegan options)
6. Generate explanation

Output:
{
  'status': 'success',
  'intent': {
    'primary_intent': 'dietary_ambience_feature',
    'confidence': 0.87
  },
  'filters': {
    'cuisine': [],
    'dietary': ['vegan'],
    'features': ['outdoor_seating'],
    'price_level': None,
    'meal_type': 'brunch',
    'distance_max_miles': None,
    'open_now': False
  },
  'boosts': {
    'highly_rated': 0.3,
    'many_reviews': 0.2,
    'exact_cuisine_match': 0.0,
    'ambience_match': 0.5,
    'has_menu_online': 0.3,
    'allergen_safe': 0.6,
    'open_now': 0.1,
    'distance_preference': 0.3
  },
  'explanation': 'Looking for vegan-friendly brunch spots with a cozy atmosphere and outdoor seating. I'll prioritize places that can accommodate dietary restrictions safely.',
  'keywords_extracted': ['cozy', 'vegan', 'brunch', 'outdoor seating']
}
```

### Example 3: Ambiguous Query Requiring Clarification
```
Input:
{
  'query': 'good food near me',
  'user_location': {'lat': 37.7749, 'lon': -122.4194},
  'context': {}
}

Processing:
1. Preprocess: "good food near me"
2. Extract keywords:
   - distance: ['near me'] → 1.0 miles
   - quality: ['good'] → boost highly_rated
3. Classify intent: "general" (confidence: 0.45 - too vague)
4. Detect ambiguity: No cuisine, no dietary, no meal type
5. Generate clarification questions

Output:
{
  'status': 'needs_clarification',
  'intent': {
    'primary_intent': 'general',
    'confidence': 0.45
  },
  'filters': {
    'cuisine': [],
    'dietary': [],
    'features': [],
    'price_level': None,
    'meal_type': None,
    'distance_max_miles': 1.0,
    'open_now': False
  },
  'boosts': {
    'highly_rated': 0.5,
    'many_reviews': 0.3,
    'distance_preference': 0.7,
    ...
  },
  'explanation': 'Looking for good restaurants nearby, but I need more details to give you the best recommendations.',
  'clarifications_needed': [
    {
      'question': 'What type of food are you in the mood for?',
      'options': ['Italian', 'Chinese', 'Mexican', 'American', 'Other'],
      'field': 'cuisine',
      'importance': 'high'
    },
    {
      'question': 'What meal are you looking for?',
      'options': ['Breakfast', 'Lunch', 'Dinner', 'Snack/Dessert'],
      'field': 'meal_type',
      'importance': 'medium'
    }
  ]
}
```

### Example 4: Context-Aware Followup
```
Previous Query: "vegan italian restaurants"
Current Input:
{
  'query': 'show me more',
  'context': {
    'conversation_history': [
      {'query': 'vegan italian restaurants', 'filters': {...}}
    ],
    'dietary_preferences': ['vegan']
  }
}

Processing:
1. Detect followup intent
2. Retrieve previous filters from context
3. Apply same filters with slight variation (different boost weights or expanded radius)

Output:
{
  'status': 'success',
  'intent': {
    'primary_intent': 'followup',
    'confidence': 0.95
  },
  'filters': {
    'cuisine': ['italian'],  # from context
    'dietary': ['vegan'],  # from context
    'distance_max_miles': 5.0  # expanded from previous 3.0
  },
  'boosts': {...},
  'explanation': 'Showing more vegan Italian restaurants, expanding the search radius.',
  'context_used': {
    'previous_cuisine': 'italian',
    'previous_dietary': 'vegan',
    'expanded_radius': True
  }
}
```

---

## 10. Common Pitfalls to Avoid

1. **❌ Don't over-filter**
   - "cozy italian" → cuisine filter + ambience boost (NOT ambience filter)
   - Reserve filters for explicit requirements only

2. **❌ Don't ignore context**
   - User says "show me more" → use conversation history
   - User has known dietary preferences → apply automatically

3. **❌ Don't hallucinate requirements**
   - If query doesn't mention price, don't add price filter
   - Be conservative, not creative

4. **❌ Don't confuse similar terms**
   - "vegan" ≠ "vegetarian"
   - "gluten-free" ≠ "low-carb"
   - Always clarify if uncertain

5. **❌ Don't ignore temporal context**
   - "brunch" query at 3pm → might mean "brunch-style food" not actual brunch time
   - Check current_time when interpreting meal types

6. **❌ Don't set unrealistic boosts**
   - Sum of boost weights doesn't need to equal 1.0
   - Each boost is independent, just keep in 0.0-1.0 range

7. **❌ Don't skip explanation**
   - Always provide human-readable interpretation
   - Users need to understand what you searched for

8. **❌ Don't assume distance units**
   - Always use miles internally (US-centric for now)
   - Document if adding km support

9. **❌ Don't ignore conflicting signals**
   - "cheap fine dining" → flag as ambiguous
   - "healthy burger" → might be valid (turkey burger, veggie burger)

10. **❌ Don't forget confidence scores**
    - Low confidence → trigger clarification
    - High confidence → proceed with interpretation

---

## 11. Success Criteria

The NL Query Interpreter Agent is complete when it:
- ✅ Correctly interprets 90%+ of test queries
- ✅ Assigns appropriate filters vs boosts (conservative filtering)
- ✅ Calculates confidence scores accurately
- ✅ Detects ambiguity and requests clarification when needed
- ✅ Generates clear, accurate explanations
- ✅ Integrates conversation context effectively
- ✅ Completes interpretation in <500ms
- ✅ Returns output in exact contract format
- ✅ Handles edge cases gracefully (long queries, typos, unknown terms)
- ✅ Passes all unit and integration tests

---

## 12. Integration Checklist

Before marking complete, verify:
- [ ] Agent receives queries from Planner in correct format
- [ ] Claude Haiku integration works reliably
- [ ] Keyword dictionaries are comprehensive
- [ ] Output format matches Ranker expectations exactly
- [ ] Filter vs boost logic is conservative
- [ ] Confidence scoring is calibrated
- [ ] Clarification flow works end-to-end
- [ ] Context integration uses conversation history
- [ ] Explanation generation is clear and accurate
- [ ] All edge cases handled gracefully
- [ ] Tests cover 20+ diverse query types

---

## 13. Next Steps

Once NL Query Interpreter Agent is complete:
1. Test with 50 diverse real-world queries
2. Measure interpretation accuracy
3. Calibrate confidence thresholds
4. Refine keyword dictionaries based on misses
5. Test integration with Planner and Ranker agents

Then proceed to: **Ranker Agent** (uses filters and boosts to rank restaurants)

---

**Remember:** This agent is the KEY to great UX. Users will judge the entire system by whether it "understands" their queries. Prioritize accuracy and clarity over speed. A clear clarification is better than a wrong guess.