'use client';

import React, { useState, useEffect } from 'react';
import { SparklesIcon } from '@heroicons/react/24/solid';

interface LoadingOverlayProps {
  isVisible: boolean;
}

const loadingMessages = [
  "Discovering hidden gems near you...",
  "Finding the perfect spot for your taste...",
  "Exploring local culinary treasures...",
  "Searching for your next favorite meal...",
  "Uncovering the best kept secrets...",
  "Scanning for amazing restaurants...",
  "Hunting down delicious discoveries...",
  "Finding places that'll make your day...",
  "Discovering flavors you'll love...",
  "Searching for your perfect dining spot..."
];

export default function LoadingOverlay({ isVisible }: LoadingOverlayProps) {
  const [currentMessage, setCurrentMessage] = useState('');
  const [messageIndex, setMessageIndex] = useState(0);

  // Set initial message and cycle through them
  useEffect(() => {
    if (!isVisible) return;
    
    // Set initial message
    setCurrentMessage(loadingMessages[messageIndex]);
    
    // Cycle through messages every 2 seconds
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % loadingMessages.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [isVisible, messageIndex]);

  // Update current message when index changes
  useEffect(() => {
    if (isVisible) {
      setCurrentMessage(loadingMessages[messageIndex]);
    }
  }, [messageIndex, isVisible]);

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 z-20 pointer-events-none">
      {/* Prompt-style loading box */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative">
          {/* Main prompt box */}
          <div 
            className="bg-neutral-950/20 backdrop-blur-sm rounded-full shadow-md border border-white/30 px-4 py-2 min-w-[320px] max-w-[480px] mx-4"
            style={{
              animation: 'hover 5s ease-in-out infinite',
            }}
          >
            <div className="flex items-center gap-2">
              {/* Sparkles icon */}
              <div className="shrink-0 z-10 ml-1">
                <SparklesIcon className="size-5 text-white" />
              </div>
              
              {/* Message text */}
              <div className="flex-1 min-w-0">
                <div className="text-white text-md font-medium leading-relaxed">
                  {currentMessage}
                </div>
              </div>
            </div>
          </div>
          
          {/* Subtle glow effect */}
          <div className="absolute inset-0 bg-linear-to-r from-amber-400/20 via-orange-400/20 to-amber-400/20 rounded-full blur-xl -z-10 animate-pulse"></div>
        </div>
      </div>
      
      {/* Add custom keyframes for hovering animation */}
      <style jsx>{`
        @keyframes hover {
          0%, 100% { 
            transform: translateY(0px) translateX(0px); 
          }
          12.5% { 
            transform: translateY(-25px) translateX(18px); 
          }
          25% { 
            transform: translateY(-35px) translateX(-15px); 
          }
          37.5% { 
            transform: translateY(-8px) translateX(22px); 
          }
          50% { 
            transform: translateY(-28px) translateX(-8px); 
          }
          62.5% { 
            transform: translateY(-18px) translateX(25px); 
          }
          75% { 
            transform: translateY(-32px) translateX(-12px); 
          }
          87.5% { 
            transform: translateY(-12px) translateX(15px); 
          }
        }
      `}</style>
    </div>
  );
}
