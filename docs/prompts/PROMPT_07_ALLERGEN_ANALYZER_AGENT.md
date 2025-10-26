# PROMPT 7: Allergen Analyzer Agent Implementation Guide

## Context
You are building the **Allergen Analyzer Agent**, which detects allergens in restaurant menus by analyzing menu text from the OCR Worker. This is a **safety-critical agent** that helps users with dietary restrictions avoid dangerous foods.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- LLM: Claude Haiku 4.5 or Sonnet 4.5 (`claude-haiku-4-5-20251001` or `claude-sonnet-4-5-20250929`)
- Backend: Flask API
- Caching: Redis (14-day TTL)
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The Allergen Analyzer Agent must:
1. **Parse menu items** - Extract dish names and descriptions from OCR text
2. **Identify ingredients** - Recognize ingredients mentioned in dishes
3. **Map to allergens** - Connect ingredients to common allergens
4. **Calculate probabilities** - Assign likelihood scores (0.0-1.0) for each allergen
5. **Apply cuisine priors** - Use cultural context (Italian → high gluten)
6. **Generate evidence** - Cite specific text supporting allergen claims
7. **Provide reasoning** - Explain why allergen is likely/unlikely
8. **Handle ambiguity** - Flag uncertain cases with low confidence
9. **Prioritize safety** - Err on side of caution (false positives better than false negatives)
10. **Support dish-level and venue-level analysis** - Both granular and aggregate views

**CRITICAL SAFETY PRINCIPLE:** When in doubt, assume allergen IS present and flag with lower confidence. It's better to warn unnecessarily than to miss a dangerous allergen.

---

## 2. File Structure

**Create:** `agents/allergen_analyzer_agent.py`

This file should contain:

### 2.1 Allergen Type Enum
Define major allergens (FDA top 9 + common additions):
- `GLUTEN` - Wheat, barley, rye
- `DAIRY` - Milk, cheese, butter, cream
- `EGGS` - Eggs and egg products
- `SOY` - Soybeans and soy products
- `PEANUTS` - Peanuts and peanut products
- `TREE_NUTS` - Almonds, walnuts, cashews, etc.
- `SHELLFISH` - Shrimp, crab, lobster, etc.
- `FISH` - Fish and fish products
- `SESAME` - Sesame seeds and oil
- `CORN` - Corn and corn products (added for completeness)
- `SULFITES` - Preservatives in wine, dried fruit

### 2.2 Evidence Type Enum
Define types of evidence:
- `EXPLICIT_INGREDIENT` - Ingredient clearly stated (e.g., "contains wheat")
- `DISH_ARCHETYPE` - Known dish type (e.g., "pasta" implies gluten)
- `CUISINE_PRIOR` - Cultural probability (e.g., Italian → dairy)
- `COOKING_METHOD` - Preparation implies allergen (e.g., "fried" → soy oil)
- `CROSS_CONTAMINATION` - Shared equipment/facility
- `INFERENCE` - Logical deduction (e.g., "cheese sauce" → dairy)
- `ALLERGEN_NOTE` - Explicit allergen declaration

### 2.3 Confidence Level Enum
Define confidence bands:
- `CERTAIN` (0.9-1.0) - Explicit ingredient listed
- `HIGH` (0.7-0.89) - Strong evidence or known dish archetype
- `MEDIUM` (0.5-0.69) - Likely based on cuisine/description
- `LOW` (0.3-0.49) - Possible but uncertain
- `UNLIKELY` (0.1-0.29) - Probably not present
- `ABSENT` (0.0-0.09) - Almost certainly not present

### 2.4 Core Classes

**AllergenAnalysisRequest Class:**
Represents an analysis job. Should include:
- `restaurant_id`: str
- `restaurant_name`: str
- `cuisine`: Optional[str] - For cuisine priors
- `menu_text`: str - From OCR Worker
- `menu_image_urls`: List[str] - For evidence linking
- `language`: str - Menu language
- `ocr_confidence`: float - OCR quality indicator
- `force_refresh`: bool - Bypass cache

**MenuItem Class:**
Represents a parsed menu item. Should include:
- `name`: str - Dish name
- `description`: Optional[str] - Dish description
- `price`: Optional[str] - Price if found
- `section`: Optional[str] - Menu section (Appetizers, Entrees, etc.)
- `ingredients_mentioned`: List[str] - Explicitly stated ingredients
- `preparation_methods`: List[str] - Cooking methods (fried, grilled, etc.)
- `text_snippet`: str - Original menu text for this item
- `line_numbers`: List[int] - Where in menu this appears

**AllergenEvidence Class:**
Evidence for allergen presence. Should include:
- `allergen`: AllergenType
- `evidence_type`: EvidenceType
- `snippet`: str - Relevant text from menu
- `reasoning`: str - Explanation
- `confidence_contribution`: float - How much this evidence adds to probability
- `source_line`: Optional[int] - Where evidence found

**DishAllergenProfile Class:**
Allergen analysis for one dish. Should include:
- `dish_name`: str
- `allergen_probabilities`: Dict[AllergenType, float] - 0.0-1.0 for each allergen
- `evidence`: Dict[AllergenType, List[AllergenEvidence]] - Supporting evidence
- `confidence`: float - Overall confidence in analysis
- `ingredients_detected`: List[str]
- `warnings`: List[str] - Concerns or ambiguities
- `safe_for`: List[str] - Dietary restrictions likely safe (e.g., "vegan-friendly")
- `unsafe_for`: List[str] - Dietary restrictions definitely not safe

**VenueAllergenSummary Class:**
Aggregate allergen profile. Should include:
- `restaurant_id`: str
- `allergen_prevalence`: Dict[AllergenType, float] - 0.0-1.0 prevalence across menu
- `allergen_stats`: Dict[AllergenType, Dict] - Statistics per allergen:
  - `dishes_with_allergen`: int
  - `total_dishes`: int
  - `percentage`: float
  - `average_probability`: float
- `safest_dishes`: List[str] - Dishes with fewest allergens
- `highest_risk_dishes`: List[str] - Dishes with most allergens
- `general_warnings`: List[str] - Venue-wide concerns

**AllergenAnalysisResult Class:**
Complete analysis output. Should include:
- `restaurant_id`: str
- `restaurant_name`: str
- `cuisine`: Optional[str]
- `updated_at`: str - ISO timestamp
- `menu_items_analyzed`: List[MenuItem]
- `by_dish`: List[DishAllergenProfile]
- `venue_summary`: VenueAllergenSummary
- `provenance`: Dict - Sources and methods used
- `overall_confidence`: float - Analysis reliability
- `cache_hit`: bool
- `warnings`: List[str] - Analysis-wide concerns
- `metadata`: Dict - Processing details

**AllergenAnalyzerAgent Class:**
Main agent implementation. Should include methods:
- `__init__()` - Initialize Claude client, allergen database
- `analyze_menu()` - Main entry point
- `_parse_menu_items()` - Extract dishes from text
- `_identify_ingredients()` - Find ingredients in descriptions
- `_map_ingredient_to_allergens()` - Allergen database lookup
- `_analyze_dish()` - Full allergen analysis for one dish
- `_calculate_allergen_probability()` - Probability for one allergen in one dish
- `_apply_cuisine_priors()` - Adjust probabilities by cuisine
- `_generate_evidence()` - Create evidence objects
- `_aggregate_venue_summary()` - Combine dish-level to venue-level
- `_calculate_confidence()` - Score analysis reliability
- `_classify_safety()` - Determine safe/unsafe for diets
- `_get_from_cache()` - Check cache
- `_save_to_cache()` - Store result

---

## 3. Input/Output Contracts

### 3.1 Input Format (from OCR Worker Agent)
Receives analysis requests in this format:
```python
{
    'restaurant_id': 'rest_123',
    'restaurant_name': 'Super Duper Burger',
    'cuisine': 'burger',
    'menu_text': '''MENU

BURGERS
Super Duper Burger - $10.99
Classic cheeseburger with lettuce, tomato, onion
Contains: wheat, dairy, soy

Veggie Burger - $9.99
Plant-based patty with avocado
Contains: soy, wheat

SIDES
French Fries - $3.99
Crispy golden fries
Cooked in soybean oil

Onion Rings - $4.99
Beer-battered onion rings
Contains: wheat, dairy
    ''',
    'menu_image_urls': ['https://example.com/menu.jpg'],
    'language': 'en',
    'ocr_confidence': 0.91,
    'force_refresh': False
}
```

### 3.2 Output Format (to Safety & QA Agent / Frontend)
Must return analysis results in this format:
```python
{
    'status': 'success' | 'partial' | 'error',
    
    'restaurant_id': 'rest_123',
    'restaurant_name': 'Super Duper Burger',
    'cuisine': 'burger',
    'updated_at': '2025-10-26T10:30:00Z',
    
    'menu_items_analyzed': [
        {
            'name': 'Super Duper Burger',
            'description': 'Classic cheeseburger with lettuce, tomato, onion',
            'price': '$10.99',
            'section': 'BURGERS',
            'ingredients_mentioned': ['cheeseburger', 'lettuce', 'tomato', 'onion', 'wheat', 'dairy', 'soy'],
            'preparation_methods': [],
            'text_snippet': 'Super Duper Burger - $10.99\nClassic cheeseburger with lettuce, tomato, onion\nContains: wheat, dairy, soy',
            'line_numbers': [3, 4, 5]
        },
        // ... more items
    ],
    
    'by_dish': [
        {
            'dish_name': 'Super Duper Burger',
            'allergen_probabilities': {
                'GLUTEN': 0.98,
                'DAIRY': 0.95,
                'EGGS': 0.15,
                'SOY': 0.85,
                'PEANUTS': 0.02,
                'TREE_NUTS': 0.02,
                'SHELLFISH': 0.01,
                'FISH': 0.01,
                'SESAME': 0.35,  // bun might have sesame
                'CORN': 0.15,
                'SULFITES': 0.05
            },
            'evidence': {
                'GLUTEN': [
                    {
                        'allergen': 'GLUTEN',
                        'evidence_type': 'ALLERGEN_NOTE',
                        'snippet': 'Contains: wheat',
                        'reasoning': 'Explicit allergen declaration states wheat, which contains gluten',
                        'confidence_contribution': 0.98,
                        'source_line': 5
                    },
                    {
                        'allergen': 'GLUTEN',
                        'evidence_type': 'DISH_ARCHETYPE',
                        'snippet': 'cheeseburger',
                        'reasoning': 'Burgers traditionally served on wheat buns',
                        'confidence_contribution': 0.90,
                        'source_line': 4
                    }
                ],
                'DAIRY': [
                    {
                        'allergen': 'DAIRY',
                        'evidence_type': 'ALLERGEN_NOTE',
                        'snippet': 'Contains: dairy',
                        'reasoning': 'Explicit allergen declaration',
                        'confidence_contribution': 0.95,
                        'source_line': 5
                    },
                    {
                        'allergen': 'DAIRY',
                        'evidence_type': 'EXPLICIT_INGREDIENT',
                        'snippet': 'cheeseburger',
                        'reasoning': 'Cheese is a dairy product',
                        'confidence_contribution': 0.98,
                        'source_line': 4
                    }
                ],
                'SOY': [
                    {
                        'allergen': 'SOY',
                        'evidence_type': 'ALLERGEN_NOTE',
                        'snippet': 'Contains: soy',
                        'reasoning': 'Explicit allergen declaration',
                        'confidence_contribution': 0.85,
                        'source_line': 5
                    }
                ]
            },
            'confidence': 0.92,
            'ingredients_detected': ['wheat', 'dairy', 'soy', 'cheese', 'lettuce', 'tomato', 'onion'],
            'warnings': ['Sesame seeds may be present on bun but not explicitly stated'],
            'safe_for': [],
            'unsafe_for': ['vegan', 'vegetarian', 'gluten-free', 'dairy-free']
        },
        {
            'dish_name': 'Veggie Burger',
            'allergen_probabilities': {
                'GLUTEN': 0.95,
                'DAIRY': 0.05,
                'EGGS': 0.08,
                'SOY': 0.92,
                'PEANUTS': 0.02,
                'TREE_NUTS': 0.02,
                'SHELLFISH': 0.01,
                'FISH': 0.01,
                'SESAME': 0.30,
                'CORN': 0.15,
                'SULFITES': 0.05
            },
            'evidence': {
                'GLUTEN': [
                    {
                        'allergen': 'GLUTEN',
                        'evidence_type': 'ALLERGEN_NOTE',
                        'snippet': 'Contains: wheat',
                        'reasoning': 'Explicit allergen declaration',
                        'confidence_contribution': 0.95,
                        'source_line': 8
                    }
                ],
                'SOY': [
                    {
                        'allergen': 'SOY',
                        'evidence_type': 'ALLERGEN_NOTE',
                        'snippet': 'Contains: soy',
                        'reasoning': 'Explicit allergen declaration',
                        'confidence_contribution': 0.90,
                        'source_line': 8
                    },
                    {
                        'allergen': 'SOY',
                        'evidence_type': 'EXPLICIT_INGREDIENT',
                        'snippet': 'Plant-based patty',
                        'reasoning': 'Plant-based burger patties commonly contain soy protein',
                        'confidence_contribution': 0.75,
                        'source_line': 7
                    }
                ],
                'DAIRY': [
                    {
                        'allergen': 'DAIRY',
                        'evidence_type': 'INFERENCE',
                        'snippet': 'Veggie Burger',
                        'reasoning': 'Veggie burgers sometimes include cheese or mayo, but not explicitly stated here',
                        'confidence_contribution': 0.05,
                        'source_line': 6
                    }
                ]
            },
            'confidence': 0.88,
            'ingredients_detected': ['plant-based patty', 'avocado', 'wheat', 'soy'],
            'warnings': [],
            'safe_for': ['dairy-free'],
            'unsafe_for': ['vegan', 'gluten-free']
        },
        // ... more dishes
    ],
    
    'venue_summary': {
        'restaurant_id': 'rest_123',
        'allergen_prevalence': {
            'GLUTEN': 0.75,  // 75% of dishes contain gluten
            'DAIRY': 0.50,
            'EGGS': 0.10,
            'SOY': 0.80,
            'PEANUTS': 0.02,
            'TREE_NUTS': 0.02,
            'SHELLFISH': 0.01,
            'FISH': 0.01,
            'SESAME': 0.25,
            'CORN': 0.15,
            'SULFITES': 0.05
        },
        'allergen_stats': {
            'GLUTEN': {
                'dishes_with_allergen': 3,
                'total_dishes': 4,
                'percentage': 0.75,
                'average_probability': 0.93
            },
            'SOY': {
                'dishes_with_allergen': 4,
                'total_dishes': 4,
                'percentage': 1.0,
                'average_probability': 0.88
            },
            // ... more allergens
        },
        'safest_dishes': [
            'French Fries'  // if only concern is cross-contamination
        ],
        'highest_risk_dishes': [
            'Super Duper Burger',  // multiple allergens
            'Onion Rings'
        ],
        'general_warnings': [
            'High prevalence of gluten (75% of dishes)',
            'High prevalence of soy (100% of dishes)',
            'All fried items cooked in soybean oil',
            'Cross-contamination risk in kitchen'
        ]
    },
    
    'provenance': {
        'menu_text_source': 'ocr',
        'ocr_confidence': 0.91,
        'llm_model': 'claude-haiku-4-5-20251001',
        'cuisine_priors_applied': True,
        'cuisine': 'burger',
        'analysis_method': 'ingredient_mapping + claude_reasoning',
        'allergen_database_version': '1.0',
        'last_updated': '2025-10-26T10:30:00Z'
    },
    
    'overall_confidence': 0.87,
    'cache_hit': False,
    
    'warnings': [
        'OCR confidence was 0.91 - some text may be misread',
        'No explicit allergen-free claims verified',
        'Cross-contamination possible in shared kitchen'
    ],
    
    'metadata': {
        'processing_time_ms': 2156,
        'menu_items_found': 4,
        'total_dishes_analyzed': 4,
        'explicit_allergen_notes': 3,
        'cuisine_priors_used': ['burger', 'american'],
        'ambiguous_items': 0
    }
}
```

---

## 4. Allergen Detection Methodology

### 4.1 Multi-Source Evidence Approach

Combine multiple evidence types for robust detection:

**Evidence Priority (highest to lowest confidence):**
```
1. ALLERGEN_NOTE (0.90-0.98)
   - "Contains: wheat, dairy"
   - "Allergens: peanuts, soy"
   - Most reliable

2. EXPLICIT_INGREDIENT (0.85-0.95)
   - "made with butter"
   - "topped with cheese"
   - Direct ingredient mention

3. DISH_ARCHETYPE (0.75-0.90)
   - "pasta" → gluten
   - "ice cream" → dairy
   - Known dish types

4. COOKING_METHOD (0.60-0.80)
   - "fried" → likely soy oil
   - "breaded" → gluten
   - Preparation implies allergen

5. CUISINE_PRIOR (0.50-0.70)
   - Italian restaurant → high gluten/dairy
   - Japanese restaurant → high soy/fish
   - Cultural probability

6. INFERENCE (0.30-0.60)
   - "burger" might have sesame bun
   - "sauce" might contain soy
   - Logical deduction

7. CROSS_CONTAMINATION (0.10-0.30)
   - Shared fryer, shared kitchen
   - Always possible, low probability
```

### 4.2 Probability Calculation Formula

For each allergen in each dish:

```
P(allergen | dish) = combine_evidence([evidence_items])

Where combine_evidence uses:

Method 1: Maximum probability (conservative)
P_final = max(P_evidence1, P_evidence2, ...)

Method 2: Noisy-OR (Bayesian combination)
P_final = 1 - ∏(1 - P_i) for all evidence P_i

Method 3: Weighted average with confidence
P_final = Σ(P_i * confidence_i) / Σ(confidence_i)

Recommended: Use Method 1 (maximum) for safety
- Takes highest probability from any evidence
- Conservative approach (better safe than sorry)
- Simple to explain
```

**Example Calculation:**
```
Dish: "Cheeseburger with fries"

Evidence for DAIRY:
1. "cheeseburger" → explicit ingredient → P=0.98
2. "burger" archetype → may have cheese → P=0.60
3. American cuisine → dairy common → P=0.50

Using maximum: P(DAIRY) = max(0.98, 0.60, 0.50) = 0.98
```

### 4.3 Cuisine Priors Database

Define baseline allergen probabilities by cuisine:

```python
CUISINE_PRIORS = {
    'italian': {
        'GLUTEN': 0.85,  # Pasta, pizza, bread
        'DAIRY': 0.75,   # Cheese, cream sauces
        'EGGS': 0.40,    # Pasta, desserts
        'SOY': 0.15,
        'TREE_NUTS': 0.25,  # Pine nuts, walnuts
        'SHELLFISH': 0.15,
        'FISH': 0.20
    },
    'japanese': {
        'GLUTEN': 0.50,  # Soy sauce (wheat), tempura
        'SOY': 0.90,     # Soy sauce, miso, tofu
        'FISH': 0.80,    # Sushi, sashimi
        'SHELLFISH': 0.50,
        'SESAME': 0.40,
        'EGGS': 0.30
    },
    'chinese': {
        'GLUTEN': 0.60,  # Soy sauce, noodles
        'SOY': 0.85,     # Soy sauce, tofu
        'PEANUTS': 0.45,
        'SHELLFISH': 0.50,
        'EGGS': 0.40,
        'SESAME': 0.35
    },
    'mexican': {
        'GLUTEN': 0.40,  # Flour tortillas, some dishes
        'DAIRY': 0.65,   # Cheese, sour cream
        'CORN': 0.70,    # Tortillas, chips
        'SOY': 0.25
    },
    'indian': {
        'DAIRY': 0.70,   # Ghee, paneer, yogurt
        'TREE_NUTS': 0.50,  # Cashews, almonds in sauces
        'GLUTEN': 0.45,  # Naan, some breads
        'PEANUTS': 0.25
    },
    'thai': {
        'PEANUTS': 0.60,
        'SHELLFISH': 0.55,
        'FISH': 0.60,    # Fish sauce
        'SOY': 0.50,
        'TREE_NUTS': 0.30,  # Cashews
        'GLUTEN': 0.30
    },
    'french': {
        'DAIRY': 0.80,   # Butter, cream, cheese
        'GLUTEN': 0.70,  # Bread, pastries
        'EGGS': 0.55,
        'SHELLFISH': 0.35,
        'TREE_NUTS': 0.30
    },
    'american': {
        'GLUTEN': 0.70,  # Buns, breading
        'DAIRY': 0.60,   # Cheese, dairy
        'SOY': 0.55,     # Frying oil
        'EGGS': 0.40
    },
    'burger': {
        'GLUTEN': 0.90,  # Buns
        'DAIRY': 0.65,   # Cheese
        'SOY': 0.75,     # Frying oil
        'EGGS': 0.30,    # Mayo
        'SESAME': 0.40   # Sesame buns common
    },
    'vegan': {
        'DAIRY': 0.01,
        'EGGS': 0.01,
        'FISH': 0.01,
        'SHELLFISH': 0.01,
        'SOY': 0.75,     # Common protein source
        'GLUTEN': 0.50,
        'TREE_NUTS': 0.45  // Nut-based cheeses
    },
    'default': {  # fallback
        'GLUTEN': 0.50,
        'DAIRY': 0.40,
        'EGGS': 0.30,
        'SOY': 0.35,
        'PEANUTS': 0.15,
        'TREE_NUTS': 0.15,
        'SHELLFISH': 0.20,
        'FISH': 0.20,
        'SESAME': 0.15,
        'CORN': 0.20,
        'SULFITES': 0.10
    }
}
```

**Usage:**
```
If dish has no explicit evidence for allergen:
  Use cuisine prior as baseline probability
Else:
  Use cuisine prior to boost/adjust explicit evidence
```

---

## 5. Claude Integration for Semantic Understanding

### 5.1 Menu Item Parsing Prompt

Use Claude to extract structured menu items from OCR text:

**System Prompt:**
```
You are a menu parsing assistant. Extract individual menu items from restaurant menu text into structured format. Be thorough and capture all dishes.
```

**User Prompt Template:**
```
Parse this restaurant menu into structured items:

Restaurant: {restaurant_name}
Cuisine: {cuisine}

Menu Text:
{menu_text}

Extract each menu item with:
- name: Dish name
- description: Description if present
- price: Price if present
- section: Menu section (Appetizers, Entrees, etc.)
- ingredients_mentioned: List of ingredients explicitly stated
- preparation_methods: Cooking methods mentioned (fried, grilled, etc.)
- text_snippet: Original text for this item

Return JSON array of menu items. Include items even if incomplete.

Example output:
[
  {
    "name": "Margherita Pizza",
    "description": "Fresh mozzarella, basil, tomato sauce",
    "price": "$14.99",
    "section": "PIZZAS",
    "ingredients_mentioned": ["mozzarella", "basil", "tomato sauce"],
    "preparation_methods": [],
    "text_snippet": "Margherita Pizza - $14.99\nFresh mozzarella, basil, tomato sauce"
  }
]
```

### 5.2 Allergen Detection Prompt

Use Claude to analyze dishes for allergens:

**System Prompt:**
```
You are an allergen detection assistant. Analyze menu items to identify potential allergens. Be conservative - it's better to warn about possible allergens than to miss them.

Your task is to identify likelihood (0.0-1.0) of these allergens:
- GLUTEN (wheat, barley, rye)
- DAIRY (milk, cheese, butter, cream)
- EGGS
- SOY (soybeans, soy sauce)
- PEANUTS
- TREE_NUTS (almonds, walnuts, cashews, etc.)
- SHELLFISH (shrimp, crab, lobster)
- FISH
- SESAME
- CORN
- SULFITES

Provide evidence and reasoning for each detected allergen.
```

**User Prompt Template:**
```
Analyze this dish for allergens:

Dish: {dish_name}
Description: {description}
Cuisine: {cuisine}
Ingredients Mentioned: {ingredients_mentioned}
Preparation: {preparation_methods}

Return JSON with allergen probabilities and evidence:
{
  "allergen_probabilities": {
    "GLUTEN": float,  // 0.0-1.0
    "DAIRY": float,
    // ... all allergens
  },
  "evidence": {
    "GLUTEN": [
      {
        "evidence_type": "EXPLICIT_INGREDIENT" | "DISH_ARCHETYPE" | "INFERENCE" | etc,
        "snippet": "relevant text",
        "reasoning": "why this suggests allergen",
        "confidence": float  // 0.0-1.0
      }
    ],
    // ... for each allergen with evidence
  },
  "safe_for": ["vegan", "gluten-free", etc],  // dietary restrictions this dish accommodates
  "unsafe_for": ["vegan", "gluten-free", etc],  // dietary restrictions this violates
  "warnings": ["potential concerns"]
}

Be especially careful with:
- Hidden allergens (soy in oil, gluten in soy sauce)
- Cross-contamination risks
- Ambiguous descriptions
```

### 5.3 Confidence Calibration

After Claude returns probabilities, calibrate them:

```
Claude's raw probability → Calibrated probability

If explicit allergen note:
  Keep probability high (0.90-0.98)

If dish archetype match:
  Keep probability high (0.75-0.90)

If inference only:
  Lower probability (0.30-0.60)

If no evidence:
  Use cuisine prior

Always apply safety factor:
  If raw > 0.7, keep it
  If raw 0.4-0.7, round up to 0.5
  If raw < 0.4, keep as-is or round to cuisine prior
```

---

## 6. Helper Functions to Create

### 6.1 Menu Item Parser Helper
**Function:** `_parse_menu_items(menu_text: str, restaurant_name: str, cuisine: str) -> List[MenuItem]`

**Purpose:** Extract structured menu items from OCR text

**Should:**
- Use Claude to parse menu into items
- Extract dish names, descriptions, prices
- Identify menu sections (headers)
- Group related text (item + description + price)
- Handle multi-line descriptions

**Returns:** List of MenuItem objects

### 6.2 Ingredient Identifier Helper
**Function:** `_identify_ingredients(dish_description: str) -> List[str]`

**Purpose:** Extract ingredient mentions from text

**Should use:**
- Ingredient keyword dictionary
- Claude for semantic understanding
- Common food words database

**Examples:**
```
"topped with cheese" → ['cheese']
"made with butter and cream" → ['butter', 'cream']
"contains: wheat, dairy, soy" → ['wheat', 'dairy', 'soy']
```

**Returns:** List of ingredient strings

### 6.3 Allergen Mapper Helper
**Function:** `_map_ingredient_to_allergens(ingredient: str) -> Dict[AllergenType, float]`

**Purpose:** Map ingredient to allergen probabilities

**Should use mapping database:**
```python
INGREDIENT_ALLERGEN_MAP = {
    'wheat': {'GLUTEN': 1.0},
    'flour': {'GLUTEN': 0.95},  # Could be gluten-free flour
    'bread': {'GLUTEN': 0.98},
    'pasta': {'GLUTEN': 0.95, 'EGGS': 0.40},
    'soy sauce': {'SOY': 0.98, 'GLUTEN': 0.85},  # Most soy sauce has wheat
    'cheese': {'DAIRY': 0.98},
    'milk': {'DAIRY': 1.0},
    'butter': {'DAIRY': 0.98},
    'cream': {'DAIRY': 0.98},
    'eggs': {'EGGS': 1.0},
    'mayo': {'EGGS': 0.95, 'SOY': 0.30},
    'mayonnaise': {'EGGS': 0.95, 'SOY': 0.30},
    'peanuts': {'PEANUTS': 1.0},
    'peanut butter': {'PEANUTS': 1.0},
    'almonds': {'TREE_NUTS': 1.0},
    'walnuts': {'TREE_NUTS': 1.0},
    'cashews': {'TREE_NUTS': 1.0},
    'shrimp': {'SHELLFISH': 1.0},
    'crab': {'SHELLFISH': 1.0},
    'lobster': {'SHELLFISH': 1.0},
    'fish': {'FISH': 1.0},
    'salmon': {'FISH': 1.0},
    'tuna': {'FISH': 1.0},
    'tofu': {'SOY': 0.98},
    'soybean oil': {'SOY': 0.90},
    'vegetable oil': {'SOY': 0.70},  // Often soy-based
    'fried': {'SOY': 0.60},  # Assumption: fried in soy oil
    'breaded': {'GLUTEN': 0.90, 'EGGS': 0.50},
    'battered': {'GLUTEN': 0.92, 'EGGS': 0.45},
    'sesame': {'SESAME': 1.0},
    'tahini': {'SESAME': 0.98}
    # ... extensive mapping
}
```

**Returns:** Dict of {AllergenType: probability}

### 6.4 Dish Analyzer Helper
**Function:** `_analyze_dish(menu_item: MenuItem, cuisine: str) -> DishAllergenProfile`

**Purpose:** Complete allergen analysis for one dish

**Should:**
- Call Claude for semantic analysis
- Map identified ingredients to allergens
- Apply cuisine priors
- Combine evidence from multiple sources
- Calculate final probabilities
- Generate evidence objects
- Classify safe/unsafe for diets

**Returns:** DishAllergenProfile object

### 6.5 Probability Calculator Helper
**Function:** `_calculate_allergen_probability(dish: MenuItem, allergen: AllergenType, evidence_list: List, cuisine_prior: float) -> float`

**Purpose:** Calculate final probability for one allergen

**Should:**
- Combine evidence probabilities
- Apply cuisine prior as baseline
- Use maximum probability (conservative)
- Cap at 0.98 (never 100% certain without lab test)
- Floor at 0.01 (never 0% in shared kitchen)

**Formula:**
```
If explicit_evidence exists:
  P = max(evidence_probabilities)
Else:
  P = cuisine_prior

# Safety adjustments
P = max(P, 0.01)  # Minimum for cross-contamination
P = min(P, 0.98)  # Maximum for uncertainty
```

**Returns:** Probability float (0.0-1.0)

### 6.6 Cuisine Prior Applier Helper
**Function:** `_apply_cuisine_priors(allergen_probs: Dict, cuisine: str) -> Dict`

**Purpose:** Adjust probabilities using cuisine context

**Should:**
- Look up cuisine in CUISINE_PRIORS database
- For allergens without explicit evidence, use prior
- For allergens with weak evidence, blend with prior
- For allergens with strong evidence, keep explicit value

**Logic:**
```
For each allergen:
  If explicit_evidence and confidence > 0.7:
    Keep explicit probability
  Elif weak_evidence (confidence 0.3-0.7):
    Blend: 0.7 * explicit + 0.3 * cuisine_prior
  Else (no evidence):
    Use cuisine_prior
```

**Returns:** Adjusted allergen probability dict

### 6.7 Evidence Generator Helper
**Function:** `_generate_evidence(allergen: AllergenType, dish: MenuItem, probability: float, cuisine: str) -> List[AllergenEvidence]`

**Purpose:** Create evidence objects supporting allergen claim

**Should generate evidence for:**
- Explicit ingredient mentions
- Dish archetype matches
- Cuisine priors
- Cooking methods
- Inferences

**Returns:** List of AllergenEvidence objects

### 6.8 Venue Aggregator Helper
**Function:** `_aggregate_venue_summary(dish_profiles: List[DishAllergenProfile]) -> VenueAllergenSummary`

**Purpose:** Create venue-wide allergen summary

**Should calculate:**
- Prevalence: % of dishes with each allergen
- Statistics: count, percentage, average probability
- Safest dishes: dishes with fewest/lowest allergens
- Highest risk dishes: dishes with most/highest allergens
- General warnings: venue-wide concerns

**Returns:** VenueAllergenSummary object

### 6.9 Confidence Calculator Helper
**Function:** `_calculate_confidence(dish_profile: DishAllergenProfile, ocr_confidence: float) -> float`

**Purpose:** Score overall analysis reliability

**Should consider:**
- OCR quality (higher OCR confidence → higher analysis confidence)
- Evidence strength (explicit notes → higher confidence)
- Dish clarity (clear description → higher confidence)
- Ambiguity level (vague descriptions → lower confidence)

**Formula:**
```
confidence = (
    0.3 * ocr_confidence +
    0.4 * average_evidence_confidence +
    0.2 * description_clarity_score +
    0.1 * (1 - ambiguity_score)
)
```

**Returns:** Confidence score (0.0-1.0)

### 6.10 Safety Classifier Helper
**Function:** `_classify_safety(allergen_probs: Dict) -> Tuple[List[str], List[str]]`

**Purpose:** Determine which diets dish is safe/unsafe for

**Logic:**
```
safe_for = []
unsafe_for = []

If DAIRY < 0.1 and EGGS < 0.1:
  safe_for.append('vegan')
Else:
  unsafe_for.append('vegan')

If GLUTEN < 0.1:
  safe_for.append('gluten-free')
Else:
  unsafe_for.append('gluten-free')

If DAIRY < 0.1:
  safe_for.append('dairy-free')

If PEANUTS < 0.1 and TREE_NUTS < 0.1:
  safe_for.append('nut-free')

# etc for other dietary restrictions
```

**Returns:** (safe_for, unsafe_for) lists

### 6.11 Cache Management Helpers

**Function:** `_generate_cache_key(restaurant_id: str) -> str`

**Format:** `allergen:{restaurant_id}`

**Function:** `_get_from_cache(cache_key: str) -> Optional[AllergenAnalysisResult]`

**Should validate cache age** (< 14 days)

**Function:** `_save_to_cache(cache_key: str, result: AllergenAnalysisResult, ttl: int = 1209600)`

---

## 7. Integration Guardrails

### 7.1 Input Validation
Before analysis:
- ✅ Validate menu_text is non-empty
- ✅ Validate restaurant_id exists
- ✅ Validate OCR confidence is reasonable (> 0.5)
- ✅ Warn if OCR confidence very low (< 0.7)

### 7.2 Output Contract Compliance
MUST return exact format expected by Safety & QA:
- ✅ All 11 allergens have probabilities (even if 0.0)
- ✅ Evidence provided for allergens > 0.3 probability
- ✅ Each evidence has all required fields
- ✅ Confidence scores are 0.0-1.0
- ✅ safe_for and unsafe_for lists populated
- ✅ Venue summary aggregates all dishes

### 7.3 Safety-Critical Requirements
**CRITICAL - This agent affects user health:**

```
1. Conservative Estimation:
   - When uncertain, assume allergen IS present
   - Better to warn unnecessarily than miss danger
   - Minimum probability 0.01 (cross-contamination always possible)

2. Evidence Required:
   - Never return probability > 0.5 without evidence
   - Always cite source text for high probabilities
   - Explain reasoning clearly

3. Explicit Warnings:
   - Flag low confidence results
   - Warn about missing menu data
   - Note cross-contamination risks
   - Explain limitations

4. No False Negatives:
   - If explicit allergen note says "contains X", probability must be > 0.85
   - If dish archetype strongly suggests allergen, probability > 0.75
   - Never return 0.0 for known allergens

5. Transparency:
   - Always show evidence
   - Always explain reasoning
   - Always provide confidence scores
   - Never hide uncertainty
```

### 7.4 Error Handling
```
Critical Errors (fail analysis):
- No menu text provided
- Menu text completely unparseable
- Claude API unavailable

Recoverable Errors (partial analysis):
- Some dishes unclear → analyze clear ones
- Low OCR confidence → proceed but flag
- Missing cuisine → use default priors

Non-Fatal Warnings:
- Ambiguous descriptions → lower confidence
- No explicit allergen notes → rely on inference
- Limited menu → note incomplete analysis
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test: Ingredient to Allergen Mapping**
```
Input: "cheese"
Expected: {'DAIRY': 0.98}

Input: "soy sauce"
Expected: {'SOY': 0.98, 'GLUTEN': 0.85}

Input: "vegetable oil"
Expected: {'SOY': 0.70}  # Often soybean oil
```

**Test: Cuisine Prior Application**
```
Cuisine: "italian"
Allergen: GLUTEN
Expected: Prior = 0.85

Cuisine: "japanese"
Allergen: SOY
Expected: Prior = 0.90
```

**Test: Probability Combination**
```
Evidence: [0.98 (explicit), 0.75 (archetype), 0.50 (prior)]
Method: Maximum
Expected: 0.98
```

**Test: Safety Classification**
```
Allergen_probs: {DAIRY: 0.05, EGGS: 0.03, ...}
Expected: safe_for = ['vegan', 'dairy-free']

Allergen_probs: {DAIRY: 0.95, ...}
Expected: unsafe_for = ['vegan', 'dairy-free']
```

### 8.2 Integration Tests

**Test: End-to-End Analysis**
```
Input: Menu with "Cheeseburger - Contains: wheat, dairy"
Verify:
- GLUTEN probability > 0.9
- DAIRY probability > 0.9
- Evidence cites "Contains: wheat, dairy"
- unsafe_for includes 'vegan', 'gluten-free'
```

**Test: Multi-Dish Aggregation**
```
Input: 4 dishes, 3 with gluten
Verify:
- Venue prevalence GLUTEN = 0.75
- Stats show 3/4 dishes
- General warning about high gluten prevalence
```

**Test: Ambiguous Dish Handling**
```
Input: "Special Sauce" (no ingredients listed)
Verify:
- Probability based on cuisine prior
- Low confidence score
- Warning about missing ingredient info
```

**Test: Explicit Allergen Note**
```
Input: "Contains: peanuts"
Verify:
- PEANUTS probability > 0.95
- Evidence type = ALLERGEN_NOTE
- High confidence
```

### 8.3 Safety Tests

**Test: Conservative Estimation**
```
Input: Ambiguous dish "sauce" (could have soy)
Expected: SOY probability >= cuisine prior, not 0.0
```

**Test: No False Negatives**
```
Input: "made with butter"
Expected: DAIRY probability > 0.85, never < 0.5
```

**Test: Cross-Contamination Baseline**
```
Input: Any dish, any allergen
Expected: Minimum probability 0.01 (cross-contam possible)
```

**Test: Explicit Override**
```
Input: "gluten-free pasta"
Expected: GLUTEN probability < 0.2, notes "gluten-free claim"
```

---

## 9. Example Analysis Flows

### Example 1: Clear Allergen Notes
```
Input:
Menu text: "Cheeseburger - $10.99\nClassic burger with cheese\nContains: wheat, dairy, soy"

Processing:
1. Parse menu: 1 item found
2. Identify ingredients: [wheat, dairy, soy, cheese]
3. Map to allergens:
   - wheat → GLUTEN: 1.0
   - dairy → DAIRY: 1.0
   - soy → SOY: 1.0
   - cheese → DAIRY: 0.98
4. Generate evidence:
   - GLUTEN: ALLERGEN_NOTE "Contains: wheat" (0.98)
   - DAIRY: ALLERGEN_NOTE "Contains: dairy" (0.95)
   - SOY: ALLERGEN_NOTE "Contains: soy" (0.85)
5. Calculate probabilities:
   - GLUTEN: max(1.0, 0.98) = 0.98 (capped)
   - DAIRY: max(1.0, 0.98, 0.95) = 0.98
   - SOY: 0.85
6. Apply cuisine priors: Minimal adjustment (explicit evidence strong)
7. Classify safety: unsafe_for = ['vegan', 'gluten-free', 'dairy-free']
8. Confidence: 0.95 (explicit notes, clear description)

Output:
{
  'dish_name': 'Cheeseburger',
  'allergen_probabilities': {
    'GLUTEN': 0.98,
    'DAIRY': 0.98,
    'SOY': 0.85,
    'EGGS': 0.15,
    'PEANUTS': 0.02,
    ...
  },
  'evidence': {
    'GLUTEN': [{
      'evidence_type': 'ALLERGEN_NOTE',
      'snippet': 'Contains: wheat',
      'reasoning': 'Explicit allergen declaration',
      'confidence': 0.98
    }],
    ...
  },
  'confidence': 0.95,
  'unsafe_for': ['vegan', 'gluten-free', 'dairy-free']
}
```

### Example 2: Ambiguous Description
```
Input:
Menu text: "Chef's Special Pasta - $18.99\nOur signature dish"

Processing:
1. Parse: 1 item found
2. Identify ingredients: [pasta] (only generic mention)
3. Map to allergens:
   - pasta → GLUTEN: 0.95, EGGS: 0.40
4. Apply cuisine priors (Italian):
   - GLUTEN: max(0.95, italian_prior_0.85) = 0.95
   - DAIRY: italian_prior_0.75 (no evidence, use prior)
   - EGGS: max(0.40, italian_prior_0.40) = 0.40
5. Generate evidence:
   - GLUTEN: DISH_ARCHETYPE "pasta" (0.75)
   - DAIRY: CUISINE_PRIOR "Italian cuisine commonly uses dairy" (0.50)
6. Classify safety: unsafe_for = ['vegan', 'gluten-free']
7. Confidence: 0.62 (ambiguous description, no explicit notes)

Output:
{
  'dish_name': "Chef's Special Pasta",
  'allergen_probabilities': {
    'GLUTEN': 0.95,
    'DAIRY': 0.75,
    'EGGS': 0.40,
    ...
  },
  'evidence': {
    'GLUTEN': [{
      'evidence_type': 'DISH_ARCHETYPE',
      'snippet': 'pasta',
      'reasoning': 'Pasta traditionally made with wheat flour',
      'confidence': 0.75
    }],
    'DAIRY': [{
      'evidence_type': 'CUISINE_PRIOR',
      'snippet': 'Italian cuisine',
      'reasoning': 'Italian dishes commonly include cheese and cream',
      'confidence': 0.50
    }]
  },
  'confidence': 0.62,
  'warnings': [
    'Limited ingredient information - probabilities based on dish type and cuisine',
    'No explicit allergen declarations found'
  ],
  'unsafe_for': ['vegan', 'gluten-free']
}
```

### Example 3: Vegan Restaurant
```
Input:
Restaurant: "Green Leaf Vegan Bistro"
Cuisine: "vegan"
Menu text: "Tofu Scramble - $12.99\nTofu, vegetables, herbs"

Processing:
1. Parse: 1 item found
2. Identify ingredients: [tofu, vegetables, herbs]
3. Map to allergens:
   - tofu → SOY: 0.98
4. Apply cuisine priors (vegan):
   - DAIRY: vegan_prior_0.01 (very low)
   - EGGS: vegan_prior_0.01
   - SOY: max(0.98, vegan_prior_0.75) = 0.98
5. Classify safety: safe_for = ['vegan', 'dairy-free']
6. Confidence: 0.88

Output:
{
  'dish_name': 'Tofu Scramble',
  'allergen_probabilities': {
    'SOY': 0.98,
    'GLUTEN': 0.50,  # Could be in seasoning
    'DAIRY': 0.01,
    'EGGS': 0.01,
    ...
  },
  'safe_for': ['vegan', 'dairy-free'],
  'unsafe_for': [],
  'warnings': []
}
```

### Example 4: Venue Aggregation
```
Input: 4 dishes analyzed

Dish 1: GLUTEN=0.98, DAIRY=0.95
Dish 2: GLUTEN=0.95, DAIRY=0.05
Dish 3: GLUTEN=0.92, SOY=0.90
Dish 4: GLUTEN=0.10, SOY=0.85

Processing:
1. Count dishes with allergen > 0.5:
   - GLUTEN: 3/4 = 75%
   - DAIRY: 1/4 = 25%
   - SOY: 2/4 = 50%
2. Calculate average probability:
   - GLUTEN: (0.98+0.95+0.92+0.10)/4 = 0.74
   - SOY: (0.0+0.0+0.90+0.85)/4 = 0.44
3. Identify safest: Dish 4 (lowest total allergen load)
4. Identify riskiest: Dish 1 (highest total allergen load)
5. Generate warnings:
   - "High prevalence of gluten (75% of dishes)"

Output:
{
  'venue_summary': {
    'allergen_prevalence': {
      'GLUTEN': 0.75,
      'DAIRY': 0.25,
      'SOY': 0.50
    },
    'safest_dishes': ['Dish 4'],
    'highest_risk_dishes': ['Dish 1'],
    'general_warnings': [
      'High prevalence of gluten (75% of dishes)',
      'Cross-contamination possible in shared kitchen'
    ]
  }
}
```

---

## 10. Common Pitfalls to Avoid

1. **❌ Don't return 0.0 for known allergens**
   - Always minimum 0.01 for cross-contamination
   - If dish archetype strongly suggests allergen, use > 0.5

2. **❌ Don't trust OCR blindly**
   - OCR can misread "wheat" as "what"
   - Use context and Claude for validation
   - Flag low OCR confidence

3. **❌ Don't ignore hidden allergens**
   - Soy oil in fried foods
   - Wheat in soy sauce
   - Dairy in battered items

4. **❌ Don't skip cuisine priors**
   - They provide important context
   - Use as baseline when no explicit evidence
   - Adjust probabilities, don't override

5. **❌ Don't be overconfident**
   - Never 100% certain without lab test
   - Cap probabilities at 0.98
   - Always provide confidence scores

6. **❌ Don't forget evidence**
   - Every claim needs supporting evidence
   - Cite specific menu text
   - Explain reasoning

7. **❌ Don't ignore ambiguity**
   - Flag unclear descriptions
   - Lower confidence for vague items
   - Warn user about limitations

8. **❌ Don't misclassify safety**
   - "vegetarian" ≠ "vegan"
   - "gluten-free" needs verification
   - Don't assume claims without evidence

9. **❌ Don't skip venue aggregation**
   - Users need venue-wide view
   - Helps identify pattern risks
   - Supports informed decision-making

10. **❌ Don't compromise on safety**
    - This is health-critical
    - Conservative > accurate
    - Transparent > complete

---

## 11. Success Criteria

The Allergen Analyzer Agent is complete when it:
- ✅ Correctly identifies allergens in 90%+ of clear cases
- ✅ Provides evidence for all allergen claims > 0.5 probability
- ✅ Never misses explicit allergen declarations
- ✅ Applies cuisine priors appropriately
- ✅ Returns conservative estimates (better safe than sorry)
- ✅ Completes analysis in <3 seconds per dish
- ✅ Handles ambiguous menus with appropriate warnings
- ✅ Aggregates venue-level summaries correctly
- ✅ Returns output in exact contract format
- ✅ Passes all safety-critical tests
- ✅ Provides clear confidence scores

---

## 12. Integration Checklist

Before marking complete, verify:
- [ ] Receives OCR text from OCR Worker
- [ ] Parses menu items accurately (90%+ recall)
- [ ] Maps ingredients to allergens correctly
- [ ] Applies cuisine priors appropriately
- [ ] Generates evidence for all claims
- [ ] Calculates conservative probabilities
- [ ] Aggregates venue summaries correctly
- [ ] Returns exact output format to Safety & QA
- [ ] Caches results properly
- [ ] Handles missing/ambiguous data gracefully
- [ ] Tests cover safety-critical scenarios
- [ ] Documentation includes confidence guidelines

---

## 13. Next Steps

Once Allergen Analyzer Agent is complete:
1. Test with 100 diverse menus (various cuisines, clarity levels)
2. Validate allergen detection accuracy (compare to known ground truth)
3. Tune cuisine priors based on real data
4. Calibrate confidence scores with user feedback
5. Test integration with OCR Worker and Safety & QA

Then proceed to: **Review Enricher Agent** or **Safety & QA Agent**

Recommended: Build **Safety & QA Agent** next since it validates allergen claims before showing to users.

---

**CRITICAL SAFETY REMINDER:** This agent's output directly affects user health decisions. When implementing:

1. **Test extensively** with known allergen cases
2. **Never skip evidence** - always cite sources
3. **Be conservative** - false positive > false negative
4. **Flag uncertainty** - clear confidence scores and warnings
5. **Document limitations** - users must understand what analysis can/cannot do

Better to tell a user "we found gluten with 60% confidence" than to say "no gluten detected" when there might be gluten. Lives depend on getting this right.