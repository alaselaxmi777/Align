# Google Maps & Real Places Integration Guide

ALIGN integrates real-world physical place and venue discovery with an intelligent dual-mode architecture:
1. **Google Maps Platform Integration** (Live Maps JavaScript API + Places API)
2. **Deterministic Haversine Fallback** (Local offline great-circle distance computation in PostgreSQL & Python)

---

## 1. Google Maps Configuration

To enable interactive map views, address autocomplete, and real-time place details:

### A. Environment Variables
Add the following keys to your `.env` file:

```env
# Frontend (Client-side interactive map)
VITE_GOOGLE_MAPS_API_KEY=AIzaSyYourGoogleMapsApiKeyHere

# Backend (Geocoding & Places verification)
GOOGLE_MAPS_API_KEY=AIzaSyYourGoogleMapsApiKeyHere
```

### B. Required Google Cloud APIs
In the [Google Cloud Console](https://console.cloud.google.com/google/maps-apis):
1. Enable **Maps JavaScript API**
2. Enable **Places API (New)**
3. Enable **Geocoding API**
4. Under Credentials, restrict your API key:
   - **Application restrictions:** HTTP referrers (`http://localhost:5173/*`, `https://your-production-domain.com/*`)
   - **API restrictions:** Limit key to the 3 APIs listed above.

---

## 2. Built-in Deterministic Haversine Fallback

When a Google Maps API key is not provided or during offline local development, ALIGN automatically uses its mathematical **Haversine Distance Engine**:

$$\Delta\sigma = 2 \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
$$d = R \cdot \Delta\sigma \quad (R = 6,371\text{ km})$$

### Features Supported Without External API:
- Automatic sorting of venues and experiences by proximity to user's current or selected coordinates.
- Proximity scoring bonuses in the hybrid recommendation engine (+10% for <25 km, +5% for <50 km).
- Direct external navigation links (`https://www.google.com/maps/search/?api=1&query={lat},{lon}`) allowing one-click opening in standard Google Maps apps on iOS/Android/Desktop.
- Pre-seeded real co-working spaces, libraries, maker spaces, and tech hubs across major metropolitan regions.
