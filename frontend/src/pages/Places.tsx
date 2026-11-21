import { useEffect, useState } from "react";
import AppShell from "../components/layout/AppShell";
import PlaceCard from "../components/cards/PlaceCard";
import SearchBar from "../components/common/SearchBar";
import CategoryChips from "../components/common/CategoryChips";
import { PlaceItem, api } from "../lib/api";

const PLACE_CATEGORIES = ["All", "Cafes", "Parks", "Co-working", "Libraries"];

export default function Places() {
  const [places, setPlaces] = useState<PlaceItem[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPlaces() {
      setLoading(true);
      try {
        const data = await api.places();
        setPlaces(data);
      } catch (err) {
        console.error("Failed to load places:", err);
      } finally {
        setLoading(false);
      }
    }
    loadPlaces();
  }, []);

  const filteredPlaces = places.filter((p) => {
    const matchesSearch =
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.city.toLowerCase().includes(search.toLowerCase()) ||
      (p.address && p.address.toLowerCase().includes(search.toLowerCase()));

    const matchesCategory =
      category === "All" ||
      (p.category && p.category.toLowerCase().includes(category.toLowerCase()));

    return matchesSearch && matchesCategory;
  });

  return (
    <AppShell title="Places">
      <p className="eyebrow">Around the corner and beyond</p>
      <h1 className="page-title">Go somewhere good.</h1>

      {/* Toolbar */}
      <div className="toolbar">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search places by name, neighborhood, or city..."
        />
      </div>

      {/* Category Chips */}
      <CategoryChips
        categories={PLACE_CATEGORIES}
        activeCategory={category}
        onSelect={setCategory}
      />

      {/* Section */}
      <div className="section-heading">
        <h2>Nearby &amp; recommended places</h2>
        <small className="meta">
          Showing {filteredPlaces.length} {filteredPlaces.length === 1 ? "place" : "places"}
        </small>
      </div>

      {loading ? (
        <div className="empty">Loading places...</div>
      ) : filteredPlaces.length === 0 ? (
        <p className="empty">No places match those filters. Try another search or category.</p>
      ) : (
        <div className="grid-3">
          {filteredPlaces.map((place) => (
            <PlaceCard key={place.id} place={place} />
          ))}
        </div>
      )}

      {/* Banner */}
      <div className="banner" style={{ marginTop: "48px" }}>
        <h2>Explore the neighborhood</h2>
        <p className="lead" style={{ margin: 0 }}>
          Tap Directions on any place card to launch its exact coordinates in Google Maps.
        </p>
      </div>
    </AppShell>
  );
}
