import { NextRequest, NextResponse } from 'next/server';

// flask backend url
const FLASK_API_URL = 'http://localhost:5001';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const lat = parseFloat(searchParams.get('lat') || '');
    const lng = parseFloat(searchParams.get('lng') || '');
    const radius = parseInt(searchParams.get('radius') || '5000'); // default 5km
    const researchLimit = parseInt(searchParams.get('researchLimit') || '3'); // default research 3 restaurants

    // validate parameters
    if (isNaN(lat) || isNaN(lng)) {
      return NextResponse.json(
        { error: 'Invalid latitude or longitude parameters' },
        { status: 400 }
      );
    }

    if (radius < 100 || radius > 50000) {
      return NextResponse.json(
        { error: 'Radius must be between 100m and 50km' },
        { status: 400 }
      );
    }

    // call flask backend research endpoint
    const flaskUrl = `${FLASK_API_URL}/restaurants/research?lat=${lat}&lng=${lng}&radius=${radius}&limit=${researchLimit}`;

    console.log('Calling Flask API:', flaskUrl);

    const flaskResponse = await fetch(flaskUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!flaskResponse.ok) {
      const errorData = await flaskResponse.json();
      return NextResponse.json(
        { error: errorData.error || 'Flask API error' },
        { status: flaskResponse.status }
      );
    }

    const data = await flaskResponse.json();

    // combine researched and non-researched restaurants
    const allRestaurants = [
      ...data.restaurants_with_research,
      ...data.restaurants_without_research
    ];

    // return in format expected by frontend
    const response = NextResponse.json({
      restaurants: allRestaurants,
      query: { lat, lng, radius },
      total: data.total_found,
      researched: data.total_researched,
      // include research metadata
      meta: {
        researched_count: data.total_researched,
        total_found: data.total_found
      }
    });

    // cache for 5 minutes
    response.headers.set('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');

    return response;

  } catch (error) {
    console.error('Restaurant API error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: String(error) },
      { status: 500 }
    );
  }
}
