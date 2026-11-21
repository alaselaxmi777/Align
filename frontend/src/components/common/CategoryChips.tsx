interface CategoryChipsProps {
  categories: string[];
  activeCategory: string;
  onSelect: (category: string) => void;
}

export default function CategoryChips({
  categories,
  activeCategory,
  onSelect,
}: CategoryChipsProps) {
  return (
    <div className="chips" role="tablist">
      {categories.map((cat) => {
        const isActive = activeCategory === cat;
        return (
          <button
            key={cat}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`chip ${isActive ? "active" : ""}`}
            onClick={() => onSelect(cat)}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
}
