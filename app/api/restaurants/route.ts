import { NextRequest, NextResponse } from 'next/server';

// Sample restaurant data around San Francisco
const SAMPLE_RESTAURANTS = [
  {
    id: "1",
    name: "The French Laundry",
    location: { lat: 37.8029, lng: -122.4481 },
    rating: 4.8,
    distanceMeters: 1200,
    cuisine: ["French", "Fine Dining"],
    address: "6640 Washington St, Yountville, CA 94599",
    phone: "(707) 944-2380",
    website: "https://www.thomaskeller.com/tfl",
    isOpen: true,
    summaryAllergenProfile: {
      gluten: 0.3,
      dairy: 0.7,
      nuts: 0.2
    }
  },
  {
    id: "2", 
    name: "Chez Panisse",
    location: { lat: 37.8025, lng: -122.4475 },
    rating: 4.6,
    distanceMeters: 800,
    cuisine: ["California", "Farm-to-Table"],
    address: "1517 Shattuck Ave, Berkeley, CA 94709",
    phone: "(510) 548-5525",
    website: "https://www.chezpanisse.com",
    isOpen: true,
    summaryAllergenProfile: {
      gluten: 0.4,
      dairy: 0.5,
      nuts: 0.3
    }
  },
  {
    id: "3",
    name: "Swan Oyster Depot",
    location: { lat: 37.8035, lng: -122.4490 },
    rating: 4.4,
    distanceMeters: 1500,
    cuisine: ["Seafood", "American"],
    address: "1517 Polk St, San Francisco, CA 94109",
    phone: "(415) 673-1101",
    isOpen: true,
    summaryAllergenProfile: {
      shellfish: 0.9,
      gluten: 0.2,
      dairy: 0.1
    }
  },
  {
    id: "4",
    name: "Tartine Bakery",
    location: { lat: 37.8015, lng: -122.4465 },
    rating: 4.2,
    distanceMeters: 600,
    cuisine: ["Bakery", "French"],
    address: "600 Guerrero St, San Francisco, CA 94110",
    phone: "(415) 487-2600",
    website: "https://www.tartinebakery.com",
    isOpen: true,
    summaryAllergenProfile: {
      gluten: 0.8,
      dairy: 0.6,
      eggs: 0.4
    }
  },
  {
    id: "5",
    name: "State Bird Provisions",
    location: { lat: 37.8040, lng: -122.4485 },
    rating: 4.5,
    distanceMeters: 1100,
    cuisine: ["American", "Innovative"],
    address: "1529 Fillmore St, San Francisco, CA 94115",
    phone: "(415) 795-1272",
    website: "https://www.statebirdsf.com",
    isOpen: true,
    summaryAllergenProfile: {
      gluten: 0.3,
      dairy: 0.4,
      nuts: 0.2
    }
  }
];

// Helper function to calculate distance between two points
function calculateDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = lat1 * Math.PI / 180;
  const φ2 = lat2 * Math.PI / 180;
  const Δφ = (lat2 - lat1) * Math.PI / 180;
  const Δλ = (lng2 - lng1) * Math.PI / 180;

  const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ/2) * Math.sin(Δλ/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

  return R * c; // Distance in meters
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const lat = parseFloat(searchParams.get('lat') || '');
    const lng = parseFloat(searchParams.get('lng') || '');
    const radius = parseInt(searchParams.get('radius') || '5000'); // Default 5km
    const limit = parseInt(searchParams.get('limit') || '20'); // Default 20 restaurants

    // Validate parameters
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

    // Filter restaurants within radius
    const nearbyRestaurants = SAMPLE_RESTAURANTS
      .map(restaurant => {
        const distance = calculateDistance(
          lat, lng, 
          restaurant.location.lat, restaurant.location.lng
        );
        return {
          ...restaurant,
          distanceMeters: Math.round(distance)
        };
      })
      .filter(restaurant => restaurant.distanceMeters <= radius)
      .sort((a, b) => a.distanceMeters - b.distanceMeters) // Sort by distance
      .slice(0, limit);

    // Cache for 5 minutes
    const response = NextResponse.json({
      restaurants: nearbyRestaurants,
      query: { lat, lng, radius, limit },
      total: nearbyRestaurants.length
    });

    response.headers.set('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    
    return response;

  } catch (error) {
    console.error('Restaurant API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
