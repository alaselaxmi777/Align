import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Compass,
  Sparkles,
  Users,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import CommunityCard from "../components/cards/CommunityCard";
import EventCard from "../components/cards/EventCard";
import PlaceCard from "../components/cards/PlaceCard";
import WhyThisPopover from "../components/common/WhyThisPopover";
import ContentDetailModal, { DetailModalData } from "../components/common/ContentDetailModal";
import { Community, EventItem, PlaceItem, DiscoveryResult, api } from "../lib/api";

const EXAMPLE_PROMPTS = [
  "I want to build an AI project with a designer",
  "Weekend hiking & photography in Pune",
  "Beginner robotics and embedded systems",
  "Co-working spaces with good coffee",
];

export default function Landing() {
  const [communities, setCommunities] = useState<Community[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [places, setPlaces] = useState<PlaceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalData, setModalData] = useState<DetailModalData | null>(null);

  // Intent search state
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<DiscoveryResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState("");

  const loggedIn = Boolean(localStorage.getItem("align_token"));
  const userName = localStorage.getItem("align_user_name") || "Friend";

  useEffect(() => {
    async function loadData() {
      try {
        const [commRes, eventRes, placeRes] = await Promise.allSettled([
          api.communities({ limit: 3 }),
          api.events({ limit: 3 }),
          api.places(),
        ]);

        if (commRes.status === "fulfilled") {
          setCommunities(commRes.value.slice(0, 3));
        }
        if (eventRes.status === "fulfilled") {
          setEvents(eventRes.value.slice(0, 3));
        }
        if (placeRes.status === "fulfilled") {
          setPlaces(placeRes.value.slice(0, 3));
        }
      } catch (err) {
        console.error("Failed to load landing data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleIntentSearch(queryToSearch: string) {
    const trimmed = queryToSearch.trim();
    if (!trimmed) return;
    setSearchQuery(trimmed);
    setIsSearching(true);
    setSearchError("");
    setHasSearched(true);
    try {
      const results = await api.search(trimmed);
      setSearchResults(results.slice(0, 3));
    } catch (err) {
      console.error("Search error:", err);
      setSearchError("Unable to retrieve recommendations right now. Please try again.");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }

  function handlePromptChipClick(prompt: string) {
    setSearchQuery(prompt);
    handleIntentSearch(prompt);
  }

  function getResultLink(res: DiscoveryResult): string {
    switch (res.result_type) {
      case "community":
        return `/communities/${res.id}`;
      case "event":
        return `/events`;
      case "place":
        return `/places`;
      case "project":
        return `/projects`;
      case "user":
        return `/people`;
      case "opportunity":
        return `/opportunities`;
      default:
        return `/discover`;
    }
  }

  return (
    <AppShell title="Home">
      {/* Logged-in Welcome Banner */}
      {loggedIn && (
        <aside
          role="status"
          aria-label="Welcome back notification"
          className="mb-8 p-4 sm:p-5 rounded-[24px] bg-[rgba(167,121,232,0.08)] border border-[rgba(167,121,232,0.22)] backdrop-blur-md flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[var(--lime)] text-[var(--on-lime)] grid place-items-center">
              <Sparkles size={16} />
            </div>
            <span className="text-sm font-semibold text-[var(--text)]">
              Welcome back, <strong className="text-[var(--lime)]">{userName}</strong>! Your personalized matches are ready.
            </span>
          </div>
          <Link
            to="/dashboard"
            className="px-4 py-2 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-xs hover:brightness-105 transition-all shadow-sm"
          >
            Go to Dashboard →
          </Link>
        </aside>
      )}

      {/* Hero Section */}
      <section className="py-8 md:py-16 text-center max-w-4xl mx-auto" aria-label="Landing hero">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[rgba(167,121,232,0.12)] border border-[rgba(167,121,232,0.25)] text-[var(--lilac)] text-[11px] font-extrabold uppercase tracking-widest mb-6">
          <Sparkles size={13} />
          <span>A BETTER WAY TO BELONG</span>
        </div>

        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[var(--text)] leading-[1.1] mb-6 font-display break-normal">
          Find the people who{" "}
          <span className="inline-block whitespace-nowrap">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[var(--lilac)] to-[var(--pink)]">
              get
            </span>{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[var(--pink)] to-[var(--peach)]">
              you.
            </span>
          </span>
        </h1>

        <p className="text-base sm:text-lg text-[var(--text-muted)] leading-relaxed max-w-2xl mx-auto mb-8">
          State your raw intent, curious passion, or weekend project in conversational language.
          Our hybrid vector embeddings and graph network match you to real circles, peers, and places.
        </p>

        {/* Outline Pill Chips */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-xs font-semibold text-[var(--text)] backdrop-blur-sm">
            <span className="text-[var(--lilac)]">✳</span>
            <span>Shared interests</span>
          </div>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-xs font-semibold text-[var(--text)] backdrop-blur-sm">
            <span className="text-[var(--pink)]">↗</span>
            <span>Real experiences</span>
          </div>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-xs font-semibold text-[var(--text)] backdrop-blur-sm">
            <span className="text-[var(--peach)]">♡</span>
            <span>Meaningful connections</span>
          </div>
        </div>

        {/* Interactive Intent Search Box */}
        <div className="p-2 sm:p-2.5 rounded-[24px] sm:rounded-full bg-[var(--bg-elev)] border border-[var(--border)] shadow-2xl backdrop-blur-xl flex flex-col sm:flex-row items-stretch sm:items-center gap-2 mb-4">
          <div className="flex items-center flex-1 px-3">
            <Search size={18} className="text-[var(--text-muted)] shrink-0 mr-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleIntentSearch(searchQuery);
                }
              }}
              placeholder="What are you curious about? e.g., 'Looking for designers to build a robotics project'"
              aria-label="Natural language intent search"
              className="w-full bg-transparent border-0 text-sm sm:text-base text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-0 p-0"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setHasSearched(false);
                  setSearchResults([]);
                }}
                aria-label="Clear search input"
                className="p-1 rounded-full text-[var(--text-muted)] hover:text-[var(--text)]"
              >
                <X size={16} />
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={() => handleIntentSearch(searchQuery)}
            disabled={isSearching || !searchQuery.trim()}
            className="py-3 px-7 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-extrabold text-sm hover:brightness-105 active:scale-95 transition-all shadow-md disabled:opacity-60 shrink-0"
          >
            {isSearching ? "Matching..." : "Discover"}
          </button>
        </div>

        {/* Prompt Chips */}
        <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
          <span className="text-xs text-[var(--text-muted)] font-medium mr-1">
            Try an intent:
          </span>
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handlePromptChipClick(prompt)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                searchQuery === prompt
                  ? "bg-[rgba(216,245,106,0.15)] border-[var(--lime)] text-[var(--lime)]"
                  : "bg-[var(--bg-card-glass)] border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--lilac)]"
              }`}
            >
              ✦ {prompt}
            </button>
          ))}
        </div>

        {/* Live Search Preview Section */}
        {hasSearched && (
          <div className="mt-8 p-6 sm:p-8 rounded-[32px] bg-[var(--bg-elev)] border border-[var(--border)] shadow-2xl text-left backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[rgba(167,121,232,0.15)] text-[var(--lilac)] grid place-items-center">
                  <Sparkles size={16} />
                </div>
                <h3 className="text-lg font-bold text-[var(--text)]">
                  Top Matches for &ldquo;{searchQuery}&rdquo;
                </h3>
              </div>
              <Link
                to="/discover"
                className="text-xs font-bold text-[var(--lime)] hover:underline inline-flex items-center gap-1"
              >
                Full Discover View →
              </Link>
            </div>

            {isSearching ? (
              <div className="text-center py-12 text-[var(--text-muted)]">
                <Sparkles size={28} className="animate-spin text-[var(--lilac)] mx-auto mb-3" />
                <p className="text-sm">Calculating pgvector embeddings and Neo4j graph affinities...</p>
              </div>
            ) : searchError ? (
              <div className="text-center py-8 text-[var(--danger)]">
                <p>{searchError}</p>
              </div>
            ) : searchResults.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {searchResults.map((result) => (
                  <article
                    key={`${result.result_type}-${result.id}`}
                    className="p-5 rounded-[24px] bg-[var(--bg-card-glass)] border border-[var(--border)] flex flex-col justify-between hover:border-[var(--lilac)] transition-all shadow-md"
                  >
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="tag text-[10.5px]">
                          {result.result_type} · {result.category || "General"}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-[var(--lime)] bg-[rgba(216,245,106,0.12)] px-2 py-0.5 rounded-full">
                            {Math.round(result.score * 100)}%
                          </span>
                          <WhyThisPopover
                            score={result.score}
                            whyRecommended={result.why_recommended}
                            scoreBreakdown={result.score_breakdown}
                            matchedTerms={result.matched_terms}
                            graphPath={result.graph_path}
                            title={result.title}
                          />
                        </div>
                      </div>

                      <h4 className="text-base font-bold text-[var(--text)] mb-2 line-clamp-1">
                        {result.title}
                      </h4>
                      <p className="text-xs text-[var(--text-muted)] line-clamp-3 leading-relaxed">
                        {result.description}
                      </p>
                    </div>

                    <div className="mt-5 pt-3.5 border-t border-[var(--border)] flex items-center justify-between">
                      <span className="text-[11px] text-[var(--text-muted)]">
                        {result.is_verified ? "✓ Verified source" : "Platform record"}
                      </span>
                      <Link
                        to={getResultLink(result)}
                        className="px-3 py-1.5 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-xs hover:brightness-105 transition-all"
                      >
                        View Details →
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="text-center py-10 text-[var(--text-muted)]">
                <p className="text-base font-semibold mb-1">No exact matches found for &ldquo;{searchQuery}&rdquo;.</p>
                <p className="text-xs">Try broader keywords or explore all available communities and projects.</p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 3-Step "How It Works" Section */}
      <section className="mt-16 md:mt-24" aria-label="How ALIGN works">
        <div className="text-center mb-12">
          <p className="eyebrow justify-center">UNDER THE HOOD</p>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight mb-3">
            How Hybrid Discovery Works
          </h2>
          <p className="text-sm sm:text-base text-[var(--text-muted)] max-w-xl mx-auto">
            Moving beyond simple keyword searches with deep semantic understanding and graph topology.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-7 rounded-[28px] bg-[var(--bg-card-glass)] border border-[var(--border)] backdrop-blur-xl">
            <div className="w-12 h-12 rounded-[16px] bg-[rgba(167,121,232,0.14)] text-[var(--lilac)] flex items-center justify-center mb-5">
              <Sparkles size={24} />
            </div>
            <strong className="text-base font-extrabold text-[var(--text)] block mb-2">
              01 / Express Natural Intent
            </strong>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] leading-relaxed m-0">
              Write your raw goal, hobby, or project idea in conversational English without worrying about exact keyword tags.
            </p>
          </div>

          <div className="p-7 rounded-[28px] bg-[var(--bg-card-glass)] border border-[var(--border)] backdrop-blur-xl">
            <div className="w-12 h-12 rounded-[16px] bg-[rgba(216,245,106,0.14)] text-[var(--lime)] flex items-center justify-center mb-5">
              <Compass size={24} />
            </div>
            <strong className="text-base font-extrabold text-[var(--text)] block mb-2">
              02 / Hybrid Vector & Graph Ranker
            </strong>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] leading-relaxed m-0">
              pgvector HNSW indexes retrieve semantic candidates in &lt;3ms, while Neo4j graph signals boost shared circles and trusted peers.
            </p>
          </div>

          <div className="p-7 rounded-[28px] bg-[var(--bg-card-glass)] border border-[var(--border)] backdrop-blur-xl">
            <div className="w-12 h-12 rounded-[16px] bg-[rgba(228,88,140,0.14)] text-[var(--pink)] flex items-center justify-center mb-5">
              <Users size={24} />
            </div>
            <strong className="text-base font-extrabold text-[var(--text)] block mb-2">
              03 / Connect & Collaborate
            </strong>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] leading-relaxed m-0">
              Join active interest circles, form multidisciplinary project teams, and attend verified events with like-minded collaborators.
            </p>
          </div>
        </div>
      </section>

      {/* Privacy Guarantee Banner */}
      <section className="mt-16" aria-label="Privacy guarantee">
        <div className="p-8 rounded-[32px] bg-[var(--bg-card-glass)] border border-[var(--border)] backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-start gap-4 max-w-2xl">
            <div className="w-12 h-12 rounded-[16px] bg-[rgba(74,222,128,0.14)] text-[var(--success)] flex items-center justify-center shrink-0">
              <ShieldCheck size={26} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[var(--text)] mb-1.5">
                Privacy-Preserving Architecture Guarantee
              </h3>
              <p className="text-xs sm:text-sm text-[var(--text-muted)] leading-relaxed m-0">
                Your exact GPS coordinates are <strong>never</strong> transmitted to other users or logged.
                With our 0.01° grid snapping (~1.1 km) and coarse distance bands, recommendations stay localized while
                preventing location triangulation.
              </p>
            </div>
          </div>
          <Link
            to="/settings"
            className="px-5 py-2.5 rounded-full border border-[var(--border)] hover:border-[var(--lilac)] text-xs font-bold text-[var(--text)] transition-all shrink-0"
          >
            Configure Privacy Controls →
          </Link>
        </div>
      </section>

      {/* Featured Communities */}
      <section className="mt-16 md:mt-20">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight">
              Find your kind of people
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1">
              Vibrant circles built around shared crafts, research, and passions.
            </p>
          </div>
          <Link
            to="/communities"
            className="text-xs font-bold text-[var(--lime)] hover:underline"
          >
            All communities →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {communities.length > 0 ? (
            communities.map((c) => (
              <CommunityCard
                key={c.id}
                community={c}
                onOpenDetail={(comm) =>
                  setModalData({
                    kind: `Community · ${comm.category}`,
                    title: comm.name,
                    description: comm.description,
                    imageUrl: comm.image_url || undefined,
                    actionText: "Visit Community",
                    onAction: () => {
                      window.location.href = `/communities/${comm.id}`;
                    },
                  })
                }
              />
            ))
          ) : (
            <div className="col-span-full text-center py-12 rounded-[28px] bg-[var(--bg-card-glass)] border border-[var(--border)]">
              <p className="text-sm text-[var(--text-muted)] mb-4">
                No communities created yet. Be the first to start a circle.
              </p>
              <Link
                to="/communities"
                className="px-5 py-2.5 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-xs"
              >
                Start a Community
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Featured Events */}
      <section className="mt-16 md:mt-20">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight">
              Happening soon
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1">
              Verified gatherings, workshops, and meetups in your area.
            </p>
          </div>
          <Link to="/events" className="text-xs font-bold text-[var(--lime)] hover:underline">
            All events →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {events.length > 0 ? (
            events.map((e) => (
              <EventCard
                key={e.id}
                event={e}
                onOpenDetail={(evt) =>
                  setModalData({
                    kind: `Event · ${evt.category}`,
                    title: evt.title,
                    description: evt.description,
                    actionText: "Explore Event",
                    onAction: () => {
                      window.location.href = "/events";
                    },
                  })
                }
              />
            ))
          ) : (
            <div className="col-span-full text-center py-12 rounded-[28px] bg-[var(--bg-card-glass)] border border-[var(--border)]">
              <p className="text-sm text-[var(--text-muted)] mb-4">
                No upcoming events scheduled right now. Check back soon or host your own.
              </p>
              <Link
                to="/events"
                className="px-5 py-2.5 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-xs"
              >
                Host an Event
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Featured Places */}
      <section className="mt-16 md:mt-20">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight">
              Spaces worth finding
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1">
              Verified co-working studios, quiet cafes, and collaborative makerspaces.
            </p>
          </div>
          <Link to="/places" className="text-xs font-bold text-[var(--lime)] hover:underline">
            All places →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {places.length > 0 ? (
            places.map((p) => (
              <PlaceCard
                key={p.id}
                place={p}
                onOpenDetail={(pl) =>
                  setModalData({
                    kind: `Place · ${pl.category}`,
                    title: pl.name,
                    description: `${pl.address}, ${pl.city}. ${pl.description}`,
                    actionText: "View on Map",
                    onAction: () => {
                      window.open(
                        `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                          `${pl.name}, ${pl.address || ""} ${pl.city}`
                        )}`,
                        "_blank"
                      );
                    },
                  })
                }
              />
            ))
          ) : (
            <div className="col-span-full text-center py-12 rounded-[28px] bg-[var(--bg-card-glass)] border border-[var(--border)]">
              <p className="text-sm text-[var(--text-muted)] mb-4">
                No verified places loaded yet in your region.
              </p>
              <Link
                to="/places"
                className="px-5 py-2.5 rounded-full border border-[var(--border)] text-xs font-bold"
              >
                Explore Places Directory
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Bottom CTA Banner */}
      <section className="mt-20 md:mt-24 p-10 md:p-14 rounded-[36px] bg-[var(--bg-elev)] border border-[var(--border)] shadow-2xl text-center backdrop-blur-2xl">
        <p className="eyebrow justify-center">ALIGN FRAMEWORK</p>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[var(--text)] tracking-tight mb-4">
          More than a feed. A feeling of belonging.
        </h2>
        <p className="text-base text-[var(--text-muted)] max-w-xl mx-auto mb-8">
          Intent-driven discovery brings the right communities, experiences, and collaborations directly into view.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/discover"
            className="py-3 px-8 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-extrabold text-sm hover:brightness-105 active:scale-95 transition-all shadow-md"
          >
            Explore Recommendations
          </Link>
          <Link
            to="/onboarding"
            className="py-3 px-8 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] hover:border-[var(--lilac)] text-[var(--text)] font-semibold text-sm transition-all"
          >
            Personalize Interests
          </Link>
        </div>
      </section>

      <ContentDetailModal data={modalData} onClose={() => setModalData(null)} />
    </AppShell>
  );
}
