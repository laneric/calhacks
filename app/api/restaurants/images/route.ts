import { NextRequest, NextResponse } from 'next/server';
import { Anthropic } from '@anthropic-ai/sdk';

// Initialize Anthropic client
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY!,
});

// Claude API helper function with web search
async function callClaudeWithWebSearch(messages: any[]) {
  try {
    const response = await anthropic.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1024,
      messages,
      tools: [{
        type: "web_search_20250305",
        name: "web_search",
        max_uses: 5
      }]
    });

    return response;
  } catch (error) {
    console.error('Claude API error:', error);
    throw new Error(`Claude API error: ${error}`);
  }
}

// Function to search for restaurant images using Claude
async function searchRestaurantImage(restaurantName: string, cuisine?: string[], address?: string, city?: string): Promise<string | null> {
  // Extract city from address if not provided
  const cityName = city || (address ? address.split(',').pop()?.trim() : null);
  
  const messages = [
    {
      role: 'user',
      content: `I need you to find a high-quality image URL for the restaurant "${restaurantName}" using web search.

Restaurant details:
- Name: ${restaurantName}
- Cuisine: ${cuisine ? cuisine.join(', ') : 'Not specified'}
- Address: ${address || 'Not specified'}
- City: ${cityName || 'Not specified'}

Please use web search to find:
1. Yelp photos of this specific restaurant
2. Google Maps/Reviews photos of this restaurant
3. TripAdvisor photos of this restaurant
4. Official restaurant website photos
5. Food blog reviews with photos
6. Instagram posts about this restaurant
7. News articles with restaurant photos

Requirements:
- Must be a direct image URL (ending in .jpg, .jpeg, .png, .webp, .gif)
- High resolution (at least 400x300 pixels)
- Publicly accessible
- Actually shows this specific restaurant (not generic stock photos)

Search for: "${restaurantName}" ${cityName ? `"${cityName}"` : ''} restaurant photos

IMPORTANT: Only return an image URL if you find an actual photo of this specific restaurant. Do NOT return generic stock photos or images of other restaurants. If you cannot find a specific image for this exact restaurant, return "NO_IMAGE_FOUND".

Return format: https://example.com/image.jpg or NO_IMAGE_FOUND`
    }
  ];

  try {
    const response = await callClaudeWithWebSearch(messages);
    console.log('Claude response:', response);
    
    // Extract the final answer from Claude's response
    let imageUrl = null;
    
    // Look for the final answer in the response
    if (response.content && response.content.length > 0) {
      const lastContent = response.content[response.content.length - 1];
      if (lastContent.type === 'text') {
        const text = lastContent.text.trim();
        console.log('Claude text response:', text);
        
        // Check if Claude found an image or not
        if (text === 'NO_IMAGE_FOUND') {
          return null;
        }
        
        // Validate that it's a proper URL
        if (text.startsWith('http://') || text.startsWith('https://')) {
          imageUrl = text;
        }
      }
    }
    
    return imageUrl;
  } catch (error) {
    console.error('Error calling Claude API:', error);
    // Return null instead of fallback
    return null;
  }
}


export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const restaurantId = searchParams.get('id');
    const restaurantName = searchParams.get('name');
    const cuisine = searchParams.get('cuisine')?.split(',');
    const address = searchParams.get('address');
    const city = searchParams.get('city');
    const debug = searchParams.get('debug') === 'true';

    if (!restaurantId && !restaurantName) {
      return NextResponse.json(
        { error: 'Restaurant ID or name is required' },
        { status: 400 }
      );
    }

    // Use Claude to search for actual restaurant images
    const imageUrl = await searchRestaurantImage(
      restaurantName || '', 
      cuisine, 
      address || undefined,
      city || undefined
    );

    const response = NextResponse.json({
      imageUrl,
      hasImage: imageUrl !== null,
      restaurantId,
      restaurantName,
      cuisine,
      address,
      city,
      timestamp: new Date().toISOString(),
      ...(debug && { 
        debug: {
          hasClaudeKey: !!process.env.ANTHROPIC_API_KEY,
          claudeKeyLength: process.env.ANTHROPIC_API_KEY?.length || 0
        }
      })
    });

    // Cache for 1 hour
    response.headers.set('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=7200');
    
    return response;

  } catch (error) {
    console.error('Restaurant images API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
