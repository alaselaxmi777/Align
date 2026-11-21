import React, { useState, useEffect } from "react";
import { resolveMediaUrl } from "../../lib/api";
import { Image as ImageIcon, User as UserIcon } from "lucide-react";

interface SafeImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, "src"> {
  src?: string | null;
  fallbackSrc?: string;
  showPlaceholderIcon?: boolean;
}

export function SafeImage({
  src,
  alt = "Image",
  fallbackSrc,
  showPlaceholderIcon = true,
  style,
  className,
  onError,
  ...props
}: SafeImageProps) {
  const [hasError, setHasError] = useState(false);
  const resolvedUrl = resolveMediaUrl(src);

  // Reset error state if src changes
  useEffect(() => {
    setHasError(false);
  }, [src]);

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    setHasError(true);
    if (onError) {
      onError(e);
    }
  };

  if (!resolvedUrl || hasError) {
    if (fallbackSrc) {
      return (
        <img
          src={resolveMediaUrl(fallbackSrc)}
          alt={alt}
          style={{ width: "100%", height: "100%", objectFit: "cover", ...style }}
          className={className}
          onError={() => setHasError(true)}
          {...props}
        />
      );
    }

    return (
      <div
        className={className}
        style={{
          width: "100%",
          height: "100%",
          minHeight: "100px",
          display: "grid",
          placeItems: "center",
          background: "linear-gradient(135deg, var(--bg-secondary, #1a1a24) 0%, var(--bg-card, #12121a) 100%)",
          color: "var(--muted, #6b7280)",
          border: "1px solid var(--border-subtle, rgba(255,255,255,0.06))",
          borderRadius: "inherit",
          userSelect: "none",
          ...style,
        }}
        aria-label={alt}
      >
        {showPlaceholderIcon && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
            <ImageIcon size={28} style={{ opacity: 0.4 }} />
          </div>
        )}
      </div>
    );
  }

  return (
    <img
      src={resolvedUrl}
      alt={alt}
      style={style}
      className={className}
      onError={handleImageError}
      loading="lazy"
      {...props}
    />
  );
}

interface SafeAvatarProps {
  src?: string | null;
  name?: string | null;
  alt?: string;
  size?: number | string;
  className?: string;
  style?: React.CSSProperties;
  fontSize?: string;
}

export function SafeAvatar({
  src,
  name,
  alt = "User Avatar",
  size = 40,
  className,
  style,
  fontSize,
}: SafeAvatarProps) {
  const [hasError, setHasError] = useState(false);
  const resolvedUrl = resolveMediaUrl(src);

  useEffect(() => {
    setHasError(false);
  }, [src]);

  const initials = (() => {
    const raw = (name || alt || "U").trim();
    if (!raw) return "U";
    const parts = raw.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return raw.slice(0, 2).toUpperCase();
  })();

  const dim = typeof size === "number" ? `${size}px` : size;

  if (!resolvedUrl || hasError) {
    return (
      <div
        className={className}
        style={{
          width: dim,
          height: dim,
          minWidth: dim,
          minHeight: dim,
          borderRadius: "50%",
          display: "grid",
          placeItems: "center",
          background: "linear-gradient(135deg, var(--accent, #6366f1) 0%, var(--accent-pink, #ec4899) 100%)",
          color: "#ffffff",
          fontWeight: 700,
          fontSize: fontSize || (typeof size === "number" ? `${Math.max(11, Math.round(size * 0.38))}px` : "14px"),
          userSelect: "none",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          flexShrink: 0,
          ...style,
        }}
        aria-label={name || alt}
      >
        {initials || <UserIcon size={typeof size === "number" ? Math.round(size * 0.5) : 16} />}
      </div>
    );
  }

  return (
    <div
      className={className}
      style={{
        width: dim,
        height: dim,
        minWidth: dim,
        minHeight: dim,
        borderRadius: "50%",
        overflow: "hidden",
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
        ...style,
      }}
    >
      <img
        src={resolvedUrl}
        alt={alt}
        onError={() => setHasError(true)}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />
    </div>
  );
}
