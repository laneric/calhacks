"use client"
import React, { useState, useEffect } from 'react';
import { MapPinIcon, ArrowPathIcon } from '@heroicons/react/24/solid';
import { TbLocationFilled } from "react-icons/tb";
import { LocationService, LocationData } from '../libs/location';

interface LocationDisplayProps {
  onLocationChange?: (location: LocationData) => void;
  onRecenter?: () => void;
  showRecenterButton?: boolean;
  className?: string;
}

export default function LocationDisplay({ onLocationChange, onRecenter, showRecenterButton = false, className = "" }: LocationDisplayProps) {
  const [location, setLocation] = useState<LocationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadLocation = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const locationService = LocationService.getInstance();
        const currentLocation = await locationService.getCurrentLocation();
        
        setLocation(currentLocation);
        onLocationChange?.(currentLocation);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to get location';
        setError(errorMessage);
        console.error('Location error:', errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    loadLocation();
  }, []); // Run only once on mount

  const getDisplayText = () => {
    if (isLoading) {
      return 'Getting location...';
    }
    
    if (error) {
      return 'Location unavailable';
    }
    
    if (location) {
      const locationService = LocationService.getInstance();
      return locationService.getLocationString(location);
    }
    
    return 'Unknown location';
  };

  const getLocationIcon = () => {
    if (isLoading) {
      return (
        <div className="w-5 h-5 border-2 mr-2 border-white/50 border-t-white rounded-full animate-spin" />
      );
    }
    
    return <MapPinIcon className="w-5 h-5 text-white" />;
  };

  return (
    <div className={`flex items-center gap-2 transition-all duration-400 ease-out ${showRecenterButton ? 'gap-2' : 'gap-0'}`}>
      <div className="flex items-center gap-1 px-6 py-3 rounded-full border border-white/20 backdrop-blur-sm bg-neutral-900/30">
        {getLocationIcon()}
        <p className="text-white text-md font-medium whitespace-nowrap">{getDisplayText()}</p>
      </div>
      
      {/* Re-center button - with fade in and slide from left transition */}
      <div 
        className={`transition-all duration-400 ease-out ${
          showRecenterButton 
            ? 'opacity-100 translate-x-0 max-w-16' 
            : 'opacity-0 -translate-x-full max-w-0 overflow-hidden pointer-events-none'
        }`}
      >
        <button
          onClick={onRecenter}
          className="p-4 rounded-full border border-white/20 hover:border-white/40 hover:bg-white/10 transition-all duration-200 bg-neutral-900/30 backdrop-blur-sm"
          title="Re-center to your location"
          disabled={!location || isLoading}
        >
          <TbLocationFilled className="size-5 text-white" />
        </button>
      </div>
    </div>
  );
}