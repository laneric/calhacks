'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Restaurant } from '../libs/types';
import { formatDistanceShort } from '../libs/distance';
import { 
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
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const carouselRef = useRef<HTMLDivElement>(null);

  // Show deck with animation
  useEffect(() => {
    if (restaurants.length > 0 && externalIsVisible) {
      setIsVisible(true);
    } else if (!externalIsVisible) {
      setIsVisible(false);
    }
  }, [restaurants, externalIsVisible]);

  // Update selected restaurant when index changes
  useEffect(() => {
    if (restaurants[currentIndex]) {
      onRestaurantSelect(restaurants[currentIndex]);
    }
  }, [currentIndex, restaurants, onRestaurantSelect]);


  const goToPrevious = useCallback(() => {
    if (currentIndex > 0 && !isTransitioning) {
      setIsTransitioning(true);
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  }, [currentIndex, isTransitioning]);

  const goToNext = useCallback(() => {
    if (currentIndex < restaurants.length - 1 && !isTransitioning) {
      setIsTransitioning(true);
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  }, [currentIndex, isTransitioning, restaurants.length]);

  const goToIndex = useCallback((index: number) => {
    if (index !== currentIndex && !isTransitioning && index >= 0 && index < restaurants.length) {
      setIsTransitioning(true);
      setCurrentIndex(index);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  }, [currentIndex, isTransitioning, restaurants.length]);

  // Touch handlers for swipe gestures
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > 50;
    const isRightSwipe = distance < -50;

    if (isLeftSwipe) {
      goToNext();
    } else if (isRightSwipe) {
      goToPrevious();
    }
  };

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsVisible(false);
      onClose();
    }, 400);
  };

  if (!isVisible || restaurants.length === 0) {
    return null;
  }

  const RestaurantCard = ({ restaurant, index }: { restaurant: Restaurant; index: number }) => (
    <div
      className="absolute inset-0 transition-all duration-300 ease-out"
      style={{
        transform: `translateX(${(index - currentIndex) * 100}%)`,
        opacity: index === currentIndex ? 1 : 0,
        zIndex: index === currentIndex ? 10 : 1,
      }}
    >
      <div className="bg-neutral-950/50 backdrop-blur-md rounded-2xl shadow-2xl border border-white/30 overflow-hidden h-full">
        <div className="p-4 h-full flex flex-col">
          {/* Restaurant Name and Cuisine */}
          <div className="mb-2">
            <h3 className="text-lg font-bold text-white leading-tight">
              {restaurant.name}
            </h3>
            {restaurant.cuisine && restaurant.cuisine.length > 0 ? (
              <p className="text-white/80 text-sm">
                {restaurant.cuisine.join(', ')}
              </p>
            ) : (
              <p className="text-white/60 text-sm">
                Restaurant
              </p>
            )}
          </div>

          {/* Rating and Distance */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <StarIcon className="size-4 text-yellow-500" />
              <span className="text-white font-semibold text-sm">
                {restaurant.rating?.toFixed(1) || 'N/A'}
              </span>
            </div>
            •
            <span className="text-white/70 text-sm">
              {formatDistanceShort(restaurant.distanceMeters)} away
            </span>
          </div>

          {/* Address */}
          <div className="flex items-start gap-1 mb-2">
            <MapPinIcon className="size-4 text-white/60 mt-0.5 shrink-0" />
            <span className="text-white/80 text-sm leading-relaxed">
              {restaurant.address || 'Address not available'}
            </span>
          </div>

          {/* Allergen Tags */}
          <div className="mt-auto">
            {restaurant.summaryAllergenProfile && Object.keys(restaurant.summaryAllergenProfile).length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {Object.entries(restaurant.summaryAllergenProfile)
                  .filter(([_, probability]) => probability > 0.5)
                  .map(([allergen, _]) => (
                    <span
                      key={allergen}
                      className="px-2 py-1 bg-green-500/20 text-green-300 text-xs rounded-full border border-green-500/30"
                    >
                      {allergen.replace('_', ' ')}
                    </span>
                  ))}
              </div>
            ) : (
              <span className="text-white/60 text-xs">
                No allergen info available.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div 
      className={`fixed bottom-32 left-1/2 -translate-x-1/2 w-80 max-w-[calc(100vw-60px)] z-30 transition-all duration-100 ease-in-out ${
        isClosing ? 'opacity-0 translate-y-12' : 'opacity-100 translate-y-0'
      }`}
      style={{
        transition: 'all 0.1s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
    >
      <div className="relative">

        <div 
          ref={carouselRef}
          className="relative h-40 overflow-hidden rounded-2xl"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          {restaurants.map((restaurant, index) => (
            <RestaurantCard
              key={restaurant.id}
              restaurant={restaurant}
              index={index}
            />
          ))}
        </div>

        <button
          onClick={goToPrevious}
          disabled={currentIndex === 0 || isTransitioning}
          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-14 z-40 w-10 h-10 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center hover:bg-white/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeftIcon className="size-5 text-white" />
        </button>

        <button
          onClick={goToNext}
          disabled={currentIndex === restaurants.length - 1 || isTransitioning}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-14 z-40 w-10 h-10 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center hover:bg-white/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRightIcon className="size-5 text-white" />
        </button>

        {restaurants.length > 1 && (
          <div className="flex justify-center gap-2 mt-4">
            {restaurants.map((_, index) => (
              <button
                key={index}
                onClick={() => goToIndex(index)}
                className={`w-2 h-2 rounded-full transition-all duration-200 ${
                  index === currentIndex 
                    ? 'bg-white' 
                    : 'bg-white/40 hover:bg-white/60'
                }`}
                disabled={isTransitioning}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
