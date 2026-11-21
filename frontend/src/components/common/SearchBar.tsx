import { Search, X } from "lucide-react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
}

export default function SearchBar({
  value,
  onChange,
  placeholder = "Search...",
  onClear,
}: SearchBarProps) {
  return (
    <div style={{ position: "relative", display: "flex", alignItems: "center", flex: 1 }}>
      <Search
        size={17}
        style={{
          position: "absolute",
          left: "14px",
          color: "var(--muted)",
          pointerEvents: "none",
        }}
      />
      <input
        type="text"
        className="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ paddingLeft: "40px", paddingRight: value ? "36px" : "14px" }}
      />
      {value && (
        <button
          type="button"
          onClick={() => {
            onChange("");
            onClear?.();
          }}
          aria-label="Clear search"
          style={{
            position: "absolute",
            right: "10px",
            background: "none",
            border: "none",
            color: "var(--muted)",
            cursor: "pointer",
            display: "grid",
            placeItems: "center",
          }}
        >
          <X size={15} />
        </button>
      )}
    </div>
  );
}
