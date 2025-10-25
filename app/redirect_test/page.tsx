'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPinIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  LinkIcon,
  BeakerIcon,
  ClockIcon,
  DocumentTextIcon,
  StarIcon
} from '@heroicons/react/24/solid';

// types for streaming events
interface MetadataEvent {
  type: 'metadata';
  query: { lat: number; lng: number; radius: number; research_limit: number };
  total_found: number;
  total_to_research: number;
}

interface ResearchedRestaurant {
  id: string;
  name: string;
  location: { lat: number; lng: number };
  distanceMeters: number;
  cuisine: string[];
  address: string;
  amenity_type: string;
  research: {
    status: 'success' | 'failed';
    content: string;
    citations: Citation[];
    reasoning_steps: string[];
    timestamp: string;
    error: string | null;
  };
}

interface Citation {
  title: string;
  url: string;
  start_index?: number;
  end_index?: number;
}

interface ResearchedRestaurantEvent {
  type: 'restaurant_researched';
  index: number;
  data: ResearchedRestaurant;
}

interface SimpleRestaurant {
  id: string;
  name: string;
  location: { lat: number; lng: number };
  distanceMeters: number;
  cuisine: string[];
  address: string;
  amenity_type: string;
}

interface NonResearchedBatchEvent {
  type: 'restaurants_without_research';
  data: SimpleRestaurant[];
}

interface CompleteEvent {
  type: 'complete';
}

interface ErrorEvent {
  type: 'error';
  error: string;
}

type StreamEvent = MetadataEvent | ResearchedRestaurantEvent | NonResearchedBatchEvent | CompleteEvent | ErrorEvent;

// config
const STREAM_CONFIG = {
  flaskUrl: 'http://localhost:5001',
  radius: 5000,
  researchLimit: 5,
  reconnectDelay: 3000
};

// utility to format distance
function formatDistance(meters?: number): string {
  if (!meters && meters !== 0) return 'N/A';
  if (meters < 1000) return `${Math.round(meters)}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}

// collapsible reasoning steps component
function ReasoningSteps({ steps }: { steps: string[] }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="mt-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-white/70 hover:text-white transition-colors"
      >
        {isOpen ? (
          <ChevronUpIcon className="size-4" />
        ) : (
          <ChevronDownIcon className="size-4" />
        )}
        <span className="text-sm font-medium">
          {isOpen ? 'Hide' : 'Show'} Reasoning Steps ({steps.length})
        </span>
      </button>

      {isOpen && (
        <ol className="mt-3 space-y-2 list-decimal list-inside">
          {steps.map((step, idx) => (
            <li key={idx} className="text-white/60 text-sm leading-relaxed">
              {step}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// researched restaurant card
function ResearchedRestaurantCard({ restaurant }: { restaurant: ResearchedRestaurant }) {
  const { research } = restaurant;
  const isSuccess = research.status === 'success';

  return (
    <article className="bg-neutral-800/50 backdrop-blur-md rounded-2xl border border-white/20 shadow-2xl p-6 space-y-4">
      {/* header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white mb-1">
            {restaurant.name}
          </h3>
          {restaurant.cuisine && restaurant.cuisine.length > 0 ? (
            <p className="text-white/70 text-sm">
              {restaurant.cuisine.join(', ')}
            </p>
          ) : (
            <p className="text-white/50 text-sm">
              {restaurant.amenity_type === 'fast_food' ? 'Fast Food' : 'Restaurant'}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isSuccess ? (
            <CheckCircleIcon className="size-6 text-green-500" />
          ) : (
            <XCircleIcon className="size-6 text-red-500" />
          )}
        </div>
      </div>

      {/* distance and address */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-white/60 text-sm">
          <MapPinIcon className="size-4" />
          <span>{formatDistance(restaurant.distanceMeters)} away</span>
        </div>
        <div className="text-white/60 text-sm">
          {restaurant.address || 'Address not available'}
        </div>
      </div>

      {/* research content */}
      {isSuccess ? (
        <>
          <div className="border-t border-white/10 pt-4">
            <div className="flex items-center gap-2 mb-3">
              <DocumentTextIcon className="size-5 text-blue-400" />
              <h4 className="text-white font-semibold">Research Findings</h4>
            </div>

            <div className="prose prose-invert max-w-none">
              <p className="text-white/90 whitespace-pre-wrap leading-relaxed text-sm">
                {research.content}
              </p>
            </div>
          </div>

          {/* citations */}
          {research.citations && research.citations.length > 0 && (
            <div className="border-t border-white/10 pt-4">
              <h4 className="text-white/70 font-semibold text-sm mb-2">Sources:</h4>
              <div className="space-y-2">
                {research.citations.map((citation, idx) => (
                  <a
                    key={idx}
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-2 text-blue-400 hover:text-blue-300 transition-colors text-sm group"
                  >
                    <LinkIcon className="size-4 mt-0.5 shrink-0" />
                    <span className="group-hover:underline break-all">
                      {citation.title || citation.url}
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* reasoning steps */}
          <ReasoningSteps steps={research.reasoning_steps} />

          {/* timestamp */}
          {research.timestamp && (
            <div className="flex items-center gap-2 text-white/40 text-xs">
              <ClockIcon className="size-3" />
              <span>{new Date(research.timestamp).toLocaleString()}</span>
            </div>
          )}
        </>
      ) : (
        <div className="border-t border-white/10 pt-4">
          <div className="flex items-center gap-2 text-red-400">
            <XCircleIcon className="size-5" />
            <span className="font-semibold">Research Failed</span>
          </div>
          {research.error && (
            <p className="text-white/60 text-sm mt-2">{research.error}</p>
          )}
        </div>
      )}
    </article>
  );
}

// simple restaurant card (non-researched)
function SimpleRestaurantCard({ restaurant }: { restaurant: SimpleRestaurant }) {
  return (
    <div className="bg-neutral-800/50 backdrop-blur-md rounded-xl border border-white/20 shadow-lg p-4">
      <h4 className="text-lg font-semibold text-white mb-1">
        {restaurant.name}
      </h4>
      {restaurant.cuisine && restaurant.cuisine.length > 0 ? (
        <p className="text-white/70 text-sm mb-2">
          {restaurant.cuisine.join(', ')}
        </p>
      ) : (
        <p className="text-white/50 text-sm mb-2">
          {restaurant.amenity_type === 'fast_food' ? 'Fast Food' : 'Restaurant'}
        </p>
      )}

      <div className="flex items-center gap-2 text-white/60 text-sm">
        <MapPinIcon className="size-4" />
        <span>{formatDistance(restaurant.distanceMeters)} away</span>
      </div>

      <div className="text-white/50 text-xs mt-2">
        {restaurant.address || 'Address not available'}
      </div>
    </div>
  );
}

// main page component
export default function StreamingTestPage() {
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<'idle' | 'connecting' | 'streaming' | 'complete' | 'error'>('idle');
  const [metadata, setMetadata] = useState<MetadataEvent | null>(null);
  const [researchedRestaurants, setResearchedRestaurants] = useState<ResearchedRestaurant[]>([]);
  const [nonResearchedRestaurants, setNonResearchedRestaurants] = useState<SimpleRestaurant[]>([]);
  const [eventLog, setEventLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const [showEventLog, setShowEventLog] = useState(false);

  // get user location on mount
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
          addLog('Location acquired');
        },
        (error) => {
          setLocationError(`Failed to get location: ${error.message}`);
          addLog(`Location error: ${error.message}`);
        }
      );
    } else {
      setLocationError('Geolocation not supported by browser');
      addLog('Geolocation not supported');
    }
  }, []);

  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setEventLog(prev => [...prev, `[${timestamp}] ${message}`]);
  }, []);

  const handleStreamEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case 'metadata':
        setMetadata(event);
        setStreamStatus('streaming');
        addLog(`Metadata: Found ${event.total_found} restaurants, researching ${event.total_to_research}`);
        break;

      case 'restaurant_researched':
        setResearchedRestaurants(prev => [...prev, event.data]);
        addLog(`Researched: ${event.data.name} (${event.index + 1})`);
        break;

      case 'restaurants_without_research':
        setNonResearchedRestaurants(event.data);
        addLog(`Received ${event.data.length} non-researched restaurants`);
        break;

      case 'complete':
        setStreamStatus('complete');
        addLog('Stream complete');
        break;

      case 'error':
        setError(event.error);
        setStreamStatus('error');
        addLog(`Error: ${event.error}`);
        break;
    }
  }, [addLog]);

  // start streaming when location is available
  useEffect(() => {
    if (!location) return;

    const params = new URLSearchParams({
      lat: location.lat.toString(),
      lng: location.lng.toString(),
      radius: STREAM_CONFIG.radius.toString(),
      limit: STREAM_CONFIG.researchLimit.toString()
    });

    const url = `${STREAM_CONFIG.flaskUrl}/restaurants/research/stream?${params}`;
    addLog(`Connecting to: ${url}`);

    const es = new EventSource(url);
    setEventSource(es);
    setStreamStatus('connecting');

    es.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        handleStreamEvent(data);
      } catch (err) {
        addLog(`Parse error: ${err}`);
      }
    };

    es.onerror = (err) => {
      setStreamStatus('error');
      setError('Stream connection failed. Is the Flask backend running?');
      addLog('Stream connection error');
      es.close();
    };

    return () => {
      addLog('Closing EventSource');
      es.close();
    };
  }, [location, handleStreamEvent, addLog]);

  const handleReconnect = () => {
    setStreamStatus('idle');
    setMetadata(null);
    setResearchedRestaurants([]);
    setNonResearchedRestaurants([]);
    setError(null);
    setEventLog([]);

    // trigger re-connection by toggling location
    if (location) {
      const temp = location;
      setLocation(null);
      setTimeout(() => setLocation(temp), 100);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* header */}
      <header className="bg-neutral-900/50 border-b border-white/10 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BeakerIcon className="size-8 text-blue-400" />
              <div>
                <h1 className="text-2xl font-bold">Streaming Research Test</h1>
                <p className="text-white/60 text-sm">Real-time restaurant research demonstration</p>
              </div>
            </div>

            {/* status indicator */}
            <div className="flex items-center gap-3">
              {streamStatus === 'connecting' && (
                <div className="flex items-center gap-2">
                  <ArrowPathIcon className="size-5 text-blue-400 animate-spin" />
                  <span className="text-sm text-blue-400">Connecting...</span>
                </div>
              )}
              {streamStatus === 'streaming' && (
                <div className="flex items-center gap-2">
                  <div className="size-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-sm text-green-400">Streaming</span>
                </div>
              )}
              {streamStatus === 'complete' && (
                <div className="flex items-center gap-2">
                  <CheckCircleIcon className="size-5 text-green-500" />
                  <span className="text-sm text-green-400">Complete</span>
                </div>
              )}
              {streamStatus === 'error' && (
                <div className="flex items-center gap-2">
                  <XCircleIcon className="size-5 text-red-500" />
                  <span className="text-sm text-red-400">Error</span>
                </div>
              )}
            </div>
          </div>

          {/* location display */}
          {location && (
            <div className="mt-3 flex items-center gap-2 text-sm text-white/60">
              <MapPinIcon className="size-4" />
              <span>
                {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
              </span>
            </div>
          )}

          {locationError && (
            <div className="mt-3 flex items-center gap-2 text-sm text-red-400">
              <XCircleIcon className="size-4" />
              <span>{locationError}</span>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* metadata panel */}
        {metadata && (
          <section className="bg-neutral-800/50 backdrop-blur-md rounded-2xl border border-white/20 shadow-2xl p-6 mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Query Information</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <div className="text-white/60 text-sm">Total Found</div>
                <div className="text-2xl font-bold text-white">{metadata.total_found}</div>
              </div>
              <div>
                <div className="text-white/60 text-sm">Researching</div>
                <div className="text-2xl font-bold text-blue-400">{metadata.total_to_research}</div>
              </div>
              <div>
                <div className="text-white/60 text-sm">Radius</div>
                <div className="text-2xl font-bold text-white">{formatDistance(metadata.query.radius)}</div>
              </div>
            </div>

            {/* progress bar */}
            <div>
              <div className="flex justify-between text-sm text-white/60 mb-2">
                <span>Progress</span>
                <span>{researchedRestaurants.length} / {metadata.total_to_research}</span>
              </div>
              <div className="w-full bg-neutral-700 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: `${(researchedRestaurants.length / metadata.total_to_research) * 100}%`
                  }}
                />
              </div>
            </div>
          </section>
        )}

        {/* error banner */}
        {error && (
          <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-4 mb-8 flex items-start justify-between">
            <div className="flex items-start gap-3">
              <XCircleIcon className="size-6 text-red-400 shrink-0" />
              <div>
                <h3 className="text-red-400 font-semibold">Stream Error</h3>
                <p className="text-white/80 text-sm mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={handleReconnect}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors"
            >
              Reconnect
            </button>
          </div>
        )}

        {/* researched restaurants */}
        {researchedRestaurants.length > 0 && (
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
              <DocumentTextIcon className="size-7 text-blue-400" />
              Researched Restaurants ({researchedRestaurants.length})
            </h2>

            <div className="space-y-6">
              {researchedRestaurants.map((restaurant) => (
                <ResearchedRestaurantCard key={restaurant.id} restaurant={restaurant} />
              ))}
            </div>
          </section>
        )}

        {/* non-researched restaurants */}
        {nonResearchedRestaurants.length > 0 && (
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
              <StarIcon className="size-7 text-white/60" />
              Additional Restaurants ({nonResearchedRestaurants.length})
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {nonResearchedRestaurants.map((restaurant) => (
                <SimpleRestaurantCard key={restaurant.id} restaurant={restaurant} />
              ))}
            </div>
          </section>
        )}

        {/* waiting state */}
        {streamStatus === 'connecting' && !metadata && (
          <div className="text-center py-16">
            <ArrowPathIcon className="size-12 text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-white/60">Connecting to stream...</p>
          </div>
        )}

        {streamStatus === 'streaming' && researchedRestaurants.length === 0 && metadata && (
          <div className="text-center py-16">
            <ArrowPathIcon className="size-12 text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-white/60">Researching restaurants...</p>
          </div>
        )}

        {/* event log */}
        <section className="mt-8">
          <button
            onClick={() => setShowEventLog(!showEventLog)}
            className="flex items-center gap-2 text-white/70 hover:text-white transition-colors mb-3"
          >
            {showEventLog ? (
              <ChevronUpIcon className="size-5" />
            ) : (
              <ChevronDownIcon className="size-5" />
            )}
            <span className="font-semibold">Event Log ({eventLog.length})</span>
          </button>

          {showEventLog && (
            <div className="bg-neutral-900 rounded-xl p-4 max-h-96 overflow-y-auto font-mono text-xs">
              {eventLog.length === 0 ? (
                <p className="text-white/40">No events yet...</p>
              ) : (
                eventLog.map((log, idx) => (
                  <div key={idx} className="text-green-400 mb-1">
                    {log}
                  </div>
                ))
              )}
            </div>
          )}
        </section>
      </main>

      {/* footer */}
      <footer className="border-t border-white/10 mt-16">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between text-sm text-white/40">
            <div>Streaming Research Test Page</div>
            <div className="flex items-center gap-4">
              <span>Flask: {STREAM_CONFIG.flaskUrl}</span>
              <span>Limit: {STREAM_CONFIG.researchLimit}</span>
              <span>Radius: {formatDistance(STREAM_CONFIG.radius)}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
