/**
 * Utility functions for distance formatting
 */

export function formatDistance(meters?: number): string {
  if (!meters) return '';
  
  // Convert meters to feet
  const feet = meters * 3.28084;
  
  if (feet < 1000) {
    return `${Math.round(feet)} ft`;
  } else {
    // Convert to miles for longer distances
    const miles = meters / 1609.34;
    if (miles < 1) {
      return `${(miles * 1000).toFixed(0)} ft`;
    } else {
      return `${miles.toFixed(1)} mi`;
    }
  }
}

export function formatDistanceShort(meters?: number): string {
  if (!meters) return '';
  
  const feet = meters * 3.28084;
  
  if (feet < 1000) {
    return `${Math.round(feet)}ft`;
  } else {
    const miles = meters / 1609.34;
    return `${miles.toFixed(1)}mi`;
  }
}
