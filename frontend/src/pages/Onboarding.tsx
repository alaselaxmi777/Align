import { FormEvent, useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  AtSign,
  Camera,
  CheckCircle2,
  Globe,
  LoaderCircle,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  User,
  Wrench,
  X,
  XCircle,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, CategorySummary, HobbyMaster, SkillMaster, resolveMediaUrl } from "../lib/api";

const MAHARASHTRA_CITIES = [
  "Pune",
  "Mumbai",
  "Nagpur",
  "Nashik",
  "Kolhapur",
  "Chhatrapati Sambhajinagar",
  "Thane",
  "Solapur",
  "Amravati",
  "Satara",
  "Sangli",
  "Navi Mumbai",
  "Other / Outside Maharashtra",
];

const AGE_COHORTS = ["18-24", "25-34", "35-44", "45+"];
const GENDERS = ["Female", "Male", "Non-binary", "Prefer not to say"];
const LANGUAGES = ["English", "Marathi (मराठी)", "Hindi (हिंदी)", "Hinglish"];

const SUGGESTED_INTERESTS = [
  "Artificial Intelligence",
  "Machine Learning",
  "Web Development",
  "Data Science",
  "Cloud Computing",
  "UI/UX Design",
  "Cybersecurity",
  "Blockchain",
  "Open Source",
  "Mobile Apps",
  "DevOps",
  "Robotics",
];

const SUGGESTED_ACTIVITIES = [
  "Hackathons",
  "Tech Meetups",
  "Pair Programming",
  "Workshops",
  "Open Source Sprints",
  "Paper Reading Groups",
  "Startup Discussions",
  "Weekend Treks",
];

const SUGGESTED_COMMUNITY_TYPES = [
  "Technical & Engineering",
  "Research & Academia",
  "Startups & Indie Hackers",
  "Creative & Design",
  "Career & Mentorship",
  "Student & Learning Circles",
];

const PROFICIENCY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"];

export default function Onboarding() {
  const navigate = useNavigate();

  // Navigation step: 1 (Username) -> 2 (Identity & Photo) -> 3 (Age & Location) -> 4 (Interests & Skills)
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [loading, setLoading] = useState(false);
  const [fetchingExisting, setFetchingExisting] = useState(true);
  const [error, setError] = useState("");

  // Step 1: Username
  const [username, setUsername] = useState("");
  const [checkingUsername, setCheckingUsername] = useState(false);
  const [usernameStatus, setUsernameStatus] = useState<{
    available?: boolean;
    message?: string;
  }>({});

  // Step 2: Identity & Avatar
  const [fullName, setFullName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string | null>(null);
  const localPreviewRef = useRef<string | null>(null);
  const [avatarLoadError, setAvatarLoadError] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [bio, setBio] = useState("");

  // Step 3: Age & Location
  const [ageCohort, setAgeCohort] = useState("18-24");
  const [gender, setGender] = useState("Prefer not to say");
  const [language, setLanguage] = useState("English");
  const [city, setCity] = useState("Pune");
  const [locationPrivacy, setLocationPrivacy] = useState("approximate");

  // Step 4: Interests & Skills
  const [skills, setSkills] = useState<string[]>([]);
  const [skillProficiency, setSkillProficiency] = useState("Intermediate");
  const [hobbies, setHobbies] = useState<string[]>([]);
  const [interests, setInterests] = useState<string[]>([]);
  const [goals, setGoals] = useState("");
  const [activities, setActivities] = useState<string[]>([]);
  const [communityTypes, setCommunityTypes] = useState<string[]>([]);

  // Dataset Masters
  const [masterSkills, setMasterSkills] = useState<SkillMaster[]>([]);
  const [skillCats, setSkillCats] = useState<CategorySummary[]>([]);
  const [selectedSkillCategory, setSelectedSkillCategory] = useState("All");
  const [skillSearchQuery, setSkillSearchQuery] = useState("");

  const [masterHobbies, setMasterHobbies] = useState<HobbyMaster[]>([]);
  const [hobbyCats, setHobbyCats] = useState<CategorySummary[]>([]);
  const [selectedHobbyCategory, setSelectedHobbyCategory] = useState("All");
  const [hobbySearchQuery, setHobbySearchQuery] = useState("");

  const [catalogsLoading, setCatalogsLoading] = useState(true);
  const [catalogsError, setCatalogsError] = useState<string | null>(null);

  // Revoke object URL on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (localPreviewRef.current) {
        URL.revokeObjectURL(localPreviewRef.current);
      }
    };
  }, []);

  async function loadCatalogs() {
    setCatalogsLoading(true);
    setCatalogsError(null);
    try {
      const [sList, sCategories, hList, hCategories] = await Promise.all([
        api.skills({ limit: 100 }),
        api.skillCategories(),
        api.hobbies({ limit: 100 }),
        api.hobbyCategories(),
      ]);
      setMasterSkills(sList || []);
      setSkillCats(sCategories || []);
      setMasterHobbies(hList || []);
      setHobbyCats(hCategories || []);
    } catch (err) {
      console.error("Failed to load catalogs:", err);
      setCatalogsError(err instanceof Error ? err.message : "Failed to load skills and hobbies");
    } finally {
      setCatalogsLoading(false);
    }
  }

  // Load existing profile & dataset catalogs
  useEffect(() => {
    async function loadData() {
      try {
        const u = await api.me().catch(() => null);
        loadCatalogs();

        if (u) {
          if (u.name) setFullName(u.name);
          if (u.username) {
            setUsername(u.username);
            setUsernameStatus({ available: true, message: "Current username" });
          } else {
            // Suggest username from name
            const suggested = u.name.toLowerCase().replace(/[^a-z0-9]/g, "_").slice(0, 16);
            if (suggested.length >= 3) setUsername(suggested);
          }

          if (u.profile) {
            if (u.profile.onboarding_completed) {
              localStorage.setItem("align_onboarded", "true");
              navigate("/feed", { replace: true });
              return;
            }
            if (u.profile.avatar_url) setAvatarUrl(u.profile.avatar_url);
            if (u.profile.bio) setBio(u.profile.bio);
            if (u.profile.location) setCity(u.profile.location);
            if (u.profile.age_cohort) setAgeCohort(u.profile.age_cohort);
            if (u.profile.gender) setGender(u.profile.gender);
            if (u.profile.preferred_language) setLanguage(u.profile.preferred_language);
            if (u.profile.location_privacy) setLocationPrivacy(u.profile.location_privacy);
            if (u.profile.interests) {
              setInterests(u.profile.interests.split(",").map((s) => s.trim()).filter(Boolean));
            }
            if (u.profile.skills) {
              setSkills(u.profile.skills.split(",").map((s) => s.trim()).filter(Boolean));
            }
            if (u.profile.hobbies) {
              setHobbies(u.profile.hobbies.split(",").map((s) => s.trim()).filter(Boolean));
            }
            if (u.profile.goals) setGoals(u.profile.goals);
            if (u.profile.preferred_activities) {
              setActivities(u.profile.preferred_activities.split(",").map((s) => s.trim()).filter(Boolean));
            }
            if (u.profile.preferred_community_types) {
              setCommunityTypes(u.profile.preferred_community_types.split(",").map((s) => s.trim()).filter(Boolean));
            }

            // Resume at saved step
            if (u.profile.onboarding_step && u.profile.onboarding_step >= 1 && u.profile.onboarding_step <= 4) {
              setStep(u.profile.onboarding_step as 1 | 2 | 3 | 4);
            }
          }
        }
      } catch (err) {
        console.error("Could not load onboarding context:", err);
      } finally {
        setFetchingExisting(false);
      }
    }
    loadData();
  }, [navigate]);

  // Live debounced username check
  useEffect(() => {
    if (!username.trim() || username.length < 3) {
      setUsernameStatus({});
      return;
    }
    const timer = setTimeout(async () => {
      setCheckingUsername(true);
      try {
        const res = await api.checkUsername(username.trim());
        setUsernameStatus(res);
      } catch (err) {
        setUsernameStatus({
          available: false,
          message: err instanceof Error ? err.message : "Error validating handle",
        });
      } finally {
        setCheckingUsername(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [username]);

  // Handle avatar file upload with instant WebP/preview
  async function handleAvatarUpload(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file (JPEG, PNG, or WebP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Avatar image must be smaller than 10MB.");
      return;
    }
    setError("");
    setAvatarLoadError(false);

    // Immediate local preview with blob URL (revoked on unmount or file change)
    if (localPreviewRef.current) {
      URL.revokeObjectURL(localPreviewRef.current);
    }
    const objUrl = URL.createObjectURL(file);
    localPreviewRef.current = objUrl;
    setLocalPreviewUrl(objUrl);

    setAvatarUploading(true);
    try {
      const res = await api.uploadImageVariant(file, "User avatar");
      const savedUrl = res.feed_url || res.thumbnail_url || res.original_url;
      setAvatarUrl(savedUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload avatar image.");
    } finally {
      setAvatarUploading(false);
    }
  }

  function addCustomSkill(val?: string) {
    const raw = (val || skillSearchQuery).trim();
    if (!raw) return;
    const canonical = masterSkills.find((s) => s.type.toLowerCase() === raw.toLowerCase())?.type || raw;
    if (!skills.includes(canonical)) {
      setSkills([...skills, canonical]);
    }
    setSkillSearchQuery("");
  }

  function removeSkill(item: string) {
    setSkills(skills.filter((s) => s !== item));
  }

  function addCustomHobby(val?: string) {
    const raw = (val || hobbySearchQuery).trim();
    if (!raw) return;
    const canonical = masterHobbies.find((h) => h.type.toLowerCase() === raw.toLowerCase())?.type || raw;
    if (!hobbies.includes(canonical)) {
      setHobbies([...hobbies, canonical]);
    }
    setHobbySearchQuery("");
  }

  function removeHobby(item: string) {
    setHobbies(hobbies.filter((h) => h !== item));
  }

  function toggleChip(list: string[], setList: (val: string[]) => void, item: string) {
    if (list.includes(item)) {
      setList(list.filter((x) => x !== item));
    } else {
      setList([...list, item]);
    }
  }

  // Step 1 Validation & Progression
  async function handleStep1Next() {
    if (!username.trim() || username.length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }
    if (usernameStatus.available === false) {
      setError(usernameStatus.message || "This username is not available.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await api.completeOnboarding({
        username: username.trim().toLowerCase(),
        step: 2,
      });
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save username.");
    } finally {
      setLoading(false);
    }
  }

  // Step 2 Validation & Progression
  async function handleStep2Next() {
    if (!fullName.trim() || fullName.trim().length < 2) {
      setError("Please enter your full name (at least 2 characters).");
      return;
    }
    if (!bio.trim() || bio.trim().length < 10) {
      setError("Please provide a short bio (at least 10 characters) to help peers connect with you.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await api.completeOnboarding({
        name: fullName.trim(),
        avatar_url: avatarUrl,
        bio: bio.trim(),
        step: 3,
      });
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile identity.");
    } finally {
      setLoading(false);
    }
  }

  // Step 3 Validation & Progression
  async function handleStep3Next() {
    setError("");
    setLoading(true);
    try {
      await api.completeOnboarding({
        age_cohort: ageCohort,
        gender: gender,
        preferred_language: language,
        location: city,
        privacy_level: locationPrivacy === "hidden" ? "private" : "public",
        step: 3,
      });
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save context preferences.");
    } finally {
      setLoading(false);
    }
  }

  // Step 4 Final Completion
  async function handleFinalSubmit(e: FormEvent) {
    e.preventDefault();
    if (skills.length === 0) {
      setError("Please select at least 1 technical skill or domain interest.");
      return;
    }
    if (!goals.trim() || goals.trim().length < 5) {
      setError("Please share what you are hoping to learn, build, or discover on ALIGN.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await api.completeOnboarding({
        username: username.trim().toLowerCase(),
        name: fullName.trim(),
        avatar_url: avatarUrl,
        bio: bio.trim(),
        age_cohort: ageCohort,
        gender: gender,
        preferred_language: language,
        location: city,
        privacy_level: locationPrivacy === "hidden" ? "private" : "public",
        skills: skills.join(", "),
        skill_proficiency: skillProficiency,
        hobbies: hobbies.join(", "),
        interests: interests.join(", "),
        goals: goals.trim(),
        preferred_activities: activities.join(", "),
        preferred_community_types: communityTypes.join(", "),
        step: 4,
      });

      localStorage.setItem("align_onboarded", "true");
      navigate("/feed", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to finish onboarding. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  // Filter skills
  const filteredSkills = masterSkills.filter((s) => {
    const matchCat = selectedSkillCategory === "All" || s.category === selectedSkillCategory;
    const matchQ = !skillSearchQuery.trim() || s.type.toLowerCase().includes(skillSearchQuery.toLowerCase());
    return matchCat && matchQ;
  });

  // Filter hobbies
  const filteredHobbies = masterHobbies.filter((h) => {
    const matchCat = selectedHobbyCategory === "All" || h.category === selectedHobbyCategory;
    const matchQ = !hobbySearchQuery.trim() || h.type.toLowerCase().includes(hobbySearchQuery.toLowerCase());
    return matchCat && matchQ;
  });

  if (fetchingExisting) {
    return (
      <AppShell title="Onboarding">
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
          <LoaderCircle size={32} className="animate-spin text-[var(--lilac)]" />
          <p className="text-sm">Setting up your personalized onboarding…</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Profile Setup">
      <div className="max-w-2xl mx-auto py-8 px-4">
        {/* Progress Tracker */}
        <div className="mb-8">
          <div className="flex items-center justify-between text-xs font-bold text-[var(--text-muted)] mb-2">
            <span>Step {step} of 4</span>
            <span>
              {step === 1 && "Choose Username"}
              {step === 2 && "Profile Identity"}
              {step === 3 && "Demographics & Location"}
              {step === 4 && "Skills & Intent"}
            </span>
          </div>
          <div className="h-2 w-full bg-[var(--surface-muted)] rounded-full overflow-hidden flex gap-1">
            <div
              className={`h-full flex-1 rounded-full transition-all duration-300 ${
                step >= 1 ? "bg-[var(--lilac)]" : "bg-transparent"
              }`}
            />
            <div
              className={`h-full flex-1 rounded-full transition-all duration-300 ${
                step >= 2 ? "bg-[var(--lilac)]" : "bg-transparent"
              }`}
            />
            <div
              className={`h-full flex-1 rounded-full transition-all duration-300 ${
                step >= 3 ? "bg-[var(--lilac)]" : "bg-transparent"
              }`}
            />
            <div
              className={`h-full flex-1 rounded-full transition-all duration-300 ${
                step >= 4 ? "bg-[var(--lime)]" : "bg-transparent"
              }`}
            />
          </div>
        </div>

        {/* Card Container */}
        <div className="p-8 rounded-3xl bg-[var(--surface)] border border-[var(--border)] shadow-xl">
          {error && (
            <div className="p-3.5 mb-6 rounded-2xl bg-[rgba(255,107,107,0.12)] border border-[var(--danger)] text-[var(--danger)] text-xs font-semibold">
              {error}
            </div>
          )}

          {/* ================= STEP 1: USERNAME ================= */}
          {step === 1 && (
            <div className="flex flex-col gap-6">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wider text-[var(--lilac)] mb-1">
                  Identity & Handle
                </p>
                <h1 className="text-2xl font-black text-[var(--text)] tracking-tight">
                  Claim your unique ALIGN handle
                </h1>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  This is your public identifier across Maharashtra for peer discovery, @mentions, and reels.
                </p>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-[var(--text)]">Username</label>
                <div className="relative flex items-center">
                  <span className="absolute left-4 text-[var(--text-muted)] font-bold">@</span>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
                    maxLength={20}
                    placeholder="your_handle"
                    className="w-full pl-9 pr-12 py-3 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] font-semibold text-sm focus:outline-none focus:border-[var(--lilac)]"
                  />
                  <div className="absolute right-4 flex items-center">
                    {checkingUsername && <LoaderCircle size={18} className="animate-spin text-slate-400" />}
                    {!checkingUsername && usernameStatus.available === true && (
                      <CheckCircle2 size={18} className="text-emerald-500" />
                    )}
                    {!checkingUsername && usernameStatus.available === false && (
                      <XCircle size={18} className="text-rose-500" />
                    )}
                  </div>
                </div>

                {usernameStatus.message && (
                  <p
                    className={`text-xs font-medium mt-1 ${
                      usernameStatus.available ? "text-emerald-500" : "text-rose-500"
                    }`}
                  >
                    {usernameStatus.message}
                  </p>
                )}

                <p className="text-[11px] text-[var(--text-muted)] mt-1">
                  • 3 to 20 characters · Lowercase letters, numbers, and underscores only.
                </p>
              </div>

              <div className="flex justify-end pt-4">
                <button
                  type="button"
                  onClick={handleStep1Next}
                  disabled={loading || checkingUsername || usernameStatus.available === false || username.length < 3}
                  className="py-3 px-6 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-extrabold text-sm flex items-center gap-2 hover:brightness-105 disabled:opacity-50 transition-all shadow-md"
                >
                  <span>{loading ? "Checking…" : "Continue to Profile"}</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* ================= STEP 2: PROFILE & AVATAR ================= */}
          {step === 2 && (
            <div className="flex flex-col gap-6">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wider text-[var(--lilac)] mb-1">
                  Profile Presentation
                </p>
                <h1 className="text-2xl font-black text-[var(--text)] tracking-tight">
                  Set up your profile photo and bio
                </h1>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Help creators, founders, and peers recognize you in the feed and communities.
                </p>
              </div>

              {/* Avatar Upload with Circular Preview & Initials Fallback */}
              {(() => {
                const displayAvatar = localPreviewUrl || resolveMediaUrl(avatarUrl);
                const userInitials = (fullName.trim() || username.trim() || "AL")
                  .split(/\s+/)
                  .slice(0, 2)
                  .map((s) => s[0].toUpperCase())
                  .join("");

                return (
                  <div className="flex items-center gap-6 p-4 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)]">
                    <div className="relative w-20 h-20 rounded-full overflow-hidden bg-slate-800 border-2 border-[var(--lilac)] flex items-center justify-center flex-shrink-0 shadow-md">
                      {displayAvatar && !avatarLoadError ? (
                        <img
                          src={displayAvatar}
                          alt="Avatar Preview"
                          onError={() => setAvatarLoadError(true)}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 text-white font-extrabold text-xl select-none">
                          {userInitials}
                        </div>
                      )}
                      {avatarUploading && (
                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                          <LoaderCircle size={22} className="animate-spin text-white" />
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-bold text-[var(--text)]">Profile Picture</label>
                      <div className="flex items-center gap-2 flex-wrap">
                        <label className="cursor-pointer inline-flex items-center gap-2 py-2 px-4 rounded-full bg-[var(--surface)] border border-[var(--border)] text-xs font-bold text-[var(--text)] hover:bg-[var(--border)] transition-all">
                          <Camera size={14} className="text-[var(--lilac)]" />
                          <span>{displayAvatar ? "Change Photo" : "Upload Photo"}</span>
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleAvatarUpload(file);
                            }}
                          />
                        </label>
                        {displayAvatar && (
                          <button
                            type="button"
                            onClick={() => {
                              if (localPreviewRef.current) {
                                URL.revokeObjectURL(localPreviewRef.current);
                                localPreviewRef.current = null;
                              }
                              setLocalPreviewUrl(null);
                              setAvatarUrl("");
                              setAvatarLoadError(false);
                            }}
                            className="text-xs font-semibold text-red-400 hover:text-red-300 px-3 py-1.5 rounded-full border border-red-500/30 bg-red-500/10 transition-all"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                      <span className="text-[11px] text-[var(--text-muted)]">
                        Instant preview · Square / circular crop · Max 10MB (JPEG, PNG, WebP)
                      </span>
                    </div>
                  </div>
                );
              })()}

              {/* Full Name */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-[var(--text)]">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="How should peers address you?"
                  className="w-full px-4 py-3 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] text-sm font-semibold focus:outline-none focus:border-[var(--lilac)]"
                />
              </div>

              {/* Bio */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-xs font-bold text-[var(--text)]">
                  <span>Bio</span>
                  <span className="text-[var(--text-muted)] font-normal">{bio.length}/250</span>
                </div>
                <textarea
                  value={bio}
                  onChange={(e) => setBio(e.target.value.slice(0, 250))}
                  rows={3}
                  placeholder="e.g. Full-stack builder in Pune exploring Rust, ML embeddings, and weekend cycling."
                  className="w-full px-4 py-3 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--lilac)] resize-none"
                />
              </div>

              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="py-3 px-5 rounded-full text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text)] flex items-center gap-1.5"
                >
                  <ArrowLeft size={16} />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={handleStep2Next}
                  disabled={loading || !fullName.trim() || bio.trim().length < 10}
                  className="py-3 px-6 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-extrabold text-sm flex items-center gap-2 hover:brightness-105 disabled:opacity-50 transition-all shadow-md"
                >
                  <span>{loading ? "Saving…" : "Continue to Context"}</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* ================= STEP 3: DEMOGRAPHICS & LOCATION ================= */}
          {step === 3 && (
            <div className="flex flex-col gap-6">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wider text-[var(--lilac)] mb-1">
                  18+ Safety & Regional Matching
                </p>
                <h1 className="text-2xl font-black text-[var(--text)] tracking-tight">
                  Demographics & Local Privacy
                </h1>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  ALIGN enforces strict 18+ policy boundaries and coarse-grid location obfuscation.
                </p>
              </div>

              {/* Age Cohort */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-[var(--text)] flex items-center gap-2">
                  <Shield size={14} className="text-[var(--lilac)]" />
                  Age Cohort (18+ Mandatory)
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {AGE_COHORTS.map((cohort) => (
                    <button
                      key={cohort}
                      type="button"
                      onClick={() => setAgeCohort(cohort)}
                      className={`py-2.5 px-3 rounded-2xl border text-xs font-bold transition-all ${
                        ageCohort === cohort
                          ? "bg-[var(--lilac)] text-white border-[var(--lilac)]"
                          : "bg-[var(--surface-muted)] text-[var(--text-muted)] border-[var(--border)] hover:border-slate-500"
                      }`}
                    >
                      {cohort}
                    </button>
                  ))}
                </div>
              </div>

              {/* Gender */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-[var(--text)]">Gender</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {GENDERS.map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setGender(g)}
                      className={`py-2.5 px-2 rounded-2xl border text-xs font-bold transition-all text-center truncate ${
                        gender === g
                          ? "bg-[var(--lilac)] text-white border-[var(--lilac)]"
                          : "bg-[var(--surface-muted)] text-[var(--text-muted)] border-[var(--border)] hover:border-slate-500"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>

              {/* Primary Language */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-[var(--text)] flex items-center gap-1.5">
                  <Globe size={14} className="text-[var(--lilac)]" />
                  Preferred Language
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {LANGUAGES.map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => setLanguage(lang)}
                      className={`py-2.5 px-3 rounded-2xl border text-xs font-bold transition-all text-left truncate ${
                        language === lang
                          ? "bg-[var(--lilac)] text-white border-[var(--lilac)]"
                          : "bg-[var(--surface-muted)] text-[var(--text-muted)] border-[var(--border)]"
                      }`}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
              </div>

              {/* City / Maharashtra Location */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-[var(--text)] flex items-center gap-1.5">
                  <MapPin size={14} className="text-[var(--lilac)]" />
                  Primary Hub / City
                </label>
                <select
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] text-sm font-semibold focus:outline-none focus:border-[var(--lilac)]"
                >
                  {MAHARASHTRA_CITIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-[var(--text-muted)]">
                  Coordinates are coarse-projected with random Gaussian offsets. No raw GPS is stored.
                </p>
              </div>

              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="py-3 px-5 rounded-full text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text)] flex items-center gap-1.5"
                >
                  <ArrowLeft size={16} />
                  <span>Back</span>
                </button>
                <button
                  type="button"
                  onClick={handleStep3Next}
                  disabled={loading}
                  className="py-3 px-6 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-extrabold text-sm flex items-center gap-2 hover:brightness-105 disabled:opacity-50 transition-all shadow-md"
                >
                  <span>{loading ? "Saving…" : "Continue to Interests"}</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* ================= STEP 4: INTERESTS, SKILLS & GOALS ================= */}
          {step === 4 && (
            <form onSubmit={handleFinalSubmit} className="flex flex-col gap-6">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-wider text-[var(--lime)] mb-1">
                  Semantic Discovery
                </p>
                <h1 className="text-2xl font-black text-[var(--text)] tracking-tight">
                  Your Skills, Hobbies & Intent Goals
                </h1>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  These inputs generate your 384-dimensional dense profile embedding for personalized recommendations.
                </p>
              </div>

              {/* Skills Multi-Select */}
              <div className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-[var(--text)] flex items-center gap-1.5">
                    <Wrench size={14} className="text-[var(--lilac)]" />
                    <span>Technical & Domain Skills (Pick at least 1)</span>
                  </label>
                  {skills.length > 0 && (
                    <span className="text-[11px] font-bold text-[var(--lilac)]">
                      {skills.length} selected
                    </span>
                  )}
                </div>

                {/* Selected Skills Chips */}
                {skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 p-2 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)]">
                    {skills.map((s) => (
                      <span
                        key={s}
                        className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-bold bg-[var(--lilac)] text-white shadow-sm"
                      >
                        <span>{s}</span>
                        <button
                          type="button"
                          onClick={() => removeSkill(s)}
                          className="hover:text-red-200 transition-colors cursor-pointer"
                          aria-label={`Remove ${s}`}
                        >
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {/* Search & Custom Input */}
                <div className="relative flex items-center">
                  <Search size={15} className="absolute left-3.5 text-slate-400" />
                  <input
                    type="text"
                    spellCheck="false"
                    value={skillSearchQuery}
                    onChange={(e) => setSkillSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addCustomSkill();
                      }
                    }}
                    placeholder="Search or add a skill (press Enter to add custom)..."
                    className="w-full pl-9 pr-24 py-2.5 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] text-xs font-medium focus:outline-none focus:border-[var(--lilac)]"
                  />
                  {skillSearchQuery.trim() && (
                    <button
                      type="button"
                      onClick={() => addCustomSkill()}
                      className="absolute right-2 px-2.5 py-1 rounded-lg bg-[var(--lilac)] text-white text-[11px] font-bold flex items-center gap-1 hover:brightness-110 cursor-pointer"
                    >
                      <Plus size={12} />
                      <span>Add</span>
                    </button>
                  )}
                </div>

                {/* Skill Category Filters */}
                {skillCats.length > 0 && (
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] no-scrollbar">
                    <button
                      type="button"
                      onClick={() => setSelectedSkillCategory("All")}
                      className={`px-2.5 py-1 rounded-lg font-semibold whitespace-nowrap transition-all cursor-pointer ${
                        selectedSkillCategory === "All"
                          ? "bg-[var(--lilac)] text-white"
                          : "bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] border border-[var(--border)]"
                      }`}
                    >
                      All ({masterSkills.length})
                    </button>
                    {skillCats.map((cat) => (
                      <button
                        key={cat.category}
                        type="button"
                        onClick={() => setSelectedSkillCategory(cat.category)}
                        className={`px-2.5 py-1 rounded-lg font-semibold whitespace-nowrap transition-all cursor-pointer ${
                          selectedSkillCategory === cat.category
                            ? "bg-[var(--lilac)] text-white"
                            : "bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] border border-[var(--border)]"
                        }`}
                      >
                        {cat.category} ({cat.count})
                      </button>
                    ))}
                  </div>
                )}

                {/* Suggestions / Options Panel */}
                <div className="flex flex-wrap gap-1.5 max-h-44 overflow-y-auto p-2.5 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)]">
                  {catalogsLoading ? (
                    <div className="flex items-center gap-2 py-4 px-3 w-full justify-center text-xs text-slate-400">
                      <LoaderCircle size={16} className="animate-spin text-[var(--lilac)]" />
                      <span>Loading technical skills catalog...</span>
                    </div>
                  ) : catalogsError ? (
                    <div className="flex items-center justify-between w-full p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300">
                      <div className="flex items-center gap-2">
                        <AlertTriangle size={15} />
                        <span>Could not load skills list: {catalogsError}</span>
                      </div>
                      <button
                        type="button"
                        onClick={loadCatalogs}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 font-bold transition-all text-red-200 cursor-pointer"
                      >
                        <RefreshCw size={12} />
                        <span>Retry</span>
                      </button>
                    </div>
                  ) : filteredSkills.length === 0 ? (
                    <div className="py-3 px-3 text-center w-full text-xs text-slate-400">
                      {skillSearchQuery.trim() ? (
                        <span>
                          No matches for "{skillSearchQuery}". Press <strong>Enter</strong> or click <strong>Add</strong> to create this custom skill.
                        </span>
                      ) : (
                        <span>No skills available in this category. Type above to add your own.</span>
                      )}
                    </div>
                  ) : (
                    filteredSkills.map((s) => {
                      const sel = skills.includes(s.type);
                      return (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => toggleChip(skills, setSkills, s.type)}
                          className={`py-1.5 px-3 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                            sel
                              ? "bg-[var(--lilac)] text-white border-[var(--lilac)] shadow-sm"
                              : "bg-[var(--surface)] text-[var(--text)] border-[var(--border)] hover:border-slate-500"
                          }`}
                        >
                          {sel ? `✓ ${s.type}` : `+ ${s.type}`}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Skill Proficiency Level */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-[var(--text)]">Self-Assessed Skill Level</label>
                <div className="grid grid-cols-4 gap-2">
                  {PROFICIENCY_LEVELS.map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setSkillProficiency(lvl)}
                      className={`py-2 px-2 rounded-2xl border text-xs font-bold transition-all text-center truncate cursor-pointer ${
                        skillProficiency === lvl
                          ? "bg-[var(--lilac)] text-white border-[var(--lilac)] shadow-sm"
                          : "bg-[var(--surface-muted)] text-[var(--text-muted)] border-[var(--border)] hover:text-[var(--text)]"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Hobbies Multi-Select */}
              <div className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-[var(--text)] flex items-center gap-1.5">
                    <Sparkles size={14} className="text-[var(--lime)]" />
                    <span>Hobbies & Passions</span>
                  </label>
                  {hobbies.length > 0 && (
                    <span className="text-[11px] font-bold text-[var(--lime)]">
                      {hobbies.length} selected
                    </span>
                  )}
                </div>

                {/* Selected Hobbies Chips */}
                {hobbies.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 p-2 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)]">
                    {hobbies.map((h) => (
                      <span
                        key={h}
                        className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-bold bg-[var(--lime)] text-[var(--on-lime)] shadow-sm"
                      >
                        <span>{h}</span>
                        <button
                          type="button"
                          onClick={() => removeHobby(h)}
                          className="hover:opacity-75 transition-opacity cursor-pointer"
                          aria-label={`Remove ${h}`}
                        >
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {/* Search & Custom Input */}
                <div className="relative flex items-center">
                  <Search size={15} className="absolute left-3.5 text-slate-400" />
                  <input
                    type="text"
                    spellCheck="false"
                    value={hobbySearchQuery}
                    onChange={(e) => setHobbySearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addCustomHobby();
                      }
                    }}
                    placeholder="Search or add a hobby (press Enter to add custom)..."
                    className="w-full pl-9 pr-24 py-2.5 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] text-xs font-medium focus:outline-none focus:border-[var(--lime)]"
                  />
                  {hobbySearchQuery.trim() && (
                    <button
                      type="button"
                      onClick={() => addCustomHobby()}
                      className="absolute right-2 px-2.5 py-1 rounded-lg bg-[var(--lime)] text-[var(--on-lime)] text-[11px] font-bold flex items-center gap-1 hover:brightness-105 cursor-pointer"
                    >
                      <Plus size={12} />
                      <span>Add</span>
                    </button>
                  )}
                </div>

                {/* Hobby Category Filters */}
                {hobbyCats.length > 0 && (
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] no-scrollbar">
                    <button
                      type="button"
                      onClick={() => setSelectedHobbyCategory("All")}
                      className={`px-2.5 py-1 rounded-lg font-semibold whitespace-nowrap transition-all cursor-pointer ${
                        selectedHobbyCategory === "All"
                          ? "bg-[var(--lime)] text-[var(--on-lime)] font-bold"
                          : "bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] border border-[var(--border)]"
                      }`}
                    >
                      All ({masterHobbies.length})
                    </button>
                    {hobbyCats.map((cat) => (
                      <button
                        key={cat.category}
                        type="button"
                        onClick={() => setSelectedHobbyCategory(cat.category)}
                        className={`px-2.5 py-1 rounded-lg font-semibold whitespace-nowrap transition-all cursor-pointer ${
                          selectedHobbyCategory === cat.category
                            ? "bg-[var(--lime)] text-[var(--on-lime)] font-bold"
                            : "bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] border border-[var(--border)]"
                        }`}
                      >
                        {cat.category} ({cat.count})
                      </button>
                    ))}
                  </div>
                )}

                {/* Suggestions / Options Panel */}
                <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto p-2.5 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)]">
                  {catalogsLoading ? (
                    <div className="flex items-center gap-2 py-4 px-3 w-full justify-center text-xs text-slate-400">
                      <LoaderCircle size={16} className="animate-spin text-[var(--lime)]" />
                      <span>Loading hobbies and interests catalog...</span>
                    </div>
                  ) : catalogsError ? (
                    <div className="flex items-center justify-between w-full p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300">
                      <div className="flex items-center gap-2">
                        <AlertTriangle size={15} />
                        <span>Could not load hobbies list</span>
                      </div>
                      <button
                        type="button"
                        onClick={loadCatalogs}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 font-bold transition-all text-red-200 cursor-pointer"
                      >
                        <RefreshCw size={12} />
                        <span>Retry</span>
                      </button>
                    </div>
                  ) : filteredHobbies.length === 0 ? (
                    <div className="py-3 px-3 text-center w-full text-xs text-slate-400">
                      {hobbySearchQuery.trim() ? (
                        <span>
                          No matches for "{hobbySearchQuery}". Press <strong>Enter</strong> or click <strong>Add</strong> to create this custom hobby.
                        </span>
                      ) : (
                        <span>No hobbies available in this category. Type above to add your own.</span>
                      )}
                    </div>
                  ) : (
                    filteredHobbies.map((h) => {
                      const sel = hobbies.includes(h.type);
                      return (
                        <button
                          key={h.id}
                          type="button"
                          onClick={() => toggleChip(hobbies, setHobbies, h.type)}
                          className={`py-1.5 px-3 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                            sel
                              ? "bg-[var(--lime)] text-[var(--on-lime)] border-[var(--lime)] font-bold shadow-sm"
                              : "bg-[var(--surface)] text-[var(--text)] border-[var(--border)] hover:border-slate-500"
                          }`}
                        >
                          {sel ? `✓ ${h.type}` : `+ ${h.type}`}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Goal Intent Text */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-[var(--text)]">
                  What are you currently looking to achieve?
                </label>
                <textarea
                  value={goals}
                  spellCheck="false"
                  onChange={(e) => setGoals(e.target.value)}
                  rows={3}
                  placeholder="e.g. Build an open-source vector database project, find a hackathon team, or learn Marathi literature."
                  className="w-full px-4 py-3 rounded-2xl bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--lime)] resize-none"
                />
              </div>

              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="py-3 px-5 rounded-full text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text)] flex items-center gap-1.5 cursor-pointer"
                >
                  <ArrowLeft size={16} />
                  <span>Back</span>
                </button>
                <div className="flex flex-col items-end gap-1">
                  <button
                    type="submit"
                    disabled={loading || skills.length === 0}
                    className="py-3.5 px-8 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-black text-sm flex items-center gap-2 hover:brightness-105 disabled:opacity-50 transition-all shadow-lg cursor-pointer disabled:cursor-not-allowed"
                  >
                    <span>{loading ? "Completing Setup…" : "Launch ALIGN"}</span>
                    <Sparkles size={16} />
                  </button>
                  {skills.length === 0 && (
                    <p className="text-[11px] text-amber-400 font-semibold tracking-wide">
                      Select or add at least 1 skill to launch ALIGN
                    </p>
                  )}
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </AppShell>
  );
}
