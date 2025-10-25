"use client"
import { useState, useCallback } from "react";
import { LocationData } from './libs/location'
import { Restaurant } from './libs/types'
import { SparklesIcon } from '@heroicons/react/24/solid'

// components
import Map from './components/Map'
import PromptInput from './components/PromptInput'
import LocationDisplay from './components/LocationDisplay'
import RestaurantCardDeck from './components/RestaurantCardDeck'

export default function Home() {
  const [userLocation, setUserLocation] = useState<LocationData | null>(null);
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [restaurantDeck, setRestaurantDeck] = useState<Restaurant[]>([]);

  const handlePromptSubmit = (prompt: string) => {
    console.log('User prompt:', prompt)
    // TODO: Implement prompt handling logic
  }

  const handleDiceRoll = async () => {
    if (!userLocation) {
      console.log('No user location available for dice roll');
      return;
    }

    try {
      // Fetch restaurants from the Flask API
      const flaskUrl = process.env.NEXT_PUBLIC_FLASK_URL || 'http://localhost:5001';
      const response = await fetch(`${flaskUrl}/restaurants?lat=${userLocation.latitude}&lng=${userLocation.longitude}&radius=5000`);
      if (!response.ok) throw new Error(`Failed to fetch restaurants: ${response.status}`);
      
      const data = await response.json();
      const restaurants = data.restaurants;
      
      if (restaurants.length > 0) {
        // Set the entire deck of restaurants
        setRestaurantDeck(restaurants);
        // Select the first restaurant to show on map
        setSelectedRestaurant(restaurants[0]);
      } else {
        console.log('No restaurants found nearby');
      }
    } catch (error) {
      console.error('Error fetching random restaurant:', error);
    }
  }

  const handleLocationChange = useCallback((location: LocationData) => {
    setUserLocation(location);
  }, []);

  return (
    <div className="relative w-full h-screen">
      {/* topbar */}
      <div className="fixed left-1/2 top-10 -translate-x-1/2 px-6 py-4 h-12 flex items-center gap-1 rounded-full border border-white/20 backdrop-blur-sm bg-neutral-900/30 whitespace-nowrap z-10">
        <LocationDisplay onLocationChange={handleLocationChange} />
      </div>
      
      {/* map view */}
      <Map 
        userLocation={userLocation} 
        selectedRestaurant={selectedRestaurant}
        onRestaurantSelect={setSelectedRestaurant}
        onRestaurantDeselect={() => setSelectedRestaurant(null)}
        isDeckActive={restaurantDeck.length > 0}
        onDeckClose={() => {
          setRestaurantDeck([]);
          setSelectedRestaurant(null); // Clear selected restaurant to hide marker
        }}
      />
      
      {/* restaurant card deck */}
      {restaurantDeck.length > 0 && (
        <RestaurantCardDeck 
          restaurants={restaurantDeck}
          isVisible={restaurantDeck.length > 0}
          onClose={() => {
            setRestaurantDeck([]);
            setSelectedRestaurant(null); // Clear selected restaurant to hide marker
          }}
          onRestaurantSelect={setSelectedRestaurant}
        />
      )}

      {/* prompt input with dice roll button */}
      <div className="fixed bottom-12 left-[30px] right-[30px] w-auto md:left-1/2 md:-translate-x-1/2 md:w-2/6 z-50 flex items-center gap-3">
        {/* dice roll button */}
        <button
          onClick={handleDiceRoll}
          className="p-4 rounded-full border-2 hover:cursor-pointer border-neutral-700 bg-white transition-colors shadow-lg"
          title="Random restaurant suggestion"
        >
          <SparklesIcon className="size-7 text-black" />
        </button>
        
        {/* prompt input */}
        <PromptInput onSend={handlePromptSubmit} />
      </div>
    </div>
  );
}
