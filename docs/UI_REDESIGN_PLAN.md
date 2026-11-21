# ALIGN Frontend Redesign Plan (Plum & Electric-Lime Design System)

**Date**: November 2026  
**Target**: Complete frontend UI redesign matching the approved reference design in both Dark ("Plum") and Light ("Warm Cream") modes without touching backend logic, routes, auth, or data contracts.

---

## 1. Design Tokens & CSS Variables

### 1.1 Color Palette & Theme Tokens
| Token | Dark Mode (`#1C1126` Plum Glow) | Light Mode (`#FFF7EE` Cream Glow) | Usage |
| :--- | :--- | :--- | :--- |
| `--bg` | `#1C1126` | `#FFF7EE` | Page background |
| `--bg-glow` | `#3A2150` (radial top-right) | `#F2E4FF` (radial top-right) | Ambient top-right radial glow |
| `--bg-elev` | `#261736` | `#FFFFFF` | Solid elevated surfaces & cards |
| `--bg-card-glass` | `rgba(255, 255, 255, 0.04)` | `rgba(42, 22, 56, 0.04)` | Glassmorphic cards & panels |
| `--border` | `rgba(255, 255, 255, 0.10)` | `rgba(42, 22, 56, 0.12)` | Subtle hairline borders |
| `--text` | `#FFF1E3` (warm cream) | `#2A1638` (deep plum) | Primary headings & body text |
| `--text-muted` | `#B9A8C9` | `#6E5A82` | Secondary labels & descriptions |
| `--lilac` | `#A67CF5` | `#7C4DDB` | Accents, links, logo badge, focus rings |
| `--lilac-strong` | `#8B5CF6` | `#6B3FD0` | Hover states, active tabs |
| `--pink` | `#FF7FA8` | `#E2487F` | Gradient stop, "align." dot, hero accents |
| `--peach` | `#FFB38A` | `#F08A4B` | Gradient stop, secondary warm accent |
| `--lime` | `#D8F56A` | `#CDEB4A` | **Primary CTA Button & Key Highlights** |
| `--on-lime` | `#1C1126` | `#2A1638` | Text on electric-lime buttons |
| `--danger` | `#FF6B81` | `#D6335A` | Errors & destructive actions |
| `--success` | `#5BE3A0` | `#12915B` | Verification checks & success states |

### 1.2 Gradients & Typography
- **Gradients**:
  - `--grad-lilac-pink`: `linear-gradient(90deg, var(--lilac), var(--pink))`
  - `--grad-pink-peach`: `linear-gradient(90deg, var(--pink), var(--peach))`
  - `--grad-hero-text`: `linear-gradient(135deg, var(--text) 0%, var(--pink) 50%, var(--peach) 100%)`
- **Typography**:
  - **Display / Headings**: `"Bricolage Grotesque"`, sans-serif (700–800, `letter-spacing: -0.03em`).
  - **Body / Interface**: `"DM Sans"`, sans-serif (400, 500, 600, 700).
  - Headline Size: Fluid `clamp(40px, 6vw, 84px)`.
- **Radii**:
  - Card: `28px – 32px` (`rounded-[28px]` or `rounded-[32px]`)
  - Input: `16px` (`rounded-[16px]`)
  - Button / Pill: `9999px` (`rounded-full`)

### 1.3 Legacy Token Aliases (Seamless Compatibility)
Map all legacy `--bg-main`, `--bg-card`, `--bg-secondary`, `--primary-accent`, `--accent-primary`, `--button-primary`, `--text-primary`, `--border-color` tokens to the new variables so all components automatically harmonize.

---

## 2. Layout Shell Architecture

1. **Sticky Top Navbar** (`Topbar.tsx` + `AppShell.tsx`):
   - Replace the left sidebar with a sleek, sticky horizontal top navigation bar.
   - **Left**: Rounded-square lilac badge with sparkle icon + lowercase wordmark **`align.`** (pink dot).
   - **Center / Right**: Primary navigation links with icons:
     - Home, Discover, Communities, Events, Opportunities, Goal Journey, Assistant.
   - **More Dropdown**:
     - Circles, Discovery Map, Places, People, Posts / Feed, Reels, Achievements, Collaborate / Projects, Skills Catalog, Goals & Interests, Settings.
   - **Far Right**:
     - Theme Toggle (accessible icon button for Light / Dark mode).
     - Notifications Bell with active indicator.
     - User Avatar (or bordered "Sign in" button with an icon for guests).
   - 1px hairline border below the navbar (`border-b border-[var(--border)]`).
2. **Single Source of Truth** (`components/layout/navItems.ts`):
   - Defines all route metadata, icon components, visibility conditions (primary vs more, authOnly).
3. **Mobile Shell ($\le 760\text{px}$)**:
   - Fixed bottom tab bar: `Home`, `Explore`, `Communities`, `Events`, `More` (triggers smooth bottom sheet).
   - "Ask ALIGN" floating assistant widget positioned safely above the bottom tab bar.
4. **Page Container**:
   - `max-width: 1280px`, margin auto, padding `clamp(16px, 4vw, 40px)`.
5. **Footer** (`Footer.tsx`):
   - Slim, minimalist footer styled using pure design tokens.

---

## 3. Shared Components Design Specification

- **Button**:
  - `primary`: Background `--lime`, text `--on-lime`, font-weight 700, pill radius (`rounded-full`), hover brightness.
  - `secondary`: Background `var(--bg-card-glass)`, border `var(--border)`, text `var(--text)`.
  - `ghost`: Transparent with subtle hover highlight.
  - `danger`: Border or background `var(--danger)`.
- **Input / Select / Textarea**:
  - Radius: `16px`.
  - Background: `var(--bg-card-glass)` in dark mode / `var(--bg-elev)` in light mode.
  - Border: `var(--border)`, active focus ring in `var(--lilac)`.
  - Password fields: toggle show/hide icon.
- **Card**:
  - Glass card: `background: var(--bg-card-glass)`, `backdrop-filter: blur(12px)`, `border: 1px solid var(--border)`, `border-radius: 28px`.
  - Elevated card: `background: var(--bg-elev)`, `border-radius: 28px`.
- **Badge / Chip / Pill**:
  - Outline pill with tiny icon: `border: 1px solid var(--border)`, `border-radius: 9999px`, font-size `12px`, letter-spacing `0.02em`.
- **Entity Cards** (`CommunityCard`, `EventCard`, `PlaceCard`, `PostCard`, `ReelCard`):
  - Retain all existing props.
  - Generous 24px–28px corner radius, image aspect ratios with subtle bottom gradient overlays, pill tags, and lime CTA actions.

---

## 4. Key Page Layouts

1. **Landing Page** (`frontend/src/pages/Landing.tsx`):
   - **Hero**:
     - Lilac sparkle eyebrow: `✦ A BETTER WAY TO BELONG`.
     - Massive headline: **Find the people who <span className="bg-gradient-to-r from-[var(--lilac)] to-[var(--pink)] bg-clip-text text-transparent">get</span> <span className="bg-gradient-to-r from-[var(--pink)] to-[var(--peach)] bg-clip-text text-transparent">you.</span>**
     - Calm paragraph in muted cream text.
     - Row of outline pill chips with tiny icons: *"Shared interests"*, *"Real experiences"*, *"Meaningful connections"*.
     - Natural-language intent search bar with example chips.
     - 3 live preview recommendation cards with Shapley popover.
   - 3-step "How It Works" cards (translucent plum glass, large radius).
   - Featured communities, events, and places.
   - Callout banner with subtle gradient border.
2. **Auth Page** (`frontend/src/pages/Auth.tsx`):
   - **Two-Column Layout**:
     - **Left**: Hero typography with gradient highlights and core value pills.
     - **Right**: Tall rounded card (`radius ~32px`) with "Back home" link, "Welcome back" title, white pill "Sign in with Google" button, "or continue with email" divider, 16px radius inputs, show/hide password icon, lilac "Forgot password?" link, full-width electric-lime button ("Sign in →"), and registration prompt.
3. **Discover & Explore** (`Discover.tsx`):
   - Large intent search bar, category pill filter strip, candidate grid with Shapley factor breakdown.
4. **Dashboard & Other Pages**:
   - Translucent plum cards, Recharts visualizations with themed tooltips, fluid responsive padding.
   - Settings page includes Appearance toggle: `System` / `Light` / `Dark`.

---

## 5. Verification & Quality Gates

- `npm run build` after each phase: zero TypeScript errors.
- Visual inspection across mobile (390px, 768px) and desktop (1024px, 1440px).
- Playwright screenshot suite in `docs/screenshots/` capturing both dark and light modes.
- Full contrast checks meeting WCAG AA standards.
