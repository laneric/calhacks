'use client';

import React, { useRef, useEffect, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { Restaurant, RestaurantResponse } from '../libs/types';
import RestaurantMarker from './RestaurantMarker';
import 'mapbox-gl/dist/mapbox-gl.css';

interface MapProps {
  userLocation?: { latitude: number; longitude: number; accuracy?: number } | null;
  onMapLoad?: (map: mapboxgl.Map) => void;
}

export default function Map({ userLocation, onMapLoad }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  const [isMapReady, setIsMapReady] = useState(false);
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [activeRestaurantId, setActiveRestaurantId] = useState<string | null>(null);

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
    if (!mapRef.current || !isMapReady) return;
    const m = mapRef.current;

    const handleMapClick = () => setActiveRestaurantId(null);
    m.on('click', handleMapClick);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setActiveRestaurantId(null);
    };
    window.addEventListener('keydown', onKey);

    return () => {
      m.off('click', handleMapClick);
      window.removeEventListener('keydown', onKey);
    };
  }, [isMapReady]);

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

  // Fetch restaurants near user
  useEffect(() => {
    const fetchRestaurants = async (lat: number, lng: number, radius = 5000) => {
      try {
        const res = await fetch(`/api/restaurants?lat=${lat}&lng=${lng}&radius=${radius}&limit=20`);
        if (!res.ok) throw new Error(`Failed to fetch restaurants: ${res.status}`);
        const data: RestaurantResponse = await res.json();
        setRestaurants(data.restaurants);
      } catch (err) {
        console.error('Error fetching restaurants:', err);
      }
    };

    if (userLocation && isMapReady) {
      fetchRestaurants(userLocation.latitude, userLocation.longitude);
    }
  }, [userLocation, isMapReady]);

  // Clear active id if the restaurant list no longer contains it
  useEffect(() => {
    if (!activeRestaurantId) return;
    if (!restaurants.some((r) => r.id === activeRestaurantId)) setActiveRestaurantId(null);
  }, [restaurants, activeRestaurantId]);

  return (
    <div ref={mapContainer} className="map-container">
      {isMapReady &&
        mapRef.current &&
        restaurants.map((r) => (
          <RestaurantMarker
            key={r.id}
            map={mapRef.current!}
            restaurant={r}
            isActive={activeRestaurantId === r.id}
            onClick={() => setActiveRestaurantId(r.id)}
          />
        ))}
    </div>
  );
}