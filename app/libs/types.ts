export interface Restaurant {
  id: string;
  name: string;
  location: { lat: number; lng: number };
  rating?: number;
  distanceMeters?: number;
  dishes?: Dish[];
  summaryAllergenProfile?: Record<string, number>;
  cuisine?: string[];
  address?: string;
  phone?: string;
  website?: string;
  isOpen?: boolean;
}

export interface Dish {
  id: string;
  name: string;
  description?: string;
  price?: number;
  allergens?: string[];
  allergenProfile?: Record<string, number>;
}

export interface AllergenRisk {
  allergen: "gluten" | "nut" | "dairy" | "soy" | "egg" | "shellfish";
  probability: number; // 0-1
  evidence: { kind: "text" | "image"; sourceUrl?: string }[];
}

export interface QueryIntent {
  cuisine?: string[];
  filters?: { vegan?: boolean; gluten_free?: boolean };
  naturalLanguage: string;
}

export interface RestaurantQuery {
  lat: number;
  lng: number;
  radius: number;
  limit?: number;
}

export interface RestaurantResponse {
  restaurants: Restaurant[];
  query: RestaurantQuery;
  total: number;
}
