'use client';

import { useEffect, useRef, useMemo } from 'react';
import mapboxgl from 'mapbox-gl';
import { createPortal } from 'react-dom';
import { BuildingStorefrontIcon, StarIcon, MapPinIcon, XMarkIcon } from '@heroicons/react/24/solid';
import type { Restaurant } from '../libs/types';
import { formatDistance } from '../libs/distance';

type Props = {
  map: mapboxgl.Map;
  restaurant: Restaurant;
  isActive?: boolean;
  onClick?: (r: Restaurant) => void;
  isDeckActive?: boolean;
};

/** Small badge used as the marker element */
function MarkerBadge({ active, isDeckActive }: { active?: boolean; isDeckActive?: boolean }) {
  return (
    <div
      className={[
        'inline-flex h-10 w-10 items-center justify-center rounded-full border bg-orange-500 text-white shadow-lg',
        isDeckActive 
          ? 'cursor-default opacity-80' 
          : 'cursor-pointer transition-transform duration-200 hover:scale-110',
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
function PopupCard({ r, onClose }: { r: Restaurant; onClose?: () => void }) {
  const cuisines = useMemo(() => r.cuisine?.join(', ') || 'Restaurant', [r.cuisine]);
  const distance = useMemo(
    () => (r.distanceMeters ? `${formatDistance(r.distanceMeters)} away` : null),
    [r.distanceMeters]
  );

  return (
    <div 
      className="w-64 max-w-xs rounded-xl bg-neutral-900/80 backdrop-blur-sm border border-white/20 p-4 text-white"
      onClick={(e) => e.stopPropagation()} // Prevent popup from closing when clicking inside
    >
      <div className="mb-1 flex items-start justify-between gap-2">
        <h3 className="line-clamp-2 text-base font-semibold text-white">{r.name}</h3>
        <div className="flex items-center gap-2">
          {/* {onClose && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Close popup"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          )} */}
        </div>
      </div>
      <div className="mb-2 flex items-center gap-1 text-sm">
        <StarIcon className="h-4 w-4 text-yellow-500" />
        <span className="font-medium text-white">{r.rating ?? 'N/A'}</span>
        <span className="text-gray-400">•</span>
        <span className="italic text-gray-300">{cuisines}</span>
      </div>
      {distance && <div className="text-xs text-gray-300">{distance}</div>}
      <div className="flex items-center gap-1">
      <MapPinIcon className="h-4 w-4 shrink-0 text-gray-400" />
      {r.address && <div className="text-xs leading-relaxed text-gray-300">{r.address}</div>}
      </div>
    </div>
  );
}

export default function RestaurantMarker({ map, restaurant, isActive, onClick, isDeckActive }: Props) {
  const markerRef = useRef<mapboxgl.Marker | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);

  // DOM nodes that React will render into, handed to Mapbox
  const markerElRef = useRef<HTMLDivElement | null>(null);
  const popupElRef = useRef<HTMLDivElement | null>(null);

  // Create container nodes immediately on mount
  if (!markerElRef.current) markerElRef.current = document.createElement('div');
  if (!popupElRef.current) popupElRef.current = document.createElement('div');

  // Create marker and popup instances
  useEffect(() => {
    if (!markerElRef.current) return;

    // Marker
    markerRef.current = new mapboxgl.Marker(markerElRef.current)
      .setLngLat([restaurant.location.lng, restaurant.location.lat])
      .addTo(map);

    // Popup shell (content via portal)
    popupRef.current = new mapboxgl.Popup({ 
      closeOnClick: false, 
      closeButton: false,  // Disable Mapbox's built-in close button
      offset: [0, -80], // Position above marker, centered between topbar and deck
      maxWidth: '280px',
      className: 'custom-popup'  // Add custom class for styling
    });

    // Notify parent on click; parent will toggle isActive
    const handleClick = (e: Event) => {
      e.stopPropagation();
      e.preventDefault();
      onClick?.(restaurant);
    };
    markerElRef.current.addEventListener('click', handleClick);
    markerElRef.current.addEventListener('mousedown', handleClick);
    markerElRef.current.addEventListener('touchstart', handleClick);

    return () => {
      markerElRef.current?.removeEventListener('click', handleClick);
      markerElRef.current?.removeEventListener('mousedown', handleClick);
      markerElRef.current?.removeEventListener('touchstart', handleClick);
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

  if (!markerElRef.current || !popupElRef.current) {
    return null;
  }

  return (
    <>
      {createPortal(<MarkerBadge active={isActive} isDeckActive={isDeckActive} />, markerElRef.current)}
      {createPortal(
        <PopupCard 
          r={restaurant} 
          onClose={() => onClick?.(restaurant)} 
        />, 
        popupElRef.current
      )}
    </>
  );
}