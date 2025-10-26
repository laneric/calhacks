# PROMPT 8: Safety & QA Agent Implementation Guide

## Context
You are building the **Safety & QA Agent**, which validates all data before it reaches users. This is the **final quality gate** that prevents incorrect, unsafe, or low-quality information from being displayed. This agent is particularly critical for allergen data, where errors could harm users.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- LLM: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) for validation reasoning
- Backend: Flask API
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The Safety & QA Agent must:
1. **Validate allergen claims** - Check allergen probabilities are reasonable and evidence-backed
2. **Check data consistency** - Ensure data from different sources doesn't contradict
3. **Verify scraping compliance** - Confirm no robots.txt violations or rate limit abuse
4. **Flag low confidence** - Warn users when data quality is poor
5. **Detect contradictions** - Find conflicting information across sources
6. **Validate source credibility** - Ensure data comes from reliable sources
7. **Check completeness** - Flag missing critical data
8. **Generate user warnings** - Create clear, actionable warnings for users
9. **Block unsafe data** - Prevent dangerous allergen misclassifications
10. **Ensure output compliance** - Validate final payload matches contract

**CRITICAL PRINCIPLE:** When in doubt, BLOCK the data or add prominent warnings. Better to show nothing than to show dangerous misinformation.

---

## 2. File Structure

**Create:** `agents/safety_qa_agent.py`

This file should contain:

### 2.1 Validation Status Enum
Define validation outcomes:
- `PASS` - Data is safe and high quality
- `PASS_WITH_WARNINGS` - Data acceptable but has concerns
- `BLOCKED` - Data unsafe or unreliable, do not show
- `NEEDS_REVIEW` - Ambiguous, requires human review

### 2.2 Issue Severity Enum
Define severity levels:
- `CRITICAL` - Safety risk, blocks data
- `HIGH` - Quality concern, prominent warning
- `MEDIUM` - Minor issue, subtle warning
- `LOW` - Informational only
- `INFO` - Not an issue, just FYI

### 2.3 Issue Category Enum
Define types of issues:
- `ALLERGEN_SAFETY` - Allergen data concerns
- `DATA_CONSISTENCY` - Contradictions between sources
- `SCRAPING_COMPLIANCE` - Robots.txt or rate limit violations
- `SOURCE_CREDIBILITY` - Questionable data sources
- `CONFIDENCE` - Low confidence scores
- `COMPLETENESS` - Missing critical data
- `OUTPUT_FORMAT` - Contract violations

### 2.4 Core Classes

**ValidationRequest Class:**
Represents a validation job. Should include:
- `restaurant_id`: str
- `enrichment_data`: Dict - From Data Enrichment Agent
- `allergen_data`: Dict - From Allergen Analyzer Agent
- `ranking_data`: Dict - From Ranker Agent
- `menu_data`: Dict - From Menu Finder Agent
- `ocr_data`: Dict - From OCR Worker Agent
- `scraping_metadata`: Dict - robots.txt checks, rate limits
- `user_query`: str - Original user query

**ValidationIssue Class:**
Represents a found issue. Should include:
- `severity`: IssueSeverity
- `category`: IssueCategory
- `message`: str - User-facing description
- `technical_detail`: str - For logging/debugging
- `affected_field`: str - Which data field has issue
- `suggested_action`: Optional[str] - How to fix or what to do
- `source_agent`: str - Which agent produced problematic data

**ValidationResult Class:**
Complete validation outcome. Should include:
- `status`: ValidationStatus - Overall status
- `issues`: List[ValidationIssue] - All issues found
- `critical_issues`: List[ValidationIssue] - Blocking issues
- `warnings`: List[ValidationIssue] - Non-blocking concerns
- `data_quality_score`: float - 0.0-1.0 overall quality
- `allergen_safety_score`: float - 0.0-1.0 allergen reliability
- `user_warnings`: List[str] - Warnings to display to user
- `blocked_data`: Dict - Data that was removed/blocked
- `passed_data`: Dict - Data that passed validation
- `metadata`: Dict - Validation details

**SafetyQAAgent Class:**
Main agent implementation. Should include methods:
- `__init__()` - Initialize validators
- `validate()` - Main entry point
- `_validate_allergen_safety()` - Check allergen data
- `_validate_data_consistency()` - Check for contradictions
- `_validate_scraping_compliance()` - Check scraping rules
- `_validate_source_credibility()` - Check data sources
- `_validate_confidence_levels()` - Check confidence scores
- `_validate_completeness()` - Check for missing data
- `_validate_output_format()` - Check contract compliance
- `_generate_user_warnings()` - Create user-facing messages
- `_calculate_quality_scores()` - Score data quality
- `_block_unsafe_data()` - Remove dangerous data
- `_resolve_contradictions()` - Choose between conflicting data

---

## 3. Input/Output Contracts

### 3.1 Input Format (from Planner Agent)
Receives validation requests with ALL agent outputs:
```python
{
    'restaurant_id': 'rest_123',
    
    # From Data Enrichment Agent
    'enrichment_data': {
        'name': 'Super Duper Burger',
        'rating': 4.3,
        'rating_sources': ['google', 'yelp'],
        'review_count': 1542,
        'website': 'https://superduperburger.com',
        'phone': '+1-510-555-1234',
        'enrichment_confidence': 0.89
    },
    
    # From Allergen Analyzer Agent
    'allergen_data': {
        'overall_confidence': 0.87,
        'venue_summary': {
            'allergen_prevalence': {
                'GLUTEN': 0.75,
                'DAIRY': 0.50,
                'SOY': 0.80
            }
        },
        'by_dish': [
            {
                'dish_name': 'Super Duper Burger',
                'allergen_probabilities': {
                    'GLUTEN': 0.98,
                    'DAIRY': 0.95
                },
                'evidence': {
                    'GLUTEN': [{
                        'evidence_type': 'ALLERGEN_NOTE',
                        'snippet': 'Contains: wheat',
                        'confidence_contribution': 0.98
                    }]
                },
                'confidence': 0.92
            }
        ]
    },
    
    # From Ranker Agent
    'ranking_data': {
        'ranked_results': [...],
        'ranking_strategy': 'hybrid',
        'filters_applied': {...}
    },
    
    # From Menu Finder Agent
    'menu_data': {
        'menu_text_urls': [...],
        'confidence': 0.88
    },
    
    # From OCR Worker Agent
    'ocr_data': {
        'results': [...],
        'average_confidence': 0.91
    },
    
    # Scraping metadata
    'scraping_metadata': {
        'robots_txt_violations': [],
        'rate_limit_hits': 0,
        'blocked_domains': [],
        'sources_checked': ['google', 'yelp', 'website']
    },
    
    # User context
    'user_query': 'vegan burger near me'
}
```

### 3.2 Output Format (to Frontend)
Must return validation results:
```python
{
    'status': 'PASS' | 'PASS_WITH_WARNINGS' | 'BLOCKED' | 'NEEDS_REVIEW',
    
    'issues': [
        {
            'severity': 'CRITICAL',
            'category': 'ALLERGEN_SAFETY',
            'message': 'Allergen data has low confidence (0.65) due to poor OCR quality',
            'technical_detail': 'OCR confidence 0.62, only 1 menu found, no explicit allergen notes',
            'affected_field': 'allergen_data.by_dish[0].confidence',
            'suggested_action': 'Request manual menu verification',
            'source_agent': 'allergen_analyzer'
        },
        {
            'severity': 'HIGH',
            'category': 'DATA_CONSISTENCY',
            'message': 'Rating varies significantly across sources',
            'technical_detail': 'Google: 4.5, Yelp: 3.8 (0.7 difference)',
            'affected_field': 'enrichment_data.rating',
            'suggested_action': 'Display rating range to user',
            'source_agent': 'data_enrichment'
        },
        {
            'severity': 'MEDIUM',
            'category': 'COMPLETENESS',
            'message': 'No menu found for allergen analysis',
            'technical_detail': 'Menu Finder returned 0 menu URLs',
            'affected_field': 'menu_data.menu_text_urls',
            'suggested_action': 'Recommend calling restaurant to verify allergens',
            'source_agent': 'menu_finder'
        }
    ],
    
    'critical_issues': [
        {/* issues with severity=CRITICAL */}
    ],
    
    'warnings': [
        {/* issues with severity=HIGH or MEDIUM */}
    ],
    
    'data_quality_score': 0.78,  // Overall quality (0.0-1.0)
    'allergen_safety_score': 0.65,  // Allergen reliability (0.0-1.0)
    
    'user_warnings': [
        '⚠️ Allergen data has lower confidence due to limited menu information',
        '⚠️ Ratings vary across sources (3.8-4.5) - some reviews may be older',
        'ℹ️ No menu found online - call restaurant to verify allergen safety'
    ],
    
    'blocked_data': {
        'allergen_claims': [
            {
                'dish': 'Mystery Special',
                'reason': 'No ingredients found, confidence < 0.3',
                'original_data': {...}
            }
        ],
        'reviews': [],
        'images': []
    },
    
    'passed_data': {
        'enrichment_data': {/* cleaned data */},
        'allergen_data': {/* cleaned data */},
        'ranking_data': {/* cleaned data */}
    },
    
    'metadata': {
        'validation_time_ms': 234,
        'total_issues': 3,
        'critical_issues': 1,
        'warnings': 2,
        'data_blocked': True,
        'scraping_compliant': True,
        'allergen_validation_passed': False
    }
}
```

---

## 4. Validation Rules and Thresholds

### 4.1 Allergen Safety Validation

**CRITICAL Checks (block if fail):**
```
1. Allergen claims without evidence:
   ❌ BLOCK if probability > 0.5 but no evidence
   Reason: Unsafe to claim allergen without basis

2. Extremely low OCR confidence:
   ❌ BLOCK if OCR confidence < 0.5
   Reason: Text likely misread, allergen data unreliable

3. Contradictory allergen notes:
   ❌ BLOCK if menu says "gluten-free" but GLUTEN=0.9
   Reason: Direct contradiction, unsafe

4. Missing evidence for high claims:
   ❌ BLOCK if ALLERGEN probability > 0.8 but confidence < 0.6
   Reason: High certainty without strong evidence suspicious

5. Impossible allergen combinations:
   ❌ BLOCK if dish="vegan burger" but DAIRY=0.95 without override evidence
   Reason: Logical contradiction
```

**HIGH Warnings (warn but allow):**
```
1. Low allergen confidence:
   ⚠️ WARN if overall allergen confidence < 0.7
   Message: "Allergen data has lower confidence due to limited information"

2. Cuisine priors only:
   ⚠️ WARN if allergen probability based only on cuisine, no menu evidence
   Message: "Allergen estimates based on typical cuisine - verify with restaurant"

3. No menu found:
   ⚠️ WARN if menu_data.total_found = 0
   Message: "No menu found online - call restaurant to verify allergen safety"

4. Partial menu coverage:
   ⚠️ WARN if only 1-2 menu items found but venue has many dishes
   Message: "Limited menu coverage - allergen data may be incomplete"

5. OCR issues:
   ⚠️ WARN if OCR confidence 0.5-0.7
   Message: "Menu text quality was lower - allergen detection may be less accurate"
```

**MEDIUM Warnings (informational):**
```
1. Single source allergen data:
   ℹ️ INFO if only 1 menu source used
   Message: "Allergen data from single menu source"

2. Old data:
   ℹ️ INFO if cache age > 7 days
   Message: "Menu data may be outdated - verify current offerings"

3. Missing allergen notes:
   ℹ️ INFO if no explicit allergen declarations in menu
   Message: "No allergen declarations found - estimates based on ingredients"
```

### 4.2 Data Consistency Validation

**HIGH Issues (prominent warning):**
```
1. Large rating discrepancy:
   ⚠️ WARN if max(ratings) - min(ratings) > 0.5
   Action: Show rating range to user

2. Review count mismatch:
   ⚠️ WARN if counts differ by >30%
   Action: Show range or note discrepancy

3. Conflicting hours:
   ⚠️ WARN if sources disagree on open/closed
   Action: Show "hours may vary, call to confirm"

4. Phone number mismatch:
   ⚠️ WARN if multiple phone numbers found
   Action: Show all numbers

5. Contradictory cuisine types:
   ⚠️ WARN if sources label different cuisines
   Action: Show multiple cuisine tags
```

**Resolution Strategy:**
```
When data conflicts:
1. Prefer official website over aggregators
2. Prefer verified sources (Google Business) over user-submitted
3. Use most recent data
4. Show range/multiple values to user
5. Note discrepancy in warning
```

### 4.3 Scraping Compliance Validation

**CRITICAL Issues (block entire request):**
```
1. robots.txt violations:
   ❌ BLOCK if any robots_txt_violations > 0
   Reason: Legal/ethical violation
   Action: Log error, don't use that data source

2. Rate limit abuse:
   ❌ BLOCK if rate_limit_hits > 5
   Reason: Abusive behavior
   Action: Throttle requests, temporary ban domain

3. Blocked domains accessed:
   ❌ BLOCK if blocked_domains list not empty
   Reason: Violates restrictions
   Action: Remove data from blocked domains
```

### 4.4 Source Credibility Validation

**HIGH Issues:**
```
1. No verified sources:
   ⚠️ WARN if all sources are unverified (scraped pages, not APIs)
   Message: "Data from web scraping - may be less reliable"

2. Single source only:
   ⚠️ WARN if enrichment_data.sources.length = 1
   Message: "Limited data sources - cross-reference recommended"

3. Low enrichment confidence:
   ⚠️ WARN if enrichment_confidence < 0.7
   Message: "Restaurant data has lower confidence"

4. Social media only:
   ⚠️ WARN if only Instagram/Facebook used for menus
   Message: "Menu from social media - may not be current"
```

### 4.5 Confidence Level Validation

**Thresholds:**
```
EXCELLENT: >= 0.9
GOOD: 0.7-0.89
FAIR: 0.5-0.69
POOR: 0.3-0.49
UNACCEPTABLE: < 0.3

Actions:
- EXCELLENT: Pass without warnings
- GOOD: Pass, maybe add minor info note
- FAIR: Pass with warning about lower confidence
- POOR: Pass with prominent warning
- UNACCEPTABLE: BLOCK data, too unreliable
```

### 4.6 Completeness Validation

**MEDIUM Issues:**
```
1. Missing restaurant name:
   ⚠️ WARN if name is null/empty
   Action: Try to use address as identifier

2. Missing contact info:
   ℹ️ INFO if phone and website both missing
   Message: "No contact information found"

3. Missing ratings:
   ℹ️ INFO if rating is null
   Message: "No ratings available"

4. Missing menu:
   ⚠️ WARN if menu_data.total_found = 0
   Message: "No menu found - allergen data unavailable"

5. Incomplete menu parse:
   ℹ️ INFO if ocr_data.results < expected_pages
   Message: "Partial menu coverage"
```

---

## 5. Helper Functions to Create

### 5.1 Allergen Safety Validator Helper
**Function:** `_validate_allergen_safety(allergen_data: Dict, ocr_data: Dict, menu_data: Dict) -> List[ValidationIssue]`

**Purpose:** Check allergen data for safety concerns

**Should check:**
- Allergen claims have supporting evidence
- OCR confidence acceptable (> 0.5)
- No contradictions (e.g., "vegan" but high dairy)
- High probability claims have high confidence
- No impossible combinations

**Should generate:**
- CRITICAL issues for unsafe claims
- HIGH warnings for low confidence
- MEDIUM info for missing data

**Returns:** List of ValidationIssue objects

### 5.2 Data Consistency Checker Helper
**Function:** `_validate_data_consistency(enrichment_data: Dict) -> List[ValidationIssue]`

**Purpose:** Check for contradictions between sources

**Should check:**
- Rating discrepancies across sources
- Review count mismatches
- Phone number conflicts
- Hours conflicts
- Cuisine type conflicts

**Should resolve:**
- Use most credible source
- Show ranges for numeric conflicts
- Note discrepancies in warnings

**Returns:** List of ValidationIssue objects

### 5.3 Scraping Compliance Checker Helper
**Function:** `_validate_scraping_compliance(scraping_metadata: Dict) -> List[ValidationIssue]`

**Purpose:** Ensure scraping was legal/ethical

**Should check:**
- No robots.txt violations
- No rate limit abuse
- No blocked domain access
- Proper User-Agent used
- Crawl delays honored

**Should block:**
- Any data from violated sources
- Entire request if critical violations

**Returns:** List of ValidationIssue objects

### 5.4 Source Credibility Assessor Helper
**Function:** `_validate_source_credibility(enrichment_data: Dict, menu_data: Dict) -> List[ValidationIssue]`

**Purpose:** Check data source reliability

**Credibility ranking:**
```
Tier 1 (Highest):
- Official website (verified)
- Google Business API
- Yelp API

Tier 2 (Good):
- Official website (unverified)
- Major menu platforms (Toast, DoorDash)

Tier 3 (Fair):
- Social media (Instagram, Facebook)
- Review aggregators

Tier 4 (Low):
- Generic web scraping
- Unverified sources
```

**Should warn:**
- If only Tier 3-4 sources used
- If single source only
- If source has low historical accuracy

**Returns:** List of ValidationIssue objects

### 5.5 Confidence Level Validator Helper
**Function:** `_validate_confidence_levels(allergen_data: Dict, enrichment_data: Dict, ocr_data: Dict) -> List[ValidationIssue]`

**Purpose:** Check all confidence scores meet thresholds

**Should check:**
- Overall allergen confidence
- Per-dish allergen confidence
- OCR confidence
- Enrichment confidence
- Menu finding confidence

**Should flag:**
- Any confidence < 0.3 → BLOCK
- Any confidence 0.3-0.5 → HIGH warning
- Any confidence 0.5-0.7 → MEDIUM warning

**Returns:** List of ValidationIssue objects

### 5.6 Completeness Validator Helper
**Function:** `_validate_completeness(enrichment_data: Dict, allergen_data: Dict, menu_data: Dict) -> List[ValidationIssue]`

**Purpose:** Check for missing critical data

**Required fields:**
- restaurant_id
- restaurant_name
- At least one of: rating, reviews, website, phone

**Desired fields:**
- Menu URLs
- Allergen data (if dietary query)
- Contact information
- Hours

**Should generate:**
- MEDIUM warnings for missing desired fields
- INFO notes for missing optional fields

**Returns:** List of ValidationIssue objects

### 5.7 Output Format Validator Helper
**Function:** `_validate_output_format(passed_data: Dict) -> List[ValidationIssue]`

**Purpose:** Ensure data matches frontend contract

**Should check:**
- All required fields present
- Field types correct (str, int, float, etc.)
- Enum values valid
- Arrays not empty when required
- Nested objects have correct structure

**Should block:**
- Malformed data that would crash frontend
- Missing required fields

**Returns:** List of ValidationIssue objects

### 5.8 User Warning Generator Helper
**Function:** `_generate_user_warnings(issues: List[ValidationIssue]) -> List[str]`

**Purpose:** Create user-facing warning messages

**Should convert:**
- Technical validation issues → Plain English
- Multiple similar issues → Single concise warning
- Severity → Emoji/icon (⚠️ for HIGH, ℹ️ for INFO)

**Examples:**
```
Technical: "OCR confidence 0.62, below threshold 0.7"
User: "⚠️ Menu text quality was lower - allergen detection may be less accurate"

Technical: "Rating sources: Google=4.5, Yelp=3.8, diff=0.7"
User: "⚠️ Ratings vary across sources (3.8-4.5)"

Technical: "menu_data.total_found = 0"
User: "ℹ️ No menu found online - call restaurant to verify allergen safety"
```

**Returns:** List of user-friendly warning strings

### 5.9 Quality Score Calculator Helper
**Function:** `_calculate_quality_scores(issues: List[ValidationIssue], allergen_data: Dict, enrichment_data: Dict) -> Tuple[float, float]`

**Purpose:** Calculate overall quality scores

**data_quality_score formula:**
```
base_score = 1.0

For each CRITICAL issue:
  base_score -= 0.3

For each HIGH issue:
  base_score -= 0.1

For each MEDIUM issue:
  base_score -= 0.05

For each LOW issue:
  base_score -= 0.02

data_quality_score = max(0.0, base_score)
```

**allergen_safety_score formula:**
```
If no allergen data:
  return 0.0

base_score = allergen_data.overall_confidence

For each allergen-related CRITICAL issue:
  base_score -= 0.4

For each allergen-related HIGH issue:
  base_score -= 0.15

For each allergen-related MEDIUM issue:
  base_score -= 0.05

allergen_safety_score = max(0.0, base_score)
```

**Returns:** (data_quality_score, allergen_safety_score)

### 5.10 Data Blocker Helper
**Function:** `_block_unsafe_data(all_data: Dict, issues: List[ValidationIssue]) -> Tuple[Dict, Dict]`

**Purpose:** Remove dangerous/unreliable data

**Should remove:**
- Allergen claims with CRITICAL issues
- Dishes with confidence < 0.3
- Data from robots.txt violations
- Contradictory information without resolution

**Should keep:**
- High-confidence data even if some concerns
- Data with warnings (but flag them)

**Returns:** (passed_data, blocked_data)

### 5.11 Contradiction Resolver Helper
**Function:** `_resolve_contradictions(conflicting_data: List[Dict], source_credibility: Dict) -> Dict`

**Purpose:** Choose best data when sources conflict

**Resolution strategy:**
```
1. Prefer higher credibility tier
2. If same tier, prefer more recent data
3. If same recency, prefer verified sources
4. If still tied, show range/multiple values
5. Always note discrepancy in warnings
```

**Examples:**
```
Rating conflict: Google=4.5, Yelp=3.8
→ Use average: 4.15, show range in warning

Phone conflict: Website=555-1234, Google=555-5678
→ Show both, note discrepancy

Hours conflict: Google says open, website says closed
→ Show "Hours may vary", recommend calling
```

**Returns:** Resolved data dict

---

## 6. Integration Guardrails

### 6.1 Input Validation
Before validation:
- ✅ Validate restaurant_id present
- ✅ Validate at least one data source provided
- ✅ Validate data structures match expected schemas

### 6.2 Output Contract Compliance
MUST return exact format expected by Frontend:
- ✅ `status` is valid ValidationStatus
- ✅ All issues have required fields
- ✅ `user_warnings` are plain English
- ✅ `passed_data` matches frontend schema
- ✅ `blocked_data` explains what and why
- ✅ Scores are 0.0-1.0 range

### 6.3 Safety-First Principles
**CRITICAL - This agent is last line of defense:**

```
1. Block Before Warn:
   - If truly unsafe, BLOCK it
   - Don't just warn about critical safety issues

2. Transparency:
   - Always tell user what's missing/uncertain
   - Never hide data quality issues

3. Conservative Thresholds:
   - Better to block good data than pass bad data
   - Especially for allergen safety

4. Clear Communication:
   - User warnings must be actionable
   - Technical details in metadata for debugging

5. Fail Closed:
   - If validation can't complete, block data
   - Don't pass unvalidated data
```

### 6.4 Error Handling
```
Critical Errors (return BLOCKED status):
- Validation logic crashes
- Required data structure missing
- Multiple CRITICAL issues found

Recoverable Errors (return PASS_WITH_WARNINGS):
- Some data missing but core data valid
- Multiple HIGH/MEDIUM issues but no CRITICAL

Non-Fatal Warnings:
- Low confidence scores
- Missing optional data
- Minor inconsistencies
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Test: Allergen Safety Validation**
```
Input: Allergen claim probability=0.9 but no evidence
Expected: CRITICAL issue generated, data blocked

Input: OCR confidence=0.45
Expected: CRITICAL issue, allergen data blocked

Input: Menu says "vegan" but DAIRY=0.95
Expected: CRITICAL issue if no override evidence
```

**Test: Data Consistency Check**
```
Input: Rating sources: Google=4.5, Yelp=3.2 (1.3 diff)
Expected: HIGH warning, suggest showing range

Input: Phone numbers: 555-1234, 555-5678
Expected: MEDIUM warning, show both numbers
```

**Test: Scraping Compliance**
```
Input: robots_txt_violations = ['domain.com/menu']
Expected: CRITICAL issue, block data from that domain

Input: rate_limit_hits = 8
Expected: CRITICAL issue, block request
```

**Test: Quality Score Calculation**
```
Input: 1 CRITICAL issue
Expected: data_quality_score <= 0.7

Input: 3 HIGH issues
Expected: data_quality_score <= 0.7

Input: No issues, allergen confidence=0.9
Expected: allergen_safety_score >= 0.85
```

### 7.2 Integration Tests

**Test: End-to-End Validation**
```
Input: Complete restaurant data with all agent outputs
Process: Run all validation checks
Verify:
- All checks run without errors
- Issues categorized correctly
- User warnings generated
- Quality scores calculated
- Status determined correctly
```

**Test: Allergen Data Blocking**
```
Input: Low-confidence allergen data (0.4)
Verify:
- Data blocked
- User warning explains why
- Suggests alternative action (call restaurant)
```

**Test: Contradiction Resolution**
```
Input: Conflicting ratings from 3 sources
Verify:
- Contradiction detected
- Resolution applied (average/range)
- Warning generated
- User sees resolved value
```

**Test: Clean Data Pass-Through**
```
Input: High-quality data, no issues
Verify:
- status = PASS
- No warnings
- All data in passed_data
- Quality scores high (>0.85)
```

### 7.3 Safety Tests

**Test: Unsafe Allergen Claim Detection**
```
Input: High allergen probability without evidence
Expected: BLOCKED, critical issue, clear explanation

Input: "gluten-free" menu note but GLUTEN=0.9
Expected: BLOCKED, contradiction detected
```

**Test: Low OCR Quality Handling**
```
Input: OCR confidence 0.45, allergen data present
Expected: Allergen data BLOCKED, user warned

Input: OCR confidence 0.65, allergen data present
Expected: PASS_WITH_WARNINGS, prominent warning
```

**Test: Fail Closed Behavior**
```
Input: Validation crashes during check
Expected: Status=BLOCKED, error logged, data not passed
```

---

## 8. Example Validation Flows

### Example 1: High-Quality Data Pass
```
Input:
- Enrichment: confidence=0.92, 3 sources, verified
- Allergen: confidence=0.89, explicit notes, clear menu
- OCR: confidence=0.91, clean text
- Scraping: compliant, no violations

Processing:
1. Allergen safety: ✅ All checks pass
2. Data consistency: ✅ Sources agree
3. Scraping compliance: ✅ No violations
4. Source credibility: ✅ Tier 1 sources
5. Confidence levels: ✅ All > 0.85
6. Completeness: ✅ All fields present
7. Output format: ✅ Valid

Calculate scores:
- data_quality_score: 0.95
- allergen_safety_score: 0.89

Output:
{
  'status': 'PASS',
  'issues': [],
  'critical_issues': [],
  'warnings': [],
  'data_quality_score': 0.95,
  'allergen_safety_score': 0.89,
  'user_warnings': [],
  'passed_data': {/* all data */},
  'blocked_data': {}
}
```

### Example 2: Low Allergen Confidence
```
Input:
- Enrichment: Good quality
- Allergen: confidence=0.58, cuisine priors only, no menu
- OCR: No menu found
- Menu: 0 menus found

Processing:
1. Allergen safety:
   - ⚠️ HIGH: No menu found, allergen data from priors only
   - ⚠️ HIGH: Allergen confidence below threshold (0.7)
2. Completeness:
   - ⚠️ MEDIUM: No menu data available
3. Other checks: Pass

Calculate scores:
- data_quality_score: 0.75 (2 HIGH issues = -0.20)
- allergen_safety_score: 0.50 (low confidence + no menu)

Generate warnings:
- "⚠️ Allergen estimates based on typical cuisine - verify with restaurant"
- "ℹ️ No menu found online - call restaurant to verify allergen safety"

Output:
{
  'status': 'PASS_WITH_WARNINGS',
  'issues': [
    {
      'severity': 'HIGH',
      'category': 'ALLERGEN_SAFETY',
      'message': 'Allergen data based on cuisine estimates only',
      ...
    }
  ],
  'critical_issues': [],
  'warnings': [/* 2 HIGH issues */],
  'data_quality_score': 0.75,
  'allergen_safety_score': 0.50,
  'user_warnings': [
    '⚠️ Allergen estimates based on typical cuisine - verify with restaurant',
    'ℹ️ No menu found online - call restaurant to verify allergen safety'
  ],
  'passed_data': {/* all data with warnings */}
}
```

### Example 3: Unsafe Allergen Claim - BLOCKED
```
Input:
- Allergen: GLUTEN=0.92, confidence=0.35, no evidence, OCR=0.48

Processing:
1. Allergen safety:
   - ❌ CRITICAL: OCR confidence < 0.5
   - ❌ CRITICAL: High allergen claim without evidence
   - ❌ CRITICAL: Overall confidence too low for high claim
2. Block unsafe data

Output:
{
  'status': 'BLOCKED',
  'issues': [
    {
      'severity': 'CRITICAL',
      'category': 'ALLERGEN_SAFETY',
      'message': 'Allergen data unreliable due to poor OCR quality',
      'technical_detail': 'OCR confidence 0.48 < threshold 0.5',
      'affected_field': 'allergen_data',
      'suggested_action': 'Request manual menu verification',
      'source_agent': 'allergen_analyzer'
    },
    {
      'severity': 'CRITICAL',
      'category': 'ALLERGEN_SAFETY',
      'message': 'High allergen probability without supporting evidence',
      'technical_detail': 'GLUTEN=0.92 but confidence=0.35, no evidence provided',
      'affected_field': 'allergen_data.by_dish[0].GLUTEN',
      'source_agent': 'allergen_analyzer'
    }
  ],
  'critical_issues': [/* 2 CRITICAL issues */],
  'data_quality_score': 0.35,
  'allergen_safety_score': 0.0,
  'user_warnings': [
    '⚠️ ALLERGEN DATA BLOCKED: Menu text quality too poor for reliable allergen detection',
    '⚠️ For safety, please call restaurant directly to verify allergen information'
  ],
  'blocked_data': {
    'allergen_data': {/* entire allergen data blocked */}
  },
  'passed_data': {
    'enrichment_data': {/* basic info only */}
  }
}
```

### Example 4: Data Contradiction
```
Input:
- Enrichment: 
  - Google rating: 4.5 (500 reviews)
  - Yelp rating: 3.2 (200 reviews)
  - Website: 4.8 (50 reviews)

Processing:
1. Data consistency:
   - ⚠️ HIGH: Large rating discrepancy (4.5 vs 3.2 = 1.3 difference)
2. Resolve contradiction:
   - Use weighted average by review count
   - (4.5*500 + 3.2*200 + 4.8*50) / 750 = 4.1
   - Show range to user: 3.2-4.8

Output:
{
  'status': 'PASS_WITH_WARNINGS',
  'issues': [
    {
      'severity': 'HIGH',
      'category': 'DATA_CONSISTENCY',
      'message': 'Rating varies significantly across sources',
      'technical_detail': 'Google: 4.5, Yelp: 3.2, Website: 4.8',
      'affected_field': 'enrichment_data.rating',
      'suggested_action': 'Display rating range to user'
    }
  ],
  'user_warnings': [
    '⚠️ Ratings vary across sources (3.2-4.8) - some reviews may be older'
  ],
  'passed_data': {
    'enrichment_data': {
      'rating': 4.1,  // weighted average
      'rating_range': {'min': 3.2, 'max': 4.8},
      'rating_sources': {
        'google': 4.5,
        'yelp': 3.2,
        'website': 4.8
      }
    }
  }
}
```

### Example 5: Scraping Violation - BLOCKED
```
Input:
- Scraping metadata:
  - robots_txt_violations: ['example.com/menu']
  - rate_limit_hits: 12

Processing:
1. Scraping compliance:
   - ❌ CRITICAL: robots.txt violation
   - ❌ CRITICAL: Rate limit abuse (12 hits)
2. Block entire request

Output:
{
  'status': 'BLOCKED',
  'issues': [
    {
      'severity': 'CRITICAL',
      'category': 'SCRAPING_COMPLIANCE',
      'message': 'Scraping policy violation detected',
      'technical_detail': 'Accessed example.com/menu despite robots.txt disallow',
      'suggested_action': 'Remove example.com from scraping sources'
    },
    {
      'severity': 'CRITICAL',
      'category': 'SCRAPING_COMPLIANCE',
      'message': 'Rate limit exceeded',
      'technical_detail': '12 rate limit hits (threshold: 5)',
      'suggested_action': 'Implement request throttling'
    }
  ],
  'critical_issues': [/* 2 CRITICAL */],
  'data_quality_score': 0.0,
  'user_warnings': [
    '⚠️ Unable to retrieve restaurant data due to technical limitations',
    'Please try again later or search for a different restaurant'
  ],
  'blocked_data': {/* all data */},
  'passed_data': {}
}
```

---

## 9. Common Pitfalls to Avoid

1. **❌ Don't pass unsafe allergen data**
   - Block if no evidence for high claims
   - Block if OCR confidence too low
   - Better to show nothing than dangerous info

2. **❌ Don't ignore contradictions**
   - Resolve conflicting data
   - Note discrepancies in warnings
   - Don't pick arbitrary value

3. **❌ Don't skip scraping compliance**
   - Always check robots.txt violations
   - Always check rate limits
   - Legal issues if ignored

4. **❌ Don't generate vague warnings**
   - Be specific about what's wrong
   - Tell user what action to take
   - Avoid technical jargon

5. **❌ Don't block everything**
   - Balance safety with utility
   - Use warnings for minor issues
   - Only block truly unsafe data

6. **❌ Don't trust single sources**
   - Validate against multiple sources
   - Flag if only one source available
   - Prefer verified sources

7. **❌ Don't hide low confidence**
   - Always show confidence scores
   - Prominent warnings for <0.7
   - Explain what affects confidence

8. **❌ Don't pass malformed data**
   - Validate output format
   - Check all required fields
   - Frontend will crash if wrong

9. **❌ Don't calculate scores incorrectly**
   - Weight CRITICAL issues heavily
   - Allergen safety separate from general quality
   - Scores must reflect actual risk

10. **❌ Don't fail silently**
    - If validation crashes, BLOCK data
    - Log all errors
    - Return clear error to user

---

## 10. Success Criteria

The Safety & QA Agent is complete when it:
- ✅ Catches 100% of unsafe allergen claims
- ✅ Detects all scraping compliance violations
- ✅ Resolves data contradictions correctly
- ✅ Generates clear, actionable user warnings
- ✅ Calculates accurate quality scores
- ✅ Blocks data appropriately (not too strict, not too lenient)
- ✅ Completes validation in <500ms
- ✅ Returns output in exact contract format
- ✅ Handles all edge cases gracefully
- ✅ Passes all safety-critical tests
- ✅ Provides transparent quality assessment

---

## 11. Integration Checklist

Before marking complete, verify:
- [ ] Receives data from all upstream agents
- [ ] Validates allergen safety correctly
- [ ] Checks data consistency across sources
- [ ] Verifies scraping compliance
- [ ] Assesses source credibility
- [ ] Validates confidence levels
- [ ] Checks data completeness
- [ ] Validates output format
- [ ] Generates user-friendly warnings
- [ ] Calculates quality scores accurately
- [ ] Blocks unsafe data appropriately
- [ ] Resolves contradictions sensibly
- [ ] Returns exact output format to Frontend
- [ ] Tests cover all validation rules
- [ ] Documentation includes validation logic

---

## 12. Next Steps

Once Safety & QA Agent is complete:
1. Test with 100 diverse restaurant datasets
2. Validate blocking thresholds are appropriate
3. Tune quality score calculations
4. A/B test warning messages for clarity
5. Test integration with all upstream agents

Then proceed to: **Review Enricher Agent** or **Image Scraper Agent** (optional enhancements)

---

**CRITICAL SAFETY REMINDER:** This is the LAST LINE OF DEFENSE. If this agent fails:
- Users see dangerous allergen data
- Users see contradictory information
- Users lose trust in the system
- Legal/ethical violations may occur

**Testing this agent thoroughly is not optional.** Every validation rule must be tested. Every edge case must be handled. Every CRITICAL issue must block data.

When in doubt, BLOCK. Better to show nothing than to show something wrong.