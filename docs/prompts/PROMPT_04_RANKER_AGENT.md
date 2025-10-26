# PROMPT 4: Ranker Agent Implementation Guide

## Context
You are building the **Ranker Agent**, which takes enriched restaurant data and user preferences (filters + boosts) and produces a ranked list of results with scores and explanations. This is the final step before presenting results to the user.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- LLM: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) for ranking explanations
- Backend: Flask API
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The Ranker Agent must:
1. **Apply hard filters** - Remove restaurants that don't meet requirements
2. **Calculate component scores** - Distance, rating, review count, allergen fit, etc.
3. **Apply boost weights** - Adjust scores based on user preferences
4. **Normalize scores** - Ensure fair comparison across different scales
5. **Combine scores** - Weighted sum to produce final ranking
6. **Sort results** - Order by final score descending
7. **Generate explanations** - Explain why each restaurant was ranked
8. **Handle edge cases** - Missing data, ties, low confidence
9. **Support multiple strategies** - Distance-focused, rating-focused, relevance-focused, hybrid

---

## 2. File Structure

**Create:** `agents/ranker_agent.py`

This file should contain:

### 2.1 Ranking Strategy Enum
Define different ranking approaches:
- `DISTANCE` - Prioritize proximity (70% distance, 20% rating, 10% reviews)
- `RATING` - Prioritize quality (60% rating, 30% reviews, 10% distance)
- `RELEVANCE` - Prioritize NL query match (50% relevance, 25% rating, 25% distance)
- `HYBRID` - Balanced approach (25% each: distance, rating, relevance, reviews + 10% allergen fit)
- `ALLERGEN_SAFE` - For dietary queries (40% allergen fit, 30% rating, 20% distance, 10% reviews)

### 2.2 Score Component Enum
Define individual score components:
- `DISTANCE_SCORE` - Proximity to user
- `RATING_SCORE` - Restaurant rating
- `REVIEW_COUNT_SCORE` - Number of reviews (confidence proxy)
- `NL_RELEVANCE_SCORE` - Match to natural language query
- `ALLERGEN_FIT_SCORE` - Safety for dietary restrictions
- `HOURS_MATCH_SCORE` - Open now or at requested time
- `AMBIENCE_SCORE` - Match to ambience preferences
- `PRICE_MATCH_SCORE` - Match to price preferences

### 2.3 Core Classes

**RankingRequest Class:**
Represents a ranking job. Should include:
- `restaurants`: List[Dict] - Enriched restaurant objects
- `filters`: StructuredFilters - Hard requirements from NL Interpreter
- `boosts`: RankingBoosts - Soft preferences from NL Interpreter
- `strategy`: RankingStrategy - Which ranking approach to use
- `user_location`: Dict - User's lat/lon for distance calculations
- `current_time`: str - For "open now" calculations
- `limit`: int - Max results to return (default: 10)

**ScoreBreakdown Class:**
Individual score components for one restaurant. Should include:
- `restaurant_id`: str
- `distance_score`: float - Normalized distance score (0.0-1.0)
- `rating_score`: float - Normalized rating score (0.0-1.0)
- `review_count_score`: float - Normalized review count score (0.0-1.0)
- `nl_relevance_score`: float - NL match score (0.0-1.0)
- `allergen_fit_score`: float - Dietary safety score (0.0-1.0)
- `hours_match_score`: float - Temporal match score (0.0-1.0)
- `ambience_score`: float - Ambience match score (0.0-1.0)
- `price_match_score`: float - Price match score (0.0-1.0)
- `final_score`: float - Weighted combination
- `raw_values`: Dict - Original values before normalization

**RankedRestaurant Class:**
A restaurant with ranking info. Should include:
- `restaurant`: Dict - Full enriched restaurant object
- `rank`: int - Position in results (1-indexed)
- `score`: float - Final score
- `score_breakdown`: ScoreBreakdown - Individual components
- `explanation`: str - Why this ranking
- `match_reasons`: List[str] - Specific match highlights
- `warnings`: List[str] - Any concerns (low confidence, missing data)

**RankingResult Class:**
Complete ranking output. Should include:
- `ranked_results`: List[RankedRestaurant] - Top N results
- `ranking_strategy`: str - Strategy used
- `filters_applied`: Dict - Which filters were applied
- `total_candidates`: int - Restaurants before filtering
- `total_after_filter`: int - Restaurants after filtering
- `total_returned`: int - Final results returned
- `metadata`: Dict - Statistics, timing, etc.

**RankerAgent Class:**
Main agent implementation. Should include methods:
- `__init__()` - Initialize Claude client, scoring functions
- `rank_restaurants()` - Main entry point
- `_apply_filters()` - Remove non-matching restaurants
- `_calculate_component_scores()` - Calculate individual scores
- `_normalize_scores()` - Normalize to 0-1 range
- `_apply_boost_weights()` - Weight scores by user preferences
- `_combine_scores()` - Produce final score
- `_sort_and_rank()` - Order by score
- `_generate_explanations()` - Explain rankings
- `_handle_ties()` - Break score ties
- `_handle_missing_data()` - Deal with incomplete enrichment

---

## 3. Input/Output Contracts

### 3.1 Input Format (from Planner Agent)
Receives ranking requests in this format:
```python
{
    'restaurants': [
        {
            'id': 'rest_123',
            'name': 'Super Duper Burger',
            'distance_meters': 644,
            'rating': 4.3,
            'review_count': 1542,
            'cuisine': 'burger',
            'price_level': '$$',
            'hours': {...},
            'allergen_summary': {'gluten': 0.91, 'dairy': 0.76, ...},
            'sources': [...],
            'enrichment_metadata': {...}
        },
        # ... more restaurants
    ],
    'filters': {
        'cuisine': ['italian'],
        'dietary': ['vegan'],
        'features': ['outdoor_seating'],
        'price_level': ['$', '$$'],
        'meal_type': 'brunch',
        'distance_max_miles': 3.0,
        'open_now': True
    },
    'boosts': {
        'highly_rated': 0.3,
        'many_reviews': 0.2,
        'exact_cuisine_match': 0.4,
        'ambience_match': 0.5,
        'has_menu_online': 0.2,
        'allergen_safe': 0.6,
        'open_now': 0.7,
        'distance_preference': 0.4
    },
    'strategy': 'hybrid',
    'user_location': {'lat': 37.7749, 'lon': -122.4194},
    'current_time': '2025-10-26T18:00:00Z',
    'limit': 10
}
```

### 3.2 Output Format (to Planner Agent → Frontend)
Must return ranked results in this format:
```python
{
    'status': 'success' | 'partial' | 'error',
    
    'ranked_results': [
        {
            'restaurant': {
                # Full enriched restaurant object
                'id': 'rest_123',
                'name': 'Plant Cafe',
                'rating': 4.6,
                'distance_meters': 820,
                ...
            },
            'rank': 1,
            'score': 0.87,
            'score_breakdown': {
                'distance_score': 0.85,
                'rating_score': 0.92,
                'review_count_score': 0.78,
                'nl_relevance_score': 0.95,
                'allergen_fit_score': 0.98,
                'hours_match_score': 1.0,
                'ambience_score': 0.88,
                'price_match_score': 0.75,
                'final_score': 0.87,
                'raw_values': {
                    'distance_miles': 0.51,
                    'rating': 4.6,
                    'review_count': 892,
                    ...
                }
            },
            'explanation': 'Top choice because it perfectly matches your vegan requirements, has excellent ratings (4.6 stars), and is currently open with a cozy atmosphere.',
            'match_reasons': [
                'Vegan-friendly (98% confidence)',
                'Highly rated (4.6/5)',
                'Currently open',
                'Cozy atmosphere mentioned in reviews'
            ],
            'warnings': []
        },
        # ... more results
    ],
    
    'ranking_strategy': 'hybrid',
    'filters_applied': {
        'cuisine': ['italian'],
        'dietary': ['vegan'],
        'removed_count': 42  # restaurants filtered out
    },
    'total_candidates': 50,
    'total_after_filter': 8,
    'total_returned': 8,
    
    'metadata': {
        'execution_time_ms': 125,
        'scoring_method': 'weighted_sum',
        'normalization': 'min_max',
        'ties_broken': 0,
        'missing_data_count': 2,
        'average_confidence': 0.82
    }
}
```

---

## 4. Ranking Strategies

### 4.1 Strategy Weight Configurations

Define weight distributions for each strategy:

**DISTANCE Strategy:**
```python
DISTANCE_WEIGHTS = {
    'distance_score': 0.70,
    'rating_score': 0.20,
    'review_count_score': 0.10,
    'nl_relevance_score': 0.0,
    'allergen_fit_score': 0.0,
    'hours_match_score': 0.0,
    'ambience_score': 0.0,
    'price_match_score': 0.0
}
# Use when: User says "nearby", "close", "walking distance"
```

**RATING Strategy:**
```python
RATING_WEIGHTS = {
    'distance_score': 0.10,
    'rating_score': 0.60,
    'review_count_score': 0.30,
    'nl_relevance_score': 0.0,
    'allergen_fit_score': 0.0,
    'hours_match_score': 0.0,
    'ambience_score': 0.0,
    'price_match_score': 0.0
}
# Use when: User says "best", "top rated", "highest rated"
```

**RELEVANCE Strategy:**
```python
RELEVANCE_WEIGHTS = {
    'distance_score': 0.15,
    'rating_score': 0.20,
    'review_count_score': 0.10,
    'nl_relevance_score': 0.50,
    'allergen_fit_score': 0.0,
    'hours_match_score': 0.0,
    'ambience_score': 0.05,
    'price_match_score': 0.0
}
# Use when: NL query has many specific preferences
```

**HYBRID Strategy (default):**
```python
HYBRID_WEIGHTS = {
    'distance_score': 0.25,
    'rating_score': 0.25,
    'review_count_score': 0.15,
    'nl_relevance_score': 0.20,
    'allergen_fit_score': 0.10,
    'hours_match_score': 0.05,
    'ambience_score': 0.0,  # included in nl_relevance
    'price_match_score': 0.0  # included in nl_relevance
}
# Use when: Balanced query with no dominant preference
```

**ALLERGEN_SAFE Strategy:**
```python
ALLERGEN_SAFE_WEIGHTS = {
    'distance_score': 0.20,
    'rating_score': 0.25,
    'review_count_score': 0.10,
    'nl_relevance_score': 0.05,
    'allergen_fit_score': 0.40,
    'hours_match_score': 0.0,
    'ambience_score': 0.0,
    'price_match_score': 0.0
}
# Use when: Dietary restrictions mentioned (vegan, gluten-free, etc.)
```

### 4.2 Dynamic Weight Adjustment

Adjust base weights using boost values from NL Interpreter:

```python
# Example adjustment logic
final_weights = base_weights.copy()

# If user emphasizes distance
if boosts['distance_preference'] > 0.5:
    final_weights['distance_score'] *= (1 + boosts['distance_preference'])

# If user emphasizes allergen safety
if boosts['allergen_safe'] > 0.5:
    final_weights['allergen_fit_score'] *= (1 + boosts['allergen_safe'])

# If user emphasizes being open now
if boosts['open_now'] > 0.5:
    final_weights['hours_match_score'] *= (1 + boosts['open_now'])

# Renormalize weights to sum to 1.0
total = sum(final_weights.values())
final_weights = {k: v/total for k, v in final_weights.items()}
```

---

## 5. Score Calculation Methods

### 5.1 Distance Score
Calculate proximity score (closer = higher score):

**Formula:**
```
distance_score = 1.0 - (distance_miles / max_distance)

Where:
- distance_miles: actual distance to restaurant
- max_distance: filter limit or 10 miles (whichever is smaller)
- Apply sigmoid smoothing to avoid cliff at max distance

Sigmoid variant:
distance_score = 1.0 / (1.0 + exp(k * (distance_miles - optimal_distance)))
Where:
- k = steepness factor (default: 2.0)
- optimal_distance = user's ideal distance (default: 0.5 miles)
```

**Example:**
```
Restaurant at 0.3 miles: score = 0.95
Restaurant at 1.0 miles: score = 0.85
Restaurant at 3.0 miles: score = 0.60
Restaurant at 5.0 miles: score = 0.40
```

### 5.2 Rating Score
Calculate quality score based on rating and confidence:

**Formula:**
```
rating_score = (rating / 5.0) * confidence_factor

Where:
- rating: 0.0-5.0 scale
- confidence_factor = min(1.0, review_count / 50)
  - Penalize restaurants with few reviews
  - Full confidence at 50+ reviews

If rating missing:
rating_score = 0.5 (neutral, not 0.0)
```

**Example:**
```
4.5 stars, 100 reviews: score = 0.90 * 1.0 = 0.90
4.5 stars, 10 reviews: score = 0.90 * 0.20 = 0.18
No rating: score = 0.50
```

### 5.3 Review Count Score
Calculate credibility score based on number of reviews:

**Formula:**
```
review_count_score = log(1 + review_count) / log(1 + 10000)

Where:
- Logarithmic scale (diminishing returns)
- 10,000 reviews = score of 1.0
- 100 reviews = score of ~0.50
- 10 reviews = score of ~0.26
```

**Example:**
```
1000 reviews: score = 0.75
100 reviews: score = 0.50
10 reviews: score = 0.26
0 reviews: score = 0.0
```

### 5.4 NL Relevance Score
Calculate match to natural language query:

**Formula:**
```
nl_relevance_score = weighted_sum of:
- cuisine_match: 1.0 if exact match, 0.8 if similar, 0.0 if different
- dietary_match: 1.0 if fully accommodates, 0.0 if conflicts
- feature_match: (matched_features / requested_features)
- ambience_match: Use keyword matching against review topics
- price_match: 1.0 if in range, 0.0 if outside

Weights:
- cuisine_match: 0.35
- dietary_match: 0.35
- feature_match: 0.15
- ambience_match: 0.10
- price_match: 0.05
```

**Example:**
```
Query: "cozy vegan italian with outdoor seating"
Restaurant: Italian, vegan options, has patio, reviews mention "cozy"
→ cuisine: 1.0, dietary: 1.0, features: 1.0, ambience: 0.9
→ relevance_score = 0.35*1.0 + 0.35*1.0 + 0.15*1.0 + 0.10*0.9 = 0.94
```

### 5.5 Allergen Fit Score
Calculate dietary safety score:

**Formula:**
```
allergen_fit_score = 1.0 - max(allergen_probabilities)

Where:
- allergen_probabilities: list of probabilities for allergens user wants to avoid
- Use max (worst case) for safety

Example for gluten-free request:
- Restaurant A: gluten_prob = 0.1 → score = 0.9
- Restaurant B: gluten_prob = 0.8 → score = 0.2

Confidence adjustment:
allergen_fit_score *= allergen_confidence
```

**Special Cases:**
```
No allergen data available: score = 0.5 (neutral)
Dietary restriction but no allergen analysis: score = 0.3 (penalize missing data)
High allergen probability (>0.7): score < 0.3 (strong penalty)
```

### 5.6 Hours Match Score
Calculate temporal compatibility:

**Formula:**
```
If "open now" requested:
  hours_match_score = 1.0 if open, 0.0 if closed, 0.5 if unknown

If "open at time" requested:
  hours_match_score = 1.0 if open at time, 0.0 if closed, 0.5 if unknown

If no temporal requirement:
  hours_match_score = 0.0 (doesn't affect ranking)
```

### 5.7 Ambience Score
Calculate atmosphere match (if applicable):

**Formula:**
```
ambience_score = keyword_overlap / total_keywords

Where:
- keyword_overlap: count of ambience keywords from query found in reviews/description
- total_keywords: count of ambience keywords in query

Example:
Query has "cozy" and "romantic"
Restaurant reviews mention "cozy" but not "romantic"
→ ambience_score = 1/2 = 0.5
```

### 5.8 Price Match Score
Calculate price compatibility:

**Formula:**
```
If restaurant price_level in user's acceptable range:
  price_match_score = 1.0
Else if one level off:
  price_match_score = 0.5
Else:
  price_match_score = 0.0

Example:
User accepts "$" and "$$"
Restaurant is "$$" → score = 1.0
Restaurant is "$$$" → score = 0.5
Restaurant is "$$$$" → score = 0.0
```

---

## 6. Helper Functions to Create

### 6.1 Filter Application Helper
**Function:** `_apply_filters(restaurants: List[Dict], filters: StructuredFilters) -> Tuple[List[Dict], List[Dict]]`

**Purpose:** Remove restaurants that don't meet hard requirements

**Should check:**
- Cuisine match (if filter specified)
- Dietary accommodation (if filter specified)
- Required features (if filter specified)
- Price level (if filter specified)
- Distance limit (if filter specified)
- Open now / open at time (if filter specified)

**Returns:** (filtered_restaurants, removed_restaurants)

**Example Logic:**
```
For each restaurant:
  If cuisine filter AND restaurant.cuisine not in filters.cuisine:
    → remove
  If dietary filter AND allergen_fit_score < 0.6:
    → remove (not safe enough)
  If features filter AND not all features present:
    → remove
  If distance_max_miles AND distance > max:
    → remove
  Etc.
```

### 6.2 Component Score Calculator Helper
**Function:** `_calculate_component_scores(restaurant: Dict, context: Dict) -> ScoreBreakdown`

**Purpose:** Calculate all individual score components

**Should calculate:**
- Distance score using Haversine distance
- Rating score with review count confidence
- Review count score (logarithmic)
- NL relevance score (if query provided)
- Allergen fit score (if dietary filters)
- Hours match score (if temporal requirement)
- Ambience score (if ambience keywords)
- Price match score (if price preference)

**Returns:** ScoreBreakdown object with all components

### 6.3 Score Normalization Helper
**Function:** `_normalize_scores(score_breakdowns: List[ScoreBreakdown], method: str) -> List[ScoreBreakdown]`

**Purpose:** Normalize scores to 0-1 range for fair comparison

**Methods:**
- `min_max`: `(value - min) / (max - min)`
- `z_score`: `(value - mean) / std_dev`
- `sigmoid`: `1 / (1 + exp(-k * (value - threshold)))`

**Should handle:**
- All zero values (set all to 0.5)
- All same values (set all to 1.0)
- Missing values (set to 0.5)

**Returns:** Normalized score breakdowns

### 6.4 Weight Application Helper
**Function:** `_apply_weights(score_breakdown: ScoreBreakdown, weights: Dict, boosts: RankingBoosts) -> float`

**Purpose:** Combine component scores using weights and boosts

**Formula:**
```
final_score = sum(component_score * weight * boost_multiplier for each component)

boost_multiplier = 1.0 + (boost_value * boost_sensitivity)
Where boost_sensitivity = 0.5 (prevents extreme adjustments)
```

**Should:**
- Apply base strategy weights
- Apply boost adjustments
- Ensure final score in 0.0-1.0 range
- Handle missing components gracefully

**Returns:** Final score (float)

### 6.5 Sorting and Ranking Helper
**Function:** `_sort_and_rank(scored_restaurants: List[Tuple[Dict, float, ScoreBreakdown]]) -> List[RankedRestaurant]`

**Purpose:** Sort by score and assign rank positions

**Should:**
- Sort by final_score descending
- Assign rank numbers (1-indexed)
- Handle ties (same score)
- Limit to requested number of results

**Tie-Breaking Strategy:**
```
If scores equal:
1. Higher rating wins
2. If still tied, more reviews wins
3. If still tied, closer distance wins
4. If still tied, alphabetical by name
```

**Returns:** List of RankedRestaurant objects

### 6.6 Explanation Generator Helper
**Function:** `_generate_explanation(restaurant: RankedRestaurant, filters: Dict, boosts: Dict) -> str`

**Purpose:** Create human-readable explanation for ranking

**Should mention:**
- Top 2-3 scoring factors
- Any perfect matches (exact cuisine, fully safe allergens)
- Any standout features (highly rated, very close, currently open)
- Any caveats (few reviews, missing menu, low allergen confidence)

**Template Examples:**
```
Rank 1: "Top choice because it perfectly matches your vegan requirements (98% confidence), has excellent ratings (4.6/5 from 892 reviews), and is currently open."

Rank 5: "Good option with solid ratings (4.2/5), but slightly farther away (2.3 miles) and missing menu data for allergen verification."

Rank 10: "Meets your requirements but has limited reviews (12), so rating confidence is lower."
```

### 6.7 Match Reasons Extractor Helper
**Function:** `_extract_match_reasons(restaurant: Dict, score_breakdown: ScoreBreakdown, filters: Dict) -> List[str]`

**Purpose:** List specific reasons why restaurant matches

**Should extract:**
- Cuisine match: "Authentic Italian cuisine"
- Dietary safe: "Vegan-friendly (95% confidence)"
- Features: "Has outdoor seating"
- Quality: "Highly rated (4.7/5)"
- Proximity: "Only 0.3 miles away"
- Temporal: "Currently open"
- Ambience: "Cozy atmosphere mentioned in reviews"

**Returns:** List of 3-5 match reason strings

### 6.8 Warning Generator Helper
**Function:** `_generate_warnings(restaurant: Dict) -> List[str]`

**Purpose:** Flag potential issues or missing data

**Should warn about:**
- Low enrichment confidence: "Some data unverified"
- Missing allergen data: "No menu found - allergen data unavailable"
- Few reviews: "Limited reviews (only 5)"
- Conflicting sources: "Rating varies across sources (3.8-4.5)"
- Missing hours: "Hours not available - may be closed"
- Low allergen confidence: "Allergen analysis has low confidence"

**Returns:** List of warning strings

### 6.9 Missing Data Handler Helper
**Function:** `_handle_missing_data(score_breakdown: ScoreBreakdown) -> ScoreBreakdown`

**Purpose:** Assign reasonable defaults for missing score components

**Strategy:**
```
Missing rating: Set rating_score = 0.5 (neutral)
Missing review_count: Set review_count_score = 0.0
Missing allergen data: Set allergen_fit_score = 0.3 (penalize but don't eliminate)
Missing hours: Set hours_match_score = 0.5 (neutral)
Missing price: Set price_match_score = 0.5 (neutral)
```

**Should:**
- Track which fields are missing
- Apply conservative scores
- Note in warnings

**Returns:** Updated score breakdown with imputed values

### 6.10 Tie Breaker Helper
**Function:** `_break_ties(tied_restaurants: List[RankedRestaurant]) -> List[RankedRestaurant]`

**Purpose:** Order restaurants with identical scores

**Tie-Breaking Hierarchy:**
```
1. Higher rating
2. More reviews
3. Closer distance
4. Has menu data (for allergen verification)
5. Alphabetical by name
```

**Returns:** Ordered list with ties resolved

---

## 7. Integration Guardrails

### 7.1 Input Validation
Before ranking:
- ✅ Validate restaurants list is non-empty
- ✅ Validate at least one restaurant has required fields (name, location)
- ✅ Validate filters object has expected structure
- ✅ Validate boosts values are in 0.0-1.0 range
- ✅ Validate strategy is valid RankingStrategy
- ✅ Validate user_location has valid lat/lon
- ✅ Validate limit is positive integer

### 7.2 Output Contract Compliance
MUST return exact format expected by Planner/Frontend:
- ✅ `ranked_results` is array of RankedRestaurant objects
- ✅ `rank` is 1-indexed (not 0-indexed)
- ✅ All score components are floats in 0.0-1.0 range
- ✅ `explanation` is non-empty string
- ✅ `match_reasons` has 1-5 items
- ✅ `score_breakdown` includes all component scores
- ✅ `raw_values` preserved for debugging
- ✅ `metadata` includes timing and statistics

### 7.3 Score Sanity Checks
Before returning results:
```
For each ranked restaurant:
- Assert final_score is in 0.0-1.0 range
- Assert score_breakdown components sum reasonably
- Assert rank order matches score order
- Warn if top result has score < 0.5 (poor matches)
- Warn if all results have score > 0.9 (suspiciously high)
```

### 7.4 Partial Results Handling
```
If no restaurants pass filters:
- Return status='partial'
- Include explanation: "No restaurants match all requirements"
- Suggest relaxing filters (show removed restaurants)

If < limit results after filtering:
- Return available results
- Note in metadata: actual_count < limit

If scoring fails for some restaurants:
- Skip those restaurants
- Log errors
- Continue with successfully scored restaurants
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test: Distance Score Calculation**
```
Restaurant at 0.5 miles: expect score ~0.95
Restaurant at 2.0 miles: expect score ~0.80
Restaurant at 5.0 miles: expect score ~0.50
Restaurant at 10.0 miles: expect score ~0.10
```

**Test: Rating Score with Confidence**
```
4.5 rating, 100 reviews: expect score ~0.90
4.5 rating, 10 reviews: expect score ~0.36
4.5 rating, 0 reviews: expect score = 0.0
```

**Test: Filter Application**
```
Input: 20 restaurants, filter cuisine='italian'
Expected: 5 italian restaurants pass, 15 removed
Verify: removed list contains non-italian restaurants
```

**Test: Weight Application**
```
Strategy: DISTANCE (70% distance, 20% rating, 10% reviews)
Restaurant: distance_score=0.9, rating_score=0.8, review_count_score=0.5
Expected: final_score = 0.7*0.9 + 0.2*0.8 + 0.1*0.5 = 0.84
```

**Test: Tie Breaking**
```
Two restaurants with score=0.85
Restaurant A: rating=4.5, reviews=100, distance=1.0mi
Restaurant B: rating=4.3, reviews=200, distance=0.8mi
Expected: A ranks higher (higher rating wins)
```

### 8.2 Integration Tests

**Test: End-to-End Ranking**
```
Input: 50 enriched restaurants, hybrid strategy, vegan filter
Process: Filter → Score → Sort → Explain
Verify:
- All results are vegan-safe
- Scores decrease monotonically
- Explanations mention vegan safety
- Top result has highest score
```

**Test: Strategy Comparison**
```
Same input, different strategies (distance vs rating vs hybrid)
Verify:
- DISTANCE strategy: closest restaurants rank highest
- RATING strategy: highest rated restaurants rank highest
- HYBRID strategy: balanced ranking
```

**Test: Boost Application**
```
Query with high allergen_safe boost (0.8)
Verify:
- Allergen_fit_score has high weight in final_score
- Restaurants with high allergen confidence rank higher
```

**Test: Missing Data Handling**
```
Input: Some restaurants missing ratings, some missing allergen data
Verify:
- No crashes or errors
- Missing data gets neutral scores
- Warnings generated for affected restaurants
```

### 8.3 Edge Case Tests

**Test: All Restaurants Filtered Out**
```
Input: 10 italian restaurants, filter cuisine='chinese'
Expected: status='partial', empty results, clear explanation
```

**Test: Single Restaurant**
```
Input: 1 restaurant
Expected: Rank=1, reasonable score, no comparison needed
```

**Test: Identical Scores**
```
Input: Multiple restaurants with exact same attributes
Expected: Tie-breaker applied, deterministic ordering
```

**Test: Extreme Boosts**
```
Input: Boost values all set to 1.0 (maximum)
Expected: Weights adjusted but still normalized, no overflow
```

---

## 9. Example Ranking Flows

### Example 1: Simple Distance-Based Ranking
```
Input:
- 10 restaurants within 5 miles
- No filters
- Strategy: DISTANCE

Processing:
1. All 10 pass filters (no filters applied)
2. Calculate distance scores:
   - Restaurant A: 0.3 mi → score = 0.94
   - Restaurant B: 1.0 mi → score = 0.80
   - Restaurant C: 2.5 mi → score = 0.50
3. Sort by distance_score (70% weight)
4. Generate explanations mentioning proximity

Output:
Rank 1: Restaurant A (0.3 mi away)
  - score: 0.92
  - explanation: "Closest option at just 0.3 miles away"
Rank 2: Restaurant B (1.0 mi away)
  - score: 0.84
  - explanation: "Nearby option within 1 mile"
...
```

### Example 2: Complex NL Query with Dietary Filter
```
Input:
- 30 restaurants
- Filters: dietary=['vegan'], features=['outdoor_seating']
- Boosts: allergen_safe=0.7, ambience_match=0.5
- Strategy: HYBRID

Processing:
1. Apply filters:
   - Remove non-vegan: 20 → 15 restaurants
   - Remove without outdoor seating: 15 → 8 restaurants
2. Calculate component scores for 8 restaurants:
   - distance_score (0-1)
   - rating_score (0-1)
   - review_count_score (0-1)
   - allergen_fit_score (0-1) - HIGH importance
   - nl_relevance_score (0-1)
3. Apply HYBRID weights with allergen boost:
   - Base weights: distance=0.25, rating=0.25, allergen=0.10
   - After boost: allergen_fit weight increased to ~0.25
4. Sort by final_score
5. Generate explanations highlighting vegan safety

Output:
Rank 1: Plant Cafe
  - score: 0.89
  - explanation: "Perfect match - vegan-friendly (98% confidence), outdoor patio, highly rated (4.6/5)"
  - match_reasons: [
      "Vegan-friendly (98% confidence)",
      "Has outdoor seating",
      "Highly rated (4.6/5)",
      "Currently open"
    ]
Rank 2: Green Leaf Bistro
  - score: 0.82
  - explanation: "Great vegan options (92% confidence), patio seating, good ratings (4.3/5)"
...
```

### Example 3: Rating-Focused with Few Results
```
Input:
- 50 restaurants
- Filters: cuisine=['italian'], price_level=['$$$', '$$$$']
- Strategy: RATING

Processing:
1. Apply filters:
   - Remove non-italian: 50 → 12 restaurants
   - Remove non-upscale: 12 → 4 restaurants
2. Calculate scores (rating weighted 60%):
   - Restaurant A: rating=4.8, reviews=523 → rating_score=0.96
   - Restaurant B: rating=4.6, reviews=892 → rating_score=0.92
   - Restaurant C: rating=4.5, reviews=234 → rating_score=0.90
   - Restaurant D: rating=4.2, reviews=89 → rating_score=0.73
3. Sort by rating_score
4. Note: Only 4 results (< limit of 10)

Output:
status: 'success'
ranked_results: [4 restaurants]
metadata:
  total_candidates: 50
  total_after_filter: 4
  total_returned: 4
  note: "Limited results due to specific filters"
```

### Example 4: Allergen-Safe Strategy
```
Input:
- 25 restaurants
- Filters: dietary=['gluten_free']
- Strategy: ALLERGEN_SAFE
- Boost: allergen_safe=0.8

Processing:
1. Apply filters:
   - Check gluten probability for each
   - Remove if gluten_prob > 0.4: 25 → 15 restaurants
2. Calculate allergen_fit_score (40% weight):
   - Restaurant A: gluten_prob=0.05 → fit_score=0.95
   - Restaurant B: gluten_prob=0.15 → fit_score=0.85
   - Restaurant C: gluten_prob=0.35 → fit_score=0.65
3. Combine with rating (25%) and distance (20%)
4. Sort by final_score (allergen safety dominant)

Output:
Rank 1: Celiac-Friendly Bistro
  - score: 0.91
  - allergen_fit_score: 0.98 (gluten_prob=0.02)
  - explanation: "Safest option for gluten-free dining (98% confidence), with excellent ratings"
  - warnings: []
Rank 2: Italian Kitchen
  - score: 0.76
  - allergen_fit_score: 0.75 (gluten_prob=0.25)
  - explanation: "Has gluten-free options but some risk (75% confidence)"
  - warnings: ["Menu analysis based on limited data"]
```

---

## 10. Common Pitfalls to Avoid

1. **❌ Don't ignore missing data**
   - Some restaurants won't have ratings or allergen data
   - Use neutral scores (0.5), don't skip or set to 0.0

2. **❌ Don't apply filters too strictly**
   - If removing 90%+ of restaurants, warn user
   - Suggest relaxing filters

3. **❌ Don't forget to normalize**
   - Raw scores have different scales
   - Always normalize to 0-1 before combining

4. **❌ Don't overflow weights**
   - After applying boosts, renormalize weights to sum ~1.0
   - Prevents extreme score inflation

5. **❌ Don't rank without explanations**
   - Users need to understand WHY something ranked #1
   - Explanations build trust

6. **❌ Don't ignore confidence**
   - Low-confidence allergen data should reduce scores
   - Few reviews should reduce rating confidence

7. **❌ Don't forget tie-breaking**
   - Multiple restaurants can have identical scores
   - Apply consistent tie-breaking logic

8. **❌ Don't skip validation**
   - Verify scores are in valid range
   - Check for NaN or infinity values

9. **❌ Don't assume complete data**
   - Handle cases where allergen analysis failed
   - Handle cases where enrichment was partial

10. **❌ Don't hard-code thresholds**
    - Make scoring parameters configurable
    - Allow tuning based on user feedback

---

## 11. Success Criteria

The Ranker Agent is complete when it:
- ✅ Correctly applies all filter types
- ✅ Calculates all score components accurately
- ✅ Produces monotonically decreasing scores (rank 1 > rank 2 > ...)
- ✅ Generates clear, accurate explanations
- ✅ Handles missing data gracefully
- ✅ Supports all 5 ranking strategies
- ✅ Applies boost weights correctly
- ✅ Breaks ties deterministically
- ✅ Completes ranking in <500ms for 50 restaurants
- ✅ Returns output in exact contract format
- ✅ Passes all unit and integration tests

---

## 12. Integration Checklist

Before marking complete, verify:
- [ ] Receives enriched restaurants from Data Enrichment Agent
- [ ] Receives filters and boosts from NL Query Interpreter
- [ ] Applies filters correctly (removes non-matching)
- [ ] Calculates all score components
- [ ] Normalizes scores to 0-1 range
- [ ] Applies strategy weights correctly
- [ ] Incorporates boost adjustments
- [ ] Sorts by final score descending
- [ ] Generates explanations for each result
- [ ] Handles edge cases (no results, few results, ties)
- [ ] Returns exact output format to Planner
- [ ] Tests cover all strategies and scenarios

---

## 13. Next Steps

Once Ranker Agent is complete:
1. Test with diverse restaurant sets (10, 50, 100 restaurants)
2. Validate scoring with human judgments
3. Tune weight configurations based on user feedback
4. Test all 5 strategies with same input
5. Verify integration with Planner and Frontend

Then proceed to: **Menu Finder Agent** (locates menu URLs for allergen analysis)

---

**Remember:** This agent directly impacts user satisfaction. If rankings don't "make sense" to users, they'll lose trust in the entire system. Prioritize transparency (good explanations) and fairness (proper normalization) over complexity.