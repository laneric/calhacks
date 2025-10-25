'use client';

import React from 'react';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface LoadingOverlayProps {
  isVisible: boolean;
}

export default function LoadingOverlay({ isVisible }: LoadingOverlayProps) {
  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 z-20 pointer-events-none">
      {/* Floating magnifying glass icon */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div 
          className="w-12 h-12 bg-transparent rounded-full shadow-lg flex items-center justify-center animate-pulse"
          style={{
            animation: 'hover 2.5s ease-in-out infinite',
          }}
        >
          <MagnifyingGlassIcon className="size-12 text-black stroke-2" />
        </div>
      </div>
      
      {/* Add custom keyframes for hovering animation */}
      <style jsx>{`
        @keyframes hover {
          0%, 100% { 
            transform: translateY(0px) translateX(0px); 
          }
          25% { 
            transform: translateY(-10px) translateX(10px); 
          }
          50% { 
            transform: translateY(-3px) translateX(-8px); 
          }
          75% { 
            transform: translateY(-12px) translateX(2px); 
          }
        }
      `}</style>
    </div>
  );
}
