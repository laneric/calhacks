"use client"
import { useState, useCallback } from "react";
import { LocationData } from './libs/location'

// components
import Map from './components/Map'
import PromptInput from './components/PromptInput'
import LocationDisplay from './components/LocationDisplay'

export default function Home() {
  const [userLocation, setUserLocation] = useState<LocationData | null>(null);

  const handlePromptSubmit = (prompt: string) => {
    console.log('User prompt:', prompt)
    // TODO: Implement prompt handling logic
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
      <Map userLocation={userLocation} />
      
      {/* prompt input */}
      <PromptInput onSend={handlePromptSubmit} />
    </div>
  );
}
