'use client';

import React, { useRef, useEffect, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { Restaurant, RestaurantResponse } from '../libs/types';
import RestaurantMarker from './RestaurantMarker';
import 'mapbox-gl/dist/mapbox-gl.css';

interface MapProps {
  userLocation?: { latitude: number; longitude: number; accuracy?: number } | null;
  onMapLoad?: (map: mapboxgl.Map) => void;
  selectedRestaurant?: Restaurant | null;
  onRestaurantSelect?: (restaurant: Restaurant | null) => void;
  onRestaurantDeselect?: () => void;
  isDeckActive?: boolean;
  onDeckClose?: () => void;
  mapRef?: React.RefObject<{ recenterToUser: () => void } | null>;
  onViewChange?: (isAwayFromUser: boolean) => void;
}

export default function Map({ userLocation, onMapLoad, selectedRestaurant, onRestaurantSelect, onRestaurantDeselect, isDeckActive, onDeckClose, mapRef: externalMapRef, onViewChange }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  const [isMapReady, setIsMapReady] = useState(false);
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [activeRestaurantId, setActiveRestaurantId] = useState<string | null>(null);

  // Helper function to calculate distance between two points in meters
  const calculateDistance = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
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
  };

  // Expose recenterToUser method through external ref
  useEffect(() => {
    if (externalMapRef && mapRef.current) {
      externalMapRef.current = {
        recenterToUser: () => {
          if (mapRef.current && userLocation && isMapReady) {
            const center: [number, number] = [userLocation.longitude, userLocation.latitude];
            mapRef.current.flyTo({ 
              center, 
              zoom: 15.5, 
              essential: true,
              duration: 1500
            });
          }
        }
      };
    }
  }, [externalMapRef, userLocation, isMapReady]);

  // Init map once
  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;

    const token =
      process.env.NEXT_PUBLIC_MAPBOX_TOKEN ??
      'pk.eyJ1IjoiZXJpY2xhbm1hcHMiLCJhIjoiY21oNXJwYmd1MDA2MzJscTNkdWZqb3AzaSJ9.dbB8rrHS-wjAf-yEX7H1Ig';
    if (!token) {
      console.error('Mapbox token is missing');
      return;
    }
    mapboxgl.accessToken = token;

    const defaultCenter: [number, number] = [-122.4481, 37.8029]; // SF
    const center: [number, number] = userLocation
      ? [userLocation.longitude, userLocation.latitude]
      : defaultCenter;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      center,
      zoom: userLocation ? 15.5 : 12,
      style: 'mapbox://styles/mapbox/dark-v11',
      attributionControl: false
    });
    mapRef.current = map;

    map.on('load', () => {
      setIsMapReady(true);
      onMapLoad?.(map);
    });

    map.on('error', (e) => console.error('Mapbox error:', e));

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onMapLoad, userLocation]);

  // Close popup on map click and on Escape
  useEffect(() => {
    if (!mapRef.current || !isMapReady || !mapContainer.current) return;
    const m = mapRef.current;
    const container = mapContainer.current;
    
    // Additional safety check - ensure map is fully initialized
    if (!m.getCanvas || !m.getCanvasContainer) {
      return;
    }

    let touchStartTime = 0;
    let touchStartPos = { x: 0, y: 0 };
    let isDragging = false;

    const handleMapClick = (e: any) => {
      // Check if clicking on map canvas or container
      const canvas = m.getCanvas();
      const canvasContainer = m.getCanvasContainer();
      
      // Safety check - ensure canvas and container exist
      if (!canvas || !canvasContainer) {
        return;
      }
      
      // Handle different target types
      let isMapClick = false;
      
      if (e.target === canvas || e.target === canvasContainer) {
        isMapClick = true;
      } else if (e.target && typeof e.target.nodeType === 'number' && canvasContainer.contains(e.target)) {
        isMapClick = true;
      } else if (e.target && e.target.className && e.target.className.includes('mapboxgl-canvas')) {
        isMapClick = true;
      }
      
      if (isMapClick) {
        setActiveRestaurantId(null);
        onRestaurantDeselect?.();
        
        // If deck is active, close it on map tap
        if (isDeckActive) {
          onDeckClose?.();
        }
      }
    };

    const handleTouchStart = (e: any) => {
      touchStartTime = Date.now();
      if (e.touches && e.touches[0]) {
        touchStartPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
      isDragging = false;
    };

    const handleTouchMove = (e: any) => {
      if (e.touches && e.touches[0]) {
        const deltaX = Math.abs(e.touches[0].clientX - touchStartPos.x);
        const deltaY = Math.abs(e.touches[0].clientY - touchStartPos.y);
        if (deltaX > 10 || deltaY > 10) {
          isDragging = true;
        }
      }
    };

    const handleTouchEnd = (e: any) => {
      const touchDuration = Date.now() - touchStartTime;
      const isQuickTap = touchDuration < 300 && !isDragging;
      
      if (isQuickTap && isDeckActive) {
        // Quick tap on map when deck is active - close the deck
        onDeckClose?.();
      }
    };
    
    // Listen to mouse clicks for desktop
    m.on('click', handleMapClick);
    
    // Listen to touch events for mobile with proper tap detection
    m.on('touchstart', handleTouchStart);
    m.on('touchmove', handleTouchMove);
    m.on('touchend', handleTouchEnd);
    
    // Also listen to the container for additional coverage
    container.addEventListener('click', handleMapClick);
    container.addEventListener('touchstart', handleTouchStart);
    container.addEventListener('touchmove', handleTouchMove);
    container.addEventListener('touchend', handleTouchEnd);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveRestaurantId(null);
        onRestaurantDeselect?.();
        if (isDeckActive) {
          onDeckClose?.();
        }
      }
    };
    window.addEventListener('keydown', onKey);

    return () => {
      m.off('click', handleMapClick);
      m.off('touchstart', handleTouchStart);
      m.off('touchmove', handleTouchMove);
      m.off('touchend', handleTouchEnd);
      container.removeEventListener('click', handleMapClick);
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchmove', handleTouchMove);
      container.removeEventListener('touchend', handleTouchEnd);
      window.removeEventListener('keydown', onKey);
    };
  }, [isMapReady, isDeckActive, onDeckClose]);

  // Center on user and show a simple user-location marker
  useEffect(() => {
    if (!mapRef.current || !isMapReady || !userLocation) return;
    const map = mapRef.current;
    const center: [number, number] = [userLocation.longitude, userLocation.latitude];

    map.flyTo({ center, zoom: 15.5, essential: true });

    const userMarker = new mapboxgl.Marker({ color: '#3b82f6', scale: 1.2 })
      .setLngLat(center)
      .addTo(map);

    return () => {
      userMarker.remove();
    };
  }, [userLocation, isMapReady]);

  // Show only selected restaurant and zoom to it
  useEffect(() => {
    if (selectedRestaurant) {
      setRestaurants([selectedRestaurant]);
      
      // Only auto-select if deck is not active (deck navigation should not show popup)
      if (!isDeckActive) {
        setActiveRestaurantId(selectedRestaurant.id);
      }
      
      // Zoom to the selected restaurant
      if (mapRef.current && isMapReady) {
        const map = mapRef.current;
        const center: [number, number] = [selectedRestaurant.location.lng, selectedRestaurant.location.lat];
        map.flyTo({ 
          center, 
          zoom: 16, 
          essential: true,
          duration: 1500
        });
      }
    } else {
      setRestaurants([]);
      setActiveRestaurantId(null);
    }
  }, [selectedRestaurant, isMapReady, isDeckActive]);

  // Clear active id if the restaurant list no longer contains it
  useEffect(() => {
    if (!activeRestaurantId) return;
    if (!restaurants.some((r) => r.id === activeRestaurantId)) setActiveRestaurantId(null);
  }, [restaurants, activeRestaurantId]);

  // Track map position changes to determine if user has moved away from their location
  useEffect(() => {
    if (!mapRef.current || !isMapReady || !userLocation || !onViewChange) return;
    
    const map = mapRef.current;
    const THRESHOLD_DISTANCE = 100; // 100 meters threshold
    
    const checkDistanceFromUser = () => {
      const center = map.getCenter();
      const distance = calculateDistance(
        userLocation.latitude,
        userLocation.longitude,
        center.lat,
        center.lng
      );
      
      const isAwayFromUser = distance > THRESHOLD_DISTANCE;
      onViewChange(isAwayFromUser);
    };
    
    // Check initial distance
    checkDistanceFromUser();
    
    // Listen for map move events
    map.on('moveend', checkDistanceFromUser);
    map.on('zoomend', checkDistanceFromUser);
    
    return () => {
      map.off('moveend', checkDistanceFromUser);
      map.off('zoomend', checkDistanceFromUser);
    };
  }, [isMapReady, userLocation, onViewChange]);


  return (
    <div 
      ref={mapContainer} 
      className="map-container"
      style={{ width: '100%', height: '100vh' }}
    >
      {isMapReady &&
        mapRef.current &&
        restaurants.map((r) => (
          <RestaurantMarker
            key={r.id}
            map={mapRef.current!}
            restaurant={r}
            isActive={activeRestaurantId === r.id}
            isDeckActive={isDeckActive}
            onClick={() => {
              if (isDeckActive) {
                // If deck is active, do nothing - markers are purely visual
                return;
              } else {
                // Normal behavior: toggle popup
                setActiveRestaurantId(activeRestaurantId === r.id ? null : r.id);
              }
            }}
          />
        ))}
    </div>
  );
}