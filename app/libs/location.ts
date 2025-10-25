export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  source: 'geolocation' | 'default';
  city?: string;
  region?: string;
  country?: string;
}

export class LocationService {
  private static instance: LocationService;
  
  public static getInstance(): LocationService {
    if (!LocationService.instance) {
      LocationService.instance = new LocationService();
    }
    return LocationService.instance;
  }

  /**
   * Get user's current location with fallback to Palace of Fine Arts
   */
  async getCurrentLocation(): Promise<LocationData> {
    try {
      return await this.getGeolocation();
    } catch (error) {
      console.warn('Geolocation failed, using Palace of Fine Arts as default');
      return this.getDefaultLocation();
    }
  }

  /**
   * Get precise location using browser geolocation API
   */
  private async getGeolocation(): Promise<LocationData> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported'));
        return;
      }

      const options: PositionOptions = {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000 // 5 minutes
      };

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const location: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            source: 'geolocation'
          };

          // Try to get city/region from coordinates
          try {
            const details = await this.getLocationDetails(position.coords.latitude, position.coords.longitude);
            if (details.city) location.city = details.city;
            if (details.region) location.region = details.region;
          } catch (error) {
            console.warn('Could not get city/region from coordinates:', error);
          }

          resolve(location);
        },
        (error) => {
          reject(new Error(this.getGeolocationErrorMessage(error.code)));
        },
        options
      );
    });
  }

  /**
   * Get default location (Palace of Fine Arts, San Francisco)
   */
  private getDefaultLocation(): LocationData {
    return {
      latitude: 37.8029,
      longitude: -122.4481,
      source: 'default',
      city: 'San Francisco',
      region: 'CA',
      country: 'United States'
    };
  }

  /**
   * Get human-readable location string
   */
  getLocationString(location: LocationData): string {
    if (location.city && location.region) {
      return `${location.city}, ${location.region}`;
    }
    
    if (location.city) {
      return location.city;
    }
    
    return 'Current Location';
  }

  /**
   * Get city and state information from coordinates using reverse geocoding
   */
  private async getLocationDetails(latitude: number, longitude: number): Promise<{ city?: string; region?: string }> {
    try {
      const response = await fetch(
        `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`,
        {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Reverse geocoding failed: ${response.status}`);
      }

      const data = await response.json();
      
      return {
        city: data.city,
        region: data.principalSubdivisionCode || data.principalSubdivision
      };
    } catch (error) {
      console.warn('Reverse geocoding failed:', error);
      return {};
    }
  }

  /**
   * Get geolocation error message
   */
  private getGeolocationErrorMessage(code: number): string {
    switch (code) {
      case 1:
        return 'Location access denied by user';
      case 2:
        return 'Location unavailable';
      case 3:
        return 'Location request timed out';
      default:
        return 'Unknown location error';
    }
  }

  /**
   * Check if geolocation is supported
   */
  isGeolocationSupported(): boolean {
    return 'geolocation' in navigator;
  }
}