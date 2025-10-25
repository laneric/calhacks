'use client';

import { useEffect, useRef, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import { createPortal } from 'react-dom';
import { BuildingStorefrontIcon, StarIcon, MapPinIcon } from '@heroicons/react/24/solid';
import type { Restaurant } from '../libs/types';

type Props = {
  map: mapboxgl.Map;
  restaurant: Restaurant;
  isActive?: boolean;
  onClick?: (r: Restaurant) => void;
};

/** Small badge used as the marker element */
function MarkerBadge({ active }: { active?: boolean }) {
  return (
    <div
      className={[
        'inline-flex h-10 w-10 items-center justify-center rounded-full border bg-orange-500 text-white shadow-lg',
        'cursor-pointer transition-transform duration-200 hover:scale-110',
        active ? 'ring-4 ring-white/60' : 'border-white'
      ].join(' ')}
      role="button"
      aria-label="Restaurant marker"
    >
      <BuildingStorefrontIcon className="h-5 w-5" />
    </div>
  );
}

/** Card shown inside the popup */
function PopupCard({ r }: { r: Restaurant }) {
  const cuisines = useMemo(() => r.cuisine?.join(', ') || 'Restaurant', [r.cuisine]);
  const distance = useMemo(
    () => (r.distanceMeters ? `${Math.round(r.distanceMeters)}m away` : null),
    [r.distanceMeters]
  );

  return (
    <div className="w-64 max-w-xs rounded-xl bg-white p-4 text-gray-900 shadow-lg">
      <div className="mb-1 flex items-start justify-between gap-2">
        <h3 className="line-clamp-2 text-base font-semibold">{r.name}</h3>
        <MapPinIcon className="h-4 w-4 shrink-0 text-gray-400" />
      </div>
      <div className="mb-2 flex items-center gap-1 text-sm">
        <StarIcon className="h-4 w-4 text-yellow-500" />
        <span className="font-medium text-gray-800">{r.rating ?? 'N/A'}</span>
        <span className="text-gray-400">•</span>
        <span className="italic text-gray-600">{cuisines}</span>
      </div>
      {distance && <div className="text-xs text-gray-500">{distance}</div>}
      {r.address && <div className="mt-2 text-xs leading-relaxed text-gray-600">{r.address}</div>}
    </div>
  );
}

export default function RestaurantMarker({ map, restaurant, isActive, onClick }: Props) {
  const markerRef = useRef<mapboxgl.Marker | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);

  // DOM nodes that React will render into, handed to Mapbox
  const markerElRef = useRef<HTMLDivElement | null>(null);
  const popupElRef = useRef<HTMLDivElement | null>(null);

  // Create marker and popup instances
  useEffect(() => {
    // Create container nodes if they don't exist
    if (!markerElRef.current) markerElRef.current = document.createElement('div');
    if (!popupElRef.current) popupElRef.current = document.createElement('div');

    console.log('Creating marker for restaurant:', restaurant.name, 'at', restaurant.location);

    // Marker
    markerRef.current = new mapboxgl.Marker(markerElRef.current)
      .setLngLat([restaurant.location.lng, restaurant.location.lat])
      .addTo(map);

    // Popup shell (content via portal)
    popupRef.current = new mapboxgl.Popup({ closeOnClick: false, offset: 16, maxWidth: '280px' });

    // Notify parent on click; parent will toggle isActive
    const handleClick = (e: Event) => {
      e.stopPropagation();
      onClick?.(restaurant);
    };
    markerElRef.current.addEventListener('click', handleClick);

    return () => {
      markerElRef.current?.removeEventListener('click', handleClick);
      popupRef.current?.remove();
      markerRef.current?.remove();
      popupRef.current = null;
      markerRef.current = null;
    };
  }, [map, restaurant.id, restaurant.location.lat, restaurant.location.lng, onClick]);

  // Drive popup visibility from isActive
  useEffect(() => {
    if (!popupRef.current || !popupElRef.current) return;

    if (isActive) {
      popupRef.current
        .setLngLat([restaurant.location.lng, restaurant.location.lat])
        .setDOMContent(popupElRef.current)
        .addTo(map);
    } else {
      popupRef.current.remove();
    }
  }, [isActive, map, restaurant.location.lng, restaurant.location.lat]);

  if (!markerElRef.current || !popupElRef.current) return null;

  return (
    <>
      {createPortal(<MarkerBadge active={isActive} />, markerElRef.current)}
      {createPortal(<PopupCard r={restaurant} />, popupElRef.current)}
    </>
  );
}