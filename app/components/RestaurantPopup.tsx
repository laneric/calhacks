'use client';

import React from 'react';
import { Restaurant } from '../libs/types';
import { formatDistance } from '../libs/distance';
import { XMarkIcon, StarIcon, MapPinIcon, PhoneIcon, GlobeAltIcon } from '@heroicons/react/24/solid';

interface RestaurantPopupProps {
  restaurant: Restaurant;
  onClose: () => void;
}

export default function RestaurantPopup({ restaurant, onClose }: RestaurantPopupProps) {

  const formatAllergenProfile = (profile?: Record<string, number>) => {
    if (!profile) return null;
    
    const allergens = Object.entries(profile)
      .filter(([_, risk]) => risk > 0.3) // Only show allergens with >30% risk
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3); // Show top 3 allergens
    
    if (allergens.length === 0) return null;
    
    return (
      <div className="flex flex-wrap gap-1 mt-2">
        {allergens.map(([allergen, risk]) => (
          <span
            key={allergen}
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              risk > 0.7 
                ? 'bg-red-100 text-red-800' 
                : risk > 0.5 
                ? 'bg-yellow-100 text-yellow-800' 
                : 'bg-green-100 text-green-800'
            }`}
          >
            {allergen} ({Math.round(risk * 100)}%)
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed bottom-30 left-[30px] right-[30px] md:left-1/2 md:-translate-x-1/2 md:w-2/6 z-30">
      <div className="bg-neutral-950/50 backdrop-blur-md rounded-2xl shadow-2xl border border-white/30 overflow-hidden">
        {/* Header */}
        <div className="bg-neutral-800/50 p-4 text-white">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-bold truncate">{restaurant.name}</h3>
              {restaurant.cuisine && (
                <p className="text-white text-sm mt-1">
                  {restaurant.cuisine.join(', ')}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="ml-3 p-1 rounded-full hover:bg-white/20 transition-colors"
            >
              <XMarkIcon className="size-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Rating and Distance */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1">
              <StarIcon className="size-4 text-yellow-500" />
              <span className="font-medium">{restaurant.rating?.toFixed(1) || 'N/A'}</span>
            </div>
            {restaurant.distanceMeters && (
              <span className="text-sm text-gray-600">
                {formatDistance(restaurant.distanceMeters)} away
              </span>
            )}
          </div>

          {/* Address */}
          {restaurant.address && (
            <div className="flex items-start gap-1 mb-3">
              <MapPinIcon className="size-4 text-neutral-300 mt-0.5 shrink-0" />
              <span className="text-sm text-neutral-300">{restaurant.address}</span>
            </div>
          )}

          {/* Allergen Profile */}
          {formatAllergenProfile(restaurant.summaryAllergenProfile)}

          {/* Contact Info */}
          {(restaurant.phone || restaurant.website) && (
            <div className="flex gap-3 mt-4 pt-3 -mx-6 px-6 border-t border-white/30">
              {restaurant.phone && (
                <a
                  href={`tel:${restaurant.phone}`}
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <PhoneIcon className="size-4" />
                  Call
                </a>
              )}
              {restaurant.website && (
                <a
                  href={restaurant.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <GlobeAltIcon className="size-4" />
                  Website
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
