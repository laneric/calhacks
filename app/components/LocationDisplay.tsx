"use client"
import React, { useState, useEffect } from 'react';
import { MapPinIcon } from '@heroicons/react/24/solid';
import { LocationService, LocationData } from '../libs/location';

interface LocationDisplayProps {
  onLocationChange?: (location: LocationData) => void;
  className?: string;
}

export default function LocationDisplay({ onLocationChange, className = "" }: LocationDisplayProps) {
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
  }, [onLocationChange]); // Include onLocationChange in dependencies

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
    <div className={`flex items-center gap-1 ${className}`}>
      {getLocationIcon()}
      <p className="text-white text-md font-medium">{getDisplayText()}</p>
    </div>
  );
}