'use client';

import React, { useState, useEffect } from 'react';
import { Restaurant } from '../libs/types';
import { formatDistanceShort } from '../libs/distance';
import { 
  XMarkIcon, 
  ChevronLeftIcon, 
  ChevronRightIcon,
  StarIcon,
  MapPinIcon
} from '@heroicons/react/24/solid';

interface RestaurantCardDeckProps {
  restaurants: Restaurant[];
  onClose: () => void;
  onRestaurantSelect: (restaurant: Restaurant) => void;
  isVisible?: boolean;
}

export default function RestaurantCardDeck({ 
  restaurants, 
  onClose, 
  onRestaurantSelect,
  isVisible: externalIsVisible = true
}: RestaurantCardDeckProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  // Show deck with animation
  useEffect(() => {
    if (restaurants.length > 0 && externalIsVisible) {
      setIsVisible(true);
    } else if (!externalIsVisible) {
      setIsVisible(false);
    }
  }, [restaurants, externalIsVisible]);

  const currentRestaurant = restaurants[currentIndex];



  const goToPrevious = () => {
    if (currentIndex > 0) {
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      onRestaurantSelect(restaurants[newIndex]);
    }
  };

  const goToNext = () => {
    if (currentIndex < restaurants.length - 1) {
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      onRestaurantSelect(restaurants[newIndex]);
    }
  };

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsVisible(false);
      onClose();
    }, 400); // Wait for animation to complete
  };

  if (!isVisible || restaurants.length === 0) {
    return null;
  }

  return (
    <div 
      className={`fixed bottom-32 left-[30px] right-[30px] md:left-1/2 md:-translate-x-1/2 md:w-2/6 z-30 transition-all duration-100 ease-in-out ${
        isClosing ? 'opacity-0 translate-y-12' : 'opacity-100 translate-y-0'
      }`}
      style={{
        transition: 'all 0.1s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
    >
      <div className="bg-neutral-950/50 backdrop-blur-md rounded-2xl shadow-2xl border border-white/30 overflow-hidden">
        {/* Header with navigation */}
        <div className="bg-neutral-800/50 p-4 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={goToPrevious}
                disabled={currentIndex === 0}
                className="p-1 rounded-full hover:bg-white/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeftIcon className="size-5" />
              </button>
              
              <div className="text-center">
                <span className="text-sm text-white/70">
                  {currentIndex + 1} of {restaurants.length}
                </span>
              </div>
              
              <button
                onClick={goToNext}
                disabled={currentIndex === restaurants.length - 1}
                className="p-1 rounded-full hover:bg-white/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRightIcon className="size-5" />
              </button>
            </div>
            
            <button
              onClick={handleClose}
              className="p-1 rounded-full hover:bg-white/20 transition-colors"
            >
              <XMarkIcon className="size-5" />
            </button>
          </div>
        </div>

        {/* Card Content */}
        <div className="p-5">
          <div className="space-y-1">
            {/* Restaurant Name and Cuisine */}
            <div className="mb-3">
              <h3 className="text-xl font-bold text-white">
                {currentRestaurant.name}
              </h3>
              {currentRestaurant.cuisine && currentRestaurant.cuisine.length > 0 ? (
                <p className="text-white/80 text-base">
                  {currentRestaurant.cuisine.join(', ')}
                </p>
              ) : (
                <p className="text-white/60 text-base">
                  Restaurant
                </p>
              )}
            </div>

            {/* Rating and Distance */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <StarIcon className="size-5 text-yellow-500" />
                <span className="text-white font-semibold text-base">
                  {currentRestaurant.rating?.toFixed(1) || 'N/A'}
                </span>
              </div>
              •
              <span className="text-white/70 text-base">
                {formatDistanceShort(currentRestaurant.distanceMeters)} away
              </span>
            </div>

            {/* Address */}
            <div className="flex items-start gap-2">
              <MapPinIcon className="size-5 text-white/60 mt-0.5 shrink-0" />
              <span className="text-white/80 text-base leading-relaxed">
                {currentRestaurant.address || 'Address not available'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
