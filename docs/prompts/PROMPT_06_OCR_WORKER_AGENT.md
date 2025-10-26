# PROMPT 6: OCR Worker Agent Implementation Guide

## Context
You are building the **OCR Worker Agent**, which extracts text from menu images using Optical Character Recognition (OCR). This agent bridges the Menu Finder and Allergen Analyzer, converting visual menus into machine-readable text.

**Tech Stack:**
- Runtime: Letta (stateful agent framework)
- OCR Engines: Tesseract, EasyOCR, or Google Cloud Vision
- Image Processing: Pillow (PIL), OpenCV
- Backend: Flask API
- Caching: Redis (14-day TTL for OCR results)
- Language: Python 3.11+

---

## 1. Purpose and Responsibilities

The OCR Worker Agent must:
1. **Download images** - Fetch menu images from URLs
2. **Preprocess images** - Enhance quality for better OCR
3. **Run OCR** - Extract text using configured engine
4. **Structure output** - Organize text into logical blocks
5. **Detect language** - Identify menu language
6. **Calculate confidence** - Score OCR reliability
7. **Post-process text** - Fix common OCR errors
8. **Handle failures** - Gracefully handle unreadable images
9. **Cache results** - Store OCR output to avoid re-processing
10. **Support parallel processing** - OCR multiple images concurrently

---

## 2. File Structure

**Create:** `agents/ocr_worker_agent.py`

This file should contain:

### 2.1 OCR Engine Enum
Define available OCR engines:
- `TESSERACT` - Open source, fast, good for English
- `EASYOCR` - Deep learning-based, better for non-English
- `GOOGLE_CLOUD_VISION` - Cloud-based, highest accuracy (requires API key)
- `PADDLE_OCR` - Alternative deep learning OCR

### 2.2 Image Quality Enum
Define image quality assessment:
- `EXCELLENT` - High resolution, clear text, good contrast
- `GOOD` - Readable, minor issues
- `FAIR` - Readable with preprocessing
- `POOR` - Difficult to read, low confidence expected
- `UNREADABLE` - Too blurry, too dark, or corrupted

### 2.3 Text Block Type Enum
Define types of text blocks:
- `HEADER` - Section headers (Appetizers, Entrees, etc.)
- `ITEM_NAME` - Dish names
- `DESCRIPTION` - Item descriptions
- `PRICE` - Prices
- `FOOTER` - Bottom text (allergen notes, hours, etc.)
- `UNKNOWN` - Unclassified text

### 2.4 Core Classes

**OCRRequest Class:**
Represents an OCR job. Should include:
- `image_urls`: List[str] - URLs of menu images to process
- `restaurant_id`: str - Associated restaurant
- `restaurant_name`: str - For context
- `cuisine`: Optional[str] - Helps with language detection
- `ocr_engine`: OCREngine - Which engine to use
- `language_hint`: Optional[str] - Expected language (ISO 639-1 code)
- `preprocessing_level`: str - 'none', 'light', 'aggressive'
- `force_refresh`: bool - Bypass cache

**ImageMetadata Class:**
Information about processed image. Should include:
- `url`: str - Original image URL
- `width`: int - Image width in pixels
- `height`: int - Image height in pixels
- `format`: str - Image format (JPEG, PNG, etc.)
- `file_size_bytes`: int - Original file size
- `aspect_ratio`: float - Width/height ratio
- `quality_assessment`: ImageQuality - Assessed quality
- `preprocessing_applied`: List[str] - Steps applied
- `download_time_ms`: int - Time to fetch image

**TextBlock Class:**
A region of extracted text. Should include:
- `text`: str - Extracted text content
- `block_type`: TextBlockType - Classification of text
- `confidence`: float - OCR confidence (0.0-1.0)
- `bounding_box`: Dict - {'x': int, 'y': int, 'width': int, 'height': int}
- `language`: str - Detected language
- `font_size_estimate`: Optional[int] - Estimated font size
- `is_bold`: Optional[bool] - Text appears bold
- `line_number`: int - Vertical position (for ordering)

**OCRResult Class:**
Complete OCR output for one image. Should include:
- `image_url`: str - Source image
- `image_metadata`: ImageMetadata
- `extracted_text`: str - Full text (all blocks concatenated)
- `text_blocks`: List[TextBlock] - Structured text blocks
- `language`: str - Primary language detected
- `ocr_engine`: str - Engine used
- `confidence`: float - Overall confidence (0.0-1.0)
- `processing_time_ms`: int - Total processing time
- `word_count`: int - Total words extracted
- `cache_hit`: bool - Whether from cache
- `errors`: List[str] - Any issues encountered
- `warnings`: List[str] - Quality concerns

**BatchOCRResult Class:**
Results for multiple images. Should include:
- `restaurant_id`: str
- `results`: List[OCRResult] - Per-image results
- `total_images`: int - Images processed
- `successful`: int - Successfully processed
- `failed`: int - Failed to process
- `total_text_length`: int - Combined text length
- `average_confidence`: float - Mean confidence across images
- `processing_time_ms`: int - Total batch time
- `cache_hits`: int - Images retrieved from cache

**OCRWorkerAgent Class:**
Main agent implementation. Should include methods:
- `__init__()` - Initialize OCR engine, image processing libs
- `process_images()` - Main entry point (batch)
- `process_single_image()` - OCR one image
- `_download_image()` - Fetch image from URL
- `_assess_image_quality()` - Check if image suitable for OCR
- `_preprocess_image()` - Enhance image for OCR
- `_run_ocr()` - Execute OCR engine
- `_structure_text_blocks()` - Organize OCR output
- `_detect_language()` - Identify language
- `_post_process_text()` - Fix common OCR errors
- `_calculate_confidence()` - Score OCR reliability
- `_classify_text_block()` - Determine block type
- `_get_from_cache()` - Check cache
- `_save_to_cache()` - Store result

---

## 3. Input/Output Contracts

### 3.1 Input Format (from Menu Finder Agent)
Receives OCR requests in this format:
```python
{
    'image_urls': [
        'https://example.com/menu1.jpg',
        'https://instagram.com/p/xyz/menu.jpg'
    ],
    'restaurant_id': 'rest_123',
    'restaurant_name': 'Super Duper Burger',
    'cuisine': 'burger',
    'ocr_engine': 'TESSERACT',
    'language_hint': 'en',
    'preprocessing_level': 'light',
    'force_refresh': False
}
```

### 3.2 Output Format (to Allergen Analyzer Agent)
Must return OCR results in this format:
```python
{
    'status': 'success' | 'partial' | 'error',
    
    'restaurant_id': 'rest_123',
    
    'results': [
        {
            'image_url': 'https://example.com/menu1.jpg',
            'image_metadata': {
                'width': 1080,
                'height': 1920,
                'format': 'JPEG',
                'file_size_bytes': 342156,
                'aspect_ratio': 0.56,
                'quality_assessment': 'GOOD',
                'preprocessing_applied': ['deskew', 'enhance_contrast'],
                'download_time_ms': 234
            },
            'extracted_text': '''MENU
            
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
Contains: soy (cooked in soybean oil)

Onion Rings - $4.99
Beer-battered onion rings
Contains: wheat, dairy
            ''',
            'text_blocks': [
                {
                    'text': 'MENU',
                    'block_type': 'HEADER',
                    'confidence': 0.98,
                    'bounding_box': {'x': 100, 'y': 50, 'width': 200, 'height': 40},
                    'language': 'en',
                    'font_size_estimate': 36,
                    'is_bold': True,
                    'line_number': 1
                },
                {
                    'text': 'BURGERS',
                    'block_type': 'HEADER',
                    'confidence': 0.95,
                    'bounding_box': {'x': 80, 'y': 120, 'width': 150, 'height': 30},
                    'language': 'en',
                    'font_size_estimate': 24,
                    'is_bold': True,
                    'line_number': 2
                },
                {
                    'text': 'Super Duper Burger',
                    'block_type': 'ITEM_NAME',
                    'confidence': 0.92,
                    'bounding_box': {'x': 80, 'y': 170, 'width': 300, 'height': 25},
                    'language': 'en',
                    'line_number': 3
                },
                {
                    'text': '$10.99',
                    'block_type': 'PRICE',
                    'confidence': 0.96,
                    'bounding_box': {'x': 500, 'y': 170, 'width': 80, 'height': 25},
                    'language': 'en',
                    'line_number': 3
                },
                {
                    'text': 'Classic cheeseburger with lettuce, tomato, onion',
                    'block_type': 'DESCRIPTION',
                    'confidence': 0.88,
                    'bounding_box': {'x': 80, 'y': 200, 'width': 400, 'height': 20},
                    'language': 'en',
                    'font_size_estimate': 12,
                    'line_number': 4
                },
                {
                    'text': 'Contains: wheat, dairy, soy',
                    'block_type': 'DESCRIPTION',
                    'confidence': 0.90,
                    'bounding_box': {'x': 80, 'y': 225, 'width': 350, 'height': 18},
                    'language': 'en',
                    'font_size_estimate': 10,
                    'line_number': 5
                }
                // ... more blocks
            ],
            'language': 'en',
            'ocr_engine': 'TESSERACT',
            'confidence': 0.91,
            'processing_time_ms': 1823,
            'word_count': 87,
            'cache_hit': False,
            'errors': [],
            'warnings': ['Some text near image edges may be cut off']
        }
        // ... more images
    ],
    
    'total_images': 2,
    'successful': 2,
    'failed': 0,
    'total_text_length': 1456,
    'average_confidence': 0.91,
    'processing_time_ms': 3421,
    'cache_hits': 0,
    
    'metadata': {
        'ocr_engine': 'TESSERACT',
        'preprocessing_level': 'light',
        'languages_detected': ['en'],
        'average_image_quality': 'GOOD'
    }
}
```

---

## 4. Image Preprocessing Techniques

### 4.1 Quality Assessment

Before OCR, assess if image is suitable:

**Quality Criteria:**
```python
EXCELLENT:
- Resolution: > 1200px on shorter side
- Contrast ratio: > 4.5:1
- Sharpness: Laplacian variance > 100
- Noise level: < 10%

GOOD:
- Resolution: 800-1200px
- Contrast ratio: 3:1 - 4.5:1
- Sharpness: Laplacian variance 50-100
- Noise level: 10-20%

FAIR:
- Resolution: 400-800px
- Contrast ratio: 2:1 - 3:1
- Sharpness: Laplacian variance 20-50
- Noise level: 20-40%

POOR:
- Resolution: < 400px
- Contrast ratio: < 2:1
- Sharpness: Laplacian variance < 20
- Noise level: > 40%

UNREADABLE:
- Extremely blurry (variance < 10)
- Extremely dark/bright (mean < 20 or > 235)
- Corrupted file
```

### 4.2 Preprocessing Pipeline

**Light Preprocessing (default):**
```
1. Convert to grayscale (faster OCR, good for most menus)
2. Deskew (rotate to correct orientation)
3. Remove noise (median filter)
4. Enhance contrast (CLAHE - Contrast Limited Adaptive Histogram Equalization)
```

**Aggressive Preprocessing (for poor quality images):**
```
1. Grayscale conversion
2. Deskew
3. Bilateral filter (remove noise, preserve edges)
4. Morphological operations (remove small artifacts)
5. Adaptive thresholding (binarize image)
6. Contrast enhancement (CLAHE)
7. Sharpening (unsharp mask)
```

**No Preprocessing:**
```
Use for high-quality images where preprocessing might hurt more than help
```

### 4.3 Specific Preprocessing Functions

**Deskew Function:**
```
Purpose: Correct image rotation
Method: Detect text lines, calculate skew angle, rotate image
Libraries: OpenCV's HoughLinesP or Tesseract's OSD (Orientation and Script Detection)
```

**Denoise Function:**
```
Purpose: Remove image noise
Method: Bilateral filter (preserves edges) or Non-local means denoising
Parameters: 
  - Filter strength: 10 (light) to 30 (aggressive)
  - Search window: 7x7 to 21x21
```

**Contrast Enhancement Function:**
```
Purpose: Make text more readable
Method: CLAHE (Contrast Limited Adaptive Histogram Equalization)
Parameters:
  - Clip limit: 2.0-4.0
  - Tile grid size: 8x8
```

**Binarization Function:**
```
Purpose: Convert to black/white for better OCR
Method: Adaptive thresholding (Otsu's method or Sauvola)
When to use: For images with varying lighting or shadows
```

**Sharpening Function:**
```
Purpose: Enhance text edges
Method: Unsharp mask
Parameters:
  - Radius: 1-2
  - Amount: 1.0-2.0
  - Threshold: 0
When to use: For slightly blurry images
```

---

## 5. OCR Engine Integration

### 5.1 Tesseract OCR

**Setup:**
```
Install: tesseract-ocr (system package)
Python wrapper: pytesseract
Languages: Install language packs as needed (tesseract-ocr-eng, tesseract-ocr-spa, etc.)
```

**Configuration:**
```python
config = {
    'psm': 3,  # Page Segmentation Mode: 3 = Fully automatic page segmentation
    'oem': 3,  # OCR Engine Mode: 3 = Default (LSTM + legacy)
    'language': 'eng',  # Language hint
    'tessedit_char_whitelist': None,  # Don't restrict characters
}

# For menu-specific optimization:
config_menu = {
    'psm': 6,  # Assume uniform block of text
    'oem': 3,
    'language': 'eng',
}
```

**Advantages:**
- Fast processing
- Good for English text
- Low resource usage
- No API costs

**Limitations:**
- Lower accuracy for non-English
- Struggles with handwritten text
- Needs good image quality

### 5.2 EasyOCR

**Setup:**
```
Install: pip install easyocr
Models: Auto-downloads on first use
Languages: Supports 80+ languages
```

**Configuration:**
```python
config = {
    'languages': ['en'],  # List of languages
    'gpu': False,  # Use GPU if available
    'detail': 1,  # Return bounding boxes and confidence
    'paragraph': False,  # Don't merge lines into paragraphs
}
```

**Advantages:**
- Better accuracy for non-English
- Better for low-quality images
- Handles multiple languages well

**Limitations:**
- Slower than Tesseract
- Requires more memory
- First run downloads models (~100MB per language)

### 5.3 Google Cloud Vision

**Setup:**
```
Install: pip install google-cloud-vision
Credentials: Set GOOGLE_APPLICATION_CREDENTIALS env var
Costs: $1.50 per 1000 images (first 1000/month free)
```

**Configuration:**
```python
config = {
    'features': ['TEXT_DETECTION'],
    'language_hints': ['en'],
    'image_context': {
        'crop_hints_params': {'aspect_ratios': [0.8, 1.0, 1.2]}
    }
}
```

**Advantages:**
- Highest accuracy
- Excellent for handwritten text
- Best language detection
- Handles difficult images

**Limitations:**
- Requires internet connection
- Costs money after free tier
- Slower due to API calls
- Privacy concerns (data sent to Google)

### 5.4 Engine Selection Logic

```
Choose engine based on:

Use TESSERACT if:
- English language
- Good image quality (GOOD or EXCELLENT)
- Speed is priority
- No API costs desired

Use EASYOCR if:
- Non-English language
- Fair image quality
- Better accuracy needed
- Running locally (no API calls)

Use GOOGLE_CLOUD_VISION if:
- Poor image quality
- Handwritten menus
- Highest accuracy required
- Budget allows API costs
```

---

## 6. Helper Functions to Create

### 6.1 Image Download Helper
**Function:** `_download_image(url: str, timeout: int = 10) -> Tuple[bytes, ImageMetadata]`

**Purpose:** Fetch image from URL

**Should handle:**
- HTTPS requests with User-Agent header
- Timeouts
- Large files (stream download for >10MB)
- Redirects
- Authentication errors (403, 401)

**Should validate:**
- Content-Type is image/* 
- File size reasonable (<20MB)
- URL accessible

**Returns:** (image_bytes, ImageMetadata)

### 6.2 Image Quality Assessor Helper
**Function:** `_assess_image_quality(image: PIL.Image) -> ImageQuality`

**Purpose:** Determine if image suitable for OCR

**Should calculate:**
- Resolution (width x height)
- Sharpness (Laplacian variance)
- Contrast ratio (std dev of grayscale)
- Brightness (mean pixel value)
- Noise level (local variance)

**Should return:** ImageQuality enum value with reasoning

### 6.3 Preprocessing Helper
**Function:** `_preprocess_image(image: PIL.Image, level: str, quality: ImageQuality) -> Tuple[PIL.Image, List[str]]`

**Purpose:** Enhance image for better OCR

**Should apply based on level:**
- 'none': No preprocessing
- 'light': Grayscale, deskew, denoise, contrast
- 'aggressive': All preprocessing steps

**Should adapt to quality:**
- EXCELLENT/GOOD: Minimal preprocessing
- FAIR: Light preprocessing
- POOR: Aggressive preprocessing

**Returns:** (preprocessed_image, steps_applied)

### 6.4 Deskew Helper
**Function:** `_deskew_image(image: PIL.Image) -> Tuple[PIL.Image, float]`

**Purpose:** Correct image rotation

**Should:**
- Detect text orientation
- Calculate skew angle
- Rotate image to correct
- Handle both portrait and landscape

**Returns:** (deskewed_image, rotation_angle)

### 6.5 OCR Executor Helper
**Function:** `_run_ocr(image: PIL.Image, engine: OCREngine, language: str, config: Dict) -> Dict`

**Purpose:** Execute configured OCR engine

**Should:**
- Call appropriate engine (Tesseract, EasyOCR, GCV)
- Apply engine-specific config
- Extract text and bounding boxes
- Get confidence scores
- Handle engine errors/timeouts

**Returns:**
```python
{
    'text': str,  # Full extracted text
    'blocks': [
        {
            'text': str,
            'confidence': float,
            'bbox': {'x': int, 'y': int, 'width': int, 'height': int}
        }
    ],
    'engine_metadata': dict
}
```

### 6.6 Text Block Structurer Helper
**Function:** `_structure_text_blocks(ocr_output: Dict, image_height: int) -> List[TextBlock]`

**Purpose:** Organize OCR output into logical blocks

**Should:**
- Sort blocks by vertical position (top to bottom)
- Classify blocks by type (header, item, price, etc.)
- Group related blocks (item name + description + price)
- Estimate font sizes
- Detect bold text (wider bounding boxes)

**Returns:** List of structured TextBlock objects

### 6.7 Text Block Classifier Helper
**Function:** `_classify_text_block(text: str, bbox: Dict, context: List[str]) -> TextBlockType`

**Purpose:** Determine what type of text block

**Should check:**
- ALL CAPS + large font → HEADER
- Contains $ or currency → PRICE
- Short text + title case + large font → ITEM_NAME
- Long text + small font → DESCRIPTION
- Bottom 10% of image → FOOTER
- Words like "APPETIZERS", "ENTREES" → HEADER

**Returns:** TextBlockType enum value

### 6.8 Language Detector Helper
**Function:** `_detect_language(text: str, cuisine_hint: Optional[str]) -> str`

**Purpose:** Identify language of menu

**Should use:**
- langdetect or langid library
- Character set analysis
- Common food words by language
- Cuisine hint (Italian restaurant → likely Italian language)

**Should handle:**
- Mixed language menus (English + Spanish)
- Short text (may be ambiguous)
- Special characters

**Returns:** ISO 639-1 language code ('en', 'es', 'fr', etc.)

### 6.9 Text Post-Processor Helper
**Function:** `_post_process_text(text: str, language: str) -> str`

**Purpose:** Fix common OCR errors

**Should fix:**
- Common character confusions (0→O, 1→l, 5→S)
- Missing spaces between words
- Extra spaces
- Repeated characters
- Currency symbols ($, €, £)
- Common food words (spell check against dictionary)

**Pattern corrections:**
```
"8urger" → "Burger"
"Ch1cken" → "Chicken"
"$1O.99" → "$10.99"
"F r i e s" → "Fries"
```

**Returns:** Corrected text string

### 6.10 Confidence Calculator Helper
**Function:** `_calculate_confidence(ocr_output: Dict, image_quality: ImageQuality, text_blocks: List[TextBlock]) -> float`

**Purpose:** Score overall OCR reliability

**Should consider:**
- Image quality (EXCELLENT = higher confidence)
- Average block confidence from OCR engine
- Text coherence (readable words vs gibberish)
- Expected menu structure (has sections, items, prices)

**Formula suggestion:**
```
confidence = (
    0.3 * image_quality_score +
    0.4 * average_ocr_confidence +
    0.2 * text_coherence_score +
    0.1 * structure_score
)

Where:
- image_quality_score: 1.0 (EXCELLENT) to 0.0 (UNREADABLE)
- average_ocr_confidence: mean of block confidences
- text_coherence_score: % of words in dictionary
- structure_score: has headers, items, prices = 1.0, else lower
```

**Returns:** Confidence score (0.0-1.0)

### 6.11 Cache Management Helpers

**Function:** `_generate_cache_key(image_url: str, ocr_engine: str, preprocessing: str) -> str`

**Purpose:** Generate unique cache key

**Format:** `ocr:{url_hash}:{engine}:{preprocessing}`

**Function:** `_get_from_cache(cache_key: str) -> Optional[OCRResult]`

**Purpose:** Check Redis for cached OCR result

**Should:**
- Deserialize JSON
- Check age (< 14 days)
- Validate structure

**Function:** `_save_to_cache(cache_key: str, result: OCRResult, ttl: int = 1209600)`

**Purpose:** Save OCR result to Redis (14 days)

---

## 7. Integration Guardrails

### 7.1 Input Validation
Before processing:
- ✅ Validate image_urls are valid URLs
- ✅ Validate image URLs return image content-type
- ✅ Validate OCR engine is supported
- ✅ Validate language hint is valid ISO 639-1 code
- ✅ Validate preprocessing level is valid option

### 7.2 Output Contract Compliance
MUST return exact format expected by Allergen Analyzer:
- ✅ `extracted_text` contains full concatenated text
- ✅ `text_blocks` array has all required fields
- ✅ Blocks sorted by line_number (top to bottom)
- ✅ Bounding boxes have x, y, width, height
- ✅ Confidence scores are 0.0-1.0
- ✅ Language is ISO 639-1 code
- ✅ Metadata includes processing time

### 7.3 Error Handling Strategy
```
Critical Errors (fail entire job):
- All images inaccessible (404, timeout)
- OCR engine not available

Recoverable Errors (partial results):
- Some images fail to download → process others
- OCR fails on some images → return successful ones
- Image corrupted → skip and continue

Non-Fatal Warnings:
- Low OCR confidence → flag in warnings
- Poor image quality → note in warnings
- Partial text extraction → include what was found
```

### 7.4 Resource Management
```
Memory:
- Limit concurrent image processing to avoid OOM
- Clear large image objects after processing
- Stream large files (>10MB) instead of loading fully

Time:
- Set timeout per image (5-10 seconds)
- Use multiprocessing for batch jobs
- Return partial results if batch timeout

Storage:
- Don't store original images (only metadata)
- Compress text blocks in cache if very large
- Clean up temp files after processing
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test: Image Download**
```
Mock URL returning image bytes
Expected: Successfully downloads, validates content-type
```

**Test: Quality Assessment**
```
Input: High-res clear image
Expected: Quality = EXCELLENT

Input: Low-res blurry image
Expected: Quality = POOR
```

**Test: Preprocessing**
```
Input: Skewed image
Expected: Deskew applied, rotation angle detected

Input: Noisy image
Expected: Denoising applied, cleaner output
```

**Test: OCR Execution**
```
Input: Clear menu image with "BURGER $10.99"
Expected: Text extracted correctly, confidence > 0.8
```

**Test: Text Block Classification**
```
Input: "APPETIZERS" in large font
Expected: block_type = HEADER

Input: "$12.99"
Expected: block_type = PRICE
```

**Test: Language Detection**
```
Input: English menu text
Expected: language = 'en'

Input: Spanish menu text
Expected: language = 'es'
```

### 8.2 Integration Tests

**Test: End-to-End OCR**
```
Input: Menu image URL
Process: Download → Assess → Preprocess → OCR → Structure → Cache
Verify:
- Text extracted
- Blocks structured
- Confidence calculated
- Result cached
```

**Test: Batch Processing**
```
Input: 5 menu images
Verify:
- All processed (or failed gracefully)
- Results in correct order
- Total processing time reasonable
- Partial results returned if some fail
```

**Test: Cache Hit/Miss**
```
First call: Cache miss, performs OCR, saves
Second call: Cache hit, returns cached
Verify: cache_hit flag correct
```

**Test: Poor Quality Image Handling**
```
Input: Blurry, dark menu image
Expected: Quality = POOR, aggressive preprocessing applied, warnings generated
```

### 8.3 Edge Case Tests

**Test: Empty Image**
```
Input: Blank white image
Expected: No text extracted, confidence = 0.0, appropriate error
```

**Test: Non-Menu Image**
```
Input: Random photo (not a menu)
Expected: Low confidence, warning about irrelevant content
```

**Test: Handwritten Menu**
```
Input: Handwritten chalkboard menu
Expected: Lower confidence, use EasyOCR or GCV for better results
```

**Test: Multi-Language Menu**
```
Input: Menu with English and Spanish
Expected: Both languages detected, text in both extracted
```

**Test: Very Large Image**
```
Input: 10MB+ high-res image
Expected: Streams download, resizes before OCR, doesn't OOM
```

---

## 9. Example OCR Flows

### Example 1: Successful High-Quality Menu
```
Input:
{
  'image_urls': ['https://example.com/menu.jpg'],
  'restaurant_name': 'Italian Kitchen',
  'cuisine': 'italian',
  'ocr_engine': 'TESSERACT',
  'preprocessing_level': 'light'
}

Processing:
1. Download image: 1080x1920, JPEG, 342KB
2. Assess quality: GOOD (high res, good contrast)
3. Preprocess (light):
   - Convert to grayscale
   - Deskew: 1.2° rotation
   - Enhance contrast (CLAHE)
4. Run Tesseract OCR:
   - Extract 487 words
   - Average confidence: 0.89
5. Structure blocks:
   - 3 headers (APPETIZERS, PASTA, ENTREES)
   - 12 item names
   - 12 descriptions
   - 12 prices
6. Post-process text:
   - Fixed "8ruschetta" → "Bruschetta"
   - Fixed "$1O" → "$10"
7. Calculate confidence: 0.91
8. Save to cache

Output:
{
  'status': 'success',
  'results': [{
    'extracted_text': 'MENU\n\nAPPETIZERS\nBruschetta - $8.99\n...',
    'text_blocks': [...],
    'language': 'en',
    'confidence': 0.91,
    'processing_time_ms': 1823,
    'warnings': []
  }]
}
```

### Example 2: Poor Quality Image Requiring Aggressive Preprocessing
```
Input:
{
  'image_urls': ['https://instagram.com/p/xyz/dark_menu.jpg'],
  'restaurant_name': 'Cafe',
  'ocr_engine': 'EASYOCR',
  'preprocessing_level': 'aggressive'
}

Processing:
1. Download image: 720x1280, JPEG, 156KB
2. Assess quality: POOR (low res, dark, low contrast)
3. Preprocess (aggressive):
   - Grayscale
   - Bilateral filter (denoise)
   - Adaptive thresholding (binarize)
   - Morph operations (clean)
   - CLAHE (strong contrast)
   - Sharpen (unsharp mask)
4. Run EasyOCR:
   - Extract 234 words
   - Average confidence: 0.62 (lower due to poor source)
5. Structure blocks: 18 blocks identified
6. Post-process: Multiple corrections needed
7. Calculate confidence: 0.65 (marked as lower due to quality)
8. Save to cache

Output:
{
  'status': 'success',
  'results': [{
    'image_metadata': {
      'quality_assessment': 'POOR',
      'preprocessing_applied': [
        'grayscale', 'denoise', 'binarize', 
        'morph', 'clahe', 'sharpen'
      ]
    },
    'confidence': 0.65,
    'warnings': [
      'Image quality poor - OCR accuracy may be limited',
      'Aggressive preprocessing applied',
      'Manual verification recommended'
    ]
  }]
}
```

### Example 3: Batch Processing with Partial Failure
```
Input:
{
  'image_urls': [
    'https://example.com/menu1.jpg',
    'https://example.com/menu2.jpg',
    'https://example.com/broken.jpg'  # 404
  ]
}

Processing:
1. Image 1: Success (confidence: 0.89)
2. Image 2: Success (confidence: 0.93)
3. Image 3: Download fails (404 Not Found)

Output:
{
  'status': 'partial',
  'results': [
    {/*image1 result*/},
    {/*image2 result*/}
  ],
  'total_images': 3,
  'successful': 2,
  'failed': 1,
  'errors': [
    'Failed to download https://example.com/broken.jpg: 404 Not Found'
  ]
}
```

### Example 4: Non-English Menu
```
Input:
{
  'image_urls': ['https://example.com/menu_es.jpg'],
  'cuisine': 'mexican',
  'ocr_engine': 'EASYOCR',
  'language_hint': 'es'
}

Processing:
1. Download and assess: GOOD quality
2. Preprocess: Light
3. Run EasyOCR with Spanish model
4. Detect language: 'es' (Spanish)
5. Extract text in Spanish
6. Post-process (Spanish spell-check)
7. Structure blocks

Output:
{
  'status': 'success',
  'results': [{
    'extracted_text': 'MENÚ\n\nENTRADAS\nTacos - $9.99\n...',
    'language': 'es',
    'confidence': 0.87,
    'text_blocks': [
      {'text': 'MENÚ', 'language': 'es', ...},
      {'text': 'ENTRADAS', 'language': 'es', ...}
    ]
  }]
}
```

---

## 10. Common Pitfalls to Avoid

1. **❌ Don't skip preprocessing**
   - Even good images benefit from deskew and contrast enhancement
   - Assess quality and apply appropriate preprocessing

2. **❌ Don't use wrong OCR engine**
   - Tesseract for English high-quality
   - EasyOCR for non-English or poor quality
   - Don't use expensive GCV when not needed

3. **❌ Don't ignore bounding boxes**
   - Bounding boxes are crucial for structuring text
   - Use them to determine reading order
   - Use them to classify text types (headers larger than descriptions)

4. **❌ Don't trust OCR blindly**
   - Calculate and return confidence scores
   - Flag low-confidence results
   - Suggest manual verification when needed

5. **❌ Don't load huge images in memory**
   - Resize large images before OCR
   - Stream downloads for >10MB files
   - Clear image objects after processing

6. **❌ Don't process non-menu images**
   - Validate image likely contains menu
   - Check for food-related text
   - Warn if content seems wrong

7. **❌ Don't forget language detection**
   - Many restaurants have non-English menus
   - Use language hint when available
   - Return detected language for allergen analysis

8. **❌ Don't skip post-processing**
   - OCR makes predictable errors
   - Fix common character confusions
   - Spell-check food words

9. **❌ Don't block on single failures**
   - Process other images if one fails
   - Return partial results
   - Log errors for debugging

10. **❌ Don't waste time on cached results**
    - Check cache before OCR
    - Cache aggressively (14 day TTL)
    - Include preprocessing settings in cache key

---

## 11. Success Criteria

The OCR Worker Agent is complete when it:
- ✅ Successfully extracts text from 85%+ of menu images
- ✅ Achieves 0.75+ average confidence on good quality images
- ✅ Properly structures text into blocks with classifications
- ✅ Handles poor quality images with aggressive preprocessing
- ✅ Supports English and at least 3 other languages
- ✅ Completes processing in <3 seconds per image (excluding download)
- ✅ Returns output in exact contract format
- ✅ Caches results to avoid redundant processing
- ✅ Processes batches in parallel efficiently
- ✅ Handles failures gracefully with partial results
- ✅ Passes all unit and integration tests

---

## 12. Integration Checklist

Before marking complete, verify:
- [ ] Receives menu image URLs from Menu Finder
- [ ] Downloads images successfully with error handling
- [ ] Assesses image quality accurately
- [ ] Applies appropriate preprocessing
- [ ] Runs configured OCR engine correctly
- [ ] Structures text blocks with classifications
- [ ] Detects language correctly
- [ ] Calculates confidence scores
- [ ] Returns exact output format to Allergen Analyzer
- [ ] Caches results properly
- [ ] Handles batch processing efficiently
- [ ] Tests cover multiple image qualities and languages
- [ ] Documentation includes example OCR outputs

---

## 13. Next Steps

Once OCR Worker Agent is complete:
1. Test with 100 diverse menu images (various qualities, languages, styles)
2. Measure text extraction accuracy (compare to ground truth)
3. Tune preprocessing parameters for edge cases
4. Optimize processing time (parallel processing, caching)
5. Test integration with Menu Finder and Allergen Analyzer

Then proceed to: **Allergen Analyzer Agent** (uses OCR text to detect allergens)

---

**Remember:** OCR is inherently imperfect. The goal is 85-90% accuracy, not perfection. Focus on:
1. Good enough for allergen detection (key words extracted)
2. Clear confidence scores (so downstream agents know reliability)
3. Graceful degradation (return what you can, warn about limitations)

Better to return low-confidence results with warnings than to fail completely.