import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Eye, EyeOff, Sparkles } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api } from "../lib/api";

export default function Auth({ mode }: { mode: "login" | "register" }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  // Forgot password state
  const [forgotOpen, setForgotOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [tokenReceived, setTokenReceived] = useState<string | null>(null);
  const [googleLoaded, setGoogleLoaded] = useState(false);

  const navigate = useNavigate();
  const [params] = useSearchParams();
  const isRegister = mode === "register";

  const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID || "").trim();

  // If already authenticated, redirect logged-in users away from /login and /register
  useEffect(() => {
    const existingToken = localStorage.getItem("align_token");
    if (existingToken) {
      const isOnboarded = localStorage.getItem("align_onboarded");
      if (isOnboarded === "false") {
        navigate("/onboarding", { replace: true });
      } else {
        navigate(params.get("next") || "/feed", { replace: true });
      }
    }
  }, [navigate, params]);

  function formatAuthError(err: unknown): string {
    const raw = err instanceof Error ? err.message : String(err || "");
    const lower = raw.toLowerCase();
    if (lower.includes("popup_closed_by_user") || lower.includes("popup closed")) {
      return "Google sign-in was closed before completion. Please try again.";
    }
    if (lower.includes("access_denied")) {
      return "Google authentication was cancelled or permission was denied.";
    }
    if (lower.includes("incorrect email or password") || lower.includes("401") || lower.includes("unauthorized")) {
      return "The email or password you entered is incorrect. Please check your credentials and try again.";
    }
    if (lower.includes("already exists") || lower.includes("409")) {
      return "An account with this email already exists. Please sign in with your password or Google account.";
    }
    if (lower.includes("failed to fetch") || lower.includes("network") || lower.includes("connection")) {
      return "Network connection issue: Unable to connect to ALIGN servers. Please check your internet connection.";
    }
    if (lower.includes("too many requests") || lower.includes("429")) {
      return "Too many attempts detected. Please pause for 60 seconds before trying again.";
    }
    if (lower.includes("password is too common")) {
      return "Password is too common and easily guessable. Please choose a stronger password.";
    }
    return raw || "Authentication failed. Please verify your information and try again.";
  }

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const initGoogle = () => {
      if (!window.google?.accounts?.id) return;
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response: { credential: string }) => {
            try {
              setBusy(true);
              setError("");
              const result = await api.googleAuth(response.credential);
              localStorage.setItem("align_token", result.access_token);
              if (result.refresh_token) {
                localStorage.setItem("align_refresh_token", result.refresh_token);
              }
              if (result.name) localStorage.setItem("align_user_name", result.name);
              if (result.email) localStorage.setItem("align_user_email", result.email);
              localStorage.setItem("align_onboarded", String(result.onboarding_completed ?? false));
              if (result.onboarding_completed === false) {
                navigate("/onboarding");
              } else {
                navigate(params.get("next") || "/feed");
              }
            } catch (err) {
              setError(formatAuthError(err));
            } finally {
              setBusy(false);
            }
          },
        });

        const btnContainer = document.getElementById("google-signin-btn");
        if (btnContainer) {
          btnContainer.innerHTML = "";
          window.google.accounts.id.renderButton(btnContainer, {
            theme: "outline",
            size: "large",
            width: "100%",
            text: isRegister ? "signup_with" : "signin_with",
            shape: "pill",
          });
          setGoogleLoaded(true);
        }
      } catch (e) {
        console.error("Google sign in initialization error:", e);
      }
    };

    if (window.google?.accounts?.id) {
      initGoogle();
    } else {
      const interval = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(interval);
          initGoogle();
        }
      }, 300);
      return () => clearInterval(interval);
    }
  }, [isRegister, navigate, params, GOOGLE_CLIENT_ID]);

  const triggerGoogleSignIn = () => {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt();
    } else {
      setError("Google sign-in is initializing. Please verify your internet connection or ad-blocker settings.");
    }
  };

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isRegister) {
        await api.register({ name, email, password });
      }
      const result = await api.login({ email, password });
      localStorage.setItem("align_token", result.access_token);
      if (result.refresh_token) {
        localStorage.setItem("align_refresh_token", result.refresh_token);
      }
      if (result.name) localStorage.setItem("align_user_name", result.name);
      if (result.email) localStorage.setItem("align_user_email", result.email);
      localStorage.setItem("align_onboarded", String(result.onboarding_completed ?? false));
      if (result.onboarding_completed === false) {
        navigate("/onboarding");
      } else {
        navigate(params.get("next") || "/feed");
      }
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  async function requestReset(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.forgotPassword(resetEmail);
      if (res.dev_token) {
        setTokenReceived(res.dev_token);
        setResetToken(res.dev_token);
        setSuccess(`Instructions generated. (Dev token auto-filled for quick reset)`);
      } else {
        setSuccess(res.message);
      }
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  async function submitNewPassword(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api.resetPassword({ token: resetToken, new_password: newPassword });
      setSuccess(res.message);
      setTimeout(() => {
        setForgotOpen(false);
        setSuccess("Password updated! Please log in.");
      }, 1500);
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title={isRegister ? "Register" : "Sign in"} hideFooter>
      <div className="max-w-6xl mx-auto py-8 md:py-16 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
        {/* Left Column: Hero Narrative */}
        <section className="lg:col-span-6 flex flex-col items-start pr-0 lg:pr-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[rgba(167,121,232,0.12)] border border-[rgba(167,121,232,0.25)] text-[var(--lilac)] text-[11px] font-extrabold uppercase tracking-widest mb-6">
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

          <p className="text-base sm:text-lg text-[var(--text-muted)] leading-relaxed mb-8 max-w-xl">
            One small step toward communities, real-world experiences, and collaborative projects that match your genuine intent.
          </p>

          <div className="flex flex-wrap gap-3">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-xs font-semibold text-[var(--text)]">
              <span className="text-[var(--lilac)]">✳</span>
              <span>Shared interests</span>
            </div>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-xs font-semibold text-[var(--text)]">
              <span className="text-[var(--pink)]">↗</span>
              <span>Real experiences</span>
            </div>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[var(--bg-card-glass)] text-xs font-semibold text-[var(--text)]">
              <span className="text-[var(--peach)]">♡</span>
              <span>Meaningful connections</span>
            </div>
          </div>
        </section>

        {/* Right Column: Tall Rounded Auth Card (32px radius) */}
        <section className="lg:col-span-6 w-full max-w-lg mx-auto">
          <div className="rounded-[32px] bg-[var(--bg-elev)] border border-[var(--border)] p-8 sm:p-10 shadow-2xl backdrop-blur-2xl transition-all">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text)] mb-6 transition-colors"
            >
              <ArrowLeft size={14} />
              <span>Back home</span>
            </Link>

            {!forgotOpen ? (
              <>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight mb-2">
                  {isRegister ? "Create your account" : "Welcome back"}
                </h2>
                <p className="text-sm text-[var(--text-muted)] mb-8">
                  {isRegister
                    ? "Your people are closer than you think."
                    : "Your next discovery is waiting for you."}
                </p>

                {error && (
                  <div className="p-3.5 mb-6 rounded-[16px] bg-[rgba(255,107,107,0.12)] border border-[var(--danger)] text-[var(--danger)] text-xs font-semibold">
                    {error}
                  </div>
                )}
                {success && (
                  <div className="p-3.5 mb-6 rounded-[16px] bg-[rgba(74,222,128,0.12)] border border-[var(--success)] text-[var(--success)] text-xs font-semibold">
                    {success}
                  </div>
                )}

                {/* Google Sign In Pill */}
                <div className="mb-6">
                  <div
                    id="google-signin-btn"
                    className="min-h-[44px] flex justify-center"
                    style={{ display: googleLoaded ? "flex" : "none" }}
                  />

                  {!googleLoaded && (
                    <button
                      type="button"
                      onClick={triggerGoogleSignIn}
                      className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-full bg-white text-slate-800 font-semibold text-xs sm:text-sm hover:bg-slate-100 transition-all shadow-sm border border-slate-200"
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24">
                        <path
                          fill="#4285F4"
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        />
                        <path
                          fill="#34A853"
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        />
                        <path
                          fill="#FBBC05"
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                        />
                        <path
                          fill="#EA4335"
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                        />
                      </svg>
                      <span>{isRegister ? "Sign up with Google" : "Sign in with Google"}</span>
                    </button>
                  )}

                  {/* Divider */}
                  <div className="flex items-center my-6 text-[var(--text-muted)] text-xs gap-3">
                    <span className="flex-1 h-[1px] bg-[var(--border)]" />
                    <span>or continue with email</span>
                    <span className="flex-1 h-[1px] bg-[var(--border)]" />
                  </div>
                </div>

                {/* Email & Password Form */}
                <form onSubmit={submit} className="flex flex-col gap-4">
                  {isRegister && (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-[var(--text)]">Full name</label>
                      <input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        minLength={2}
                        placeholder="How should we call you?"
                        className="w-full"
                      />
                    </div>
                  )}

                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-[var(--text)]">Email address</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      autoComplete="email"
                      className="w-full"
                    />
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <div className="flex justify-between items-center">
                      <label className="text-xs font-bold text-[var(--text)]">Password</label>
                      {!isRegister && (
                        <button
                          type="button"
                          onClick={() => {
                            setForgotOpen(true);
                            setError("");
                            setSuccess("");
                          }}
                          className="text-xs font-semibold text-[var(--lilac)] hover:underline"
                        >
                          Forgot password?
                        </button>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type={show ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={isRegister ? 8 : 1}
                        autoComplete={isRegister ? "new-password" : "current-password"}
                        placeholder={isRegister ? "At least 8 characters" : "Your password"}
                        className="w-full pr-12"
                      />
                      <button
                        type="button"
                        onClick={() => setShow(!show)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text)]"
                        aria-label={show ? "Hide password" : "Show password"}
                      >
                        {show ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Primary Electric Lime CTA Button */}
                  <button
                    type="submit"
                    disabled={busy}
                    className="w-full mt-4 py-3.5 px-6 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-extrabold text-sm flex items-center justify-center gap-2 hover:brightness-105 active:scale-[0.99] transition-all shadow-md disabled:opacity-60"
                  >
                    <span>{busy ? "Please wait…" : isRegister ? "Create account" : "Sign in"}</span>
                    <ArrowRight size={16} />
                  </button>

                  {isRegister && (
                    <p className="text-[11px] text-[var(--text-muted)] text-center mt-2 leading-relaxed">
                      By creating an account, you agree to our{" "}
                      <Link to="/terms" className="underline text-[var(--text)] font-semibold">
                        Terms of Service
                      </Link>{" "}
                      and{" "}
                      <Link to="/privacy" className="underline text-[var(--text)] font-semibold">
                        Privacy Policy
                      </Link>
                      .
                    </p>
                  )}
                </form>

                <p className="text-center text-xs text-[var(--text-muted)] mt-6">
                  {isRegister ? "Already have an account?" : "New to ALIGN?"}{" "}
                  <Link
                    to={isRegister ? "/login" : "/register"}
                    className="font-bold text-[var(--lilac)] hover:underline ml-1"
                  >
                    {isRegister ? "Sign in" : "Create an account"}
                  </Link>
                </p>
              </>
            ) : (
              /* Forgot / Reset Password Flow */
              <>
                <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight mb-2">
                  Reset Password
                </h2>
                <p className="text-sm text-[var(--text-muted)] mb-6">
                  Enter your account email to receive a secure password reset token.
                </p>

                {error && (
                  <div className="p-3 mb-4 rounded-[16px] bg-[rgba(255,107,107,0.12)] border border-[var(--danger)] text-[var(--danger)] text-xs font-semibold">
                    {error}
                  </div>
                )}
                {success && (
                  <div className="p-3 mb-4 rounded-[16px] bg-[rgba(74,222,128,0.12)] border border-[var(--success)] text-[var(--success)] text-xs font-semibold">
                    {success}
                  </div>
                )}

                {!tokenReceived ? (
                  <form onSubmit={requestReset} className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-[var(--text)]">Registered Email</label>
                      <input
                        type="email"
                        value={resetEmail}
                        onChange={(e) => setResetEmail(e.target.value)}
                        required
                        placeholder="you@example.com"
                        className="w-full"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={busy}
                      className="w-full py-3 px-6 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-sm hover:brightness-105 transition-all"
                    >
                      {busy ? "Sending..." : "Request Reset Token"}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={submitNewPassword} className="flex flex-col gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-[var(--text)]">Reset Token</label>
                      <input
                        value={resetToken}
                        onChange={(e) => setResetToken(e.target.value)}
                        required
                        placeholder="Paste your reset token"
                        className="w-full"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-[var(--text)]">New Password (min 8 chars)</label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        minLength={8}
                        placeholder="At least 8 characters"
                        className="w-full"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={busy}
                      className="w-full py-3 px-6 rounded-full bg-[var(--lime)] text-[var(--on-lime)] font-bold text-sm hover:brightness-105 transition-all"
                    >
                      {busy ? "Resetting..." : "Set New Password"}
                    </button>
                  </form>
                )}

                <button
                  type="button"
                  onClick={() => {
                    setForgotOpen(false);
                    setTokenReceived(null);
                    setError("");
                    setSuccess("");
                  }}
                  className="mt-6 text-xs text-[var(--text-muted)] hover:text-[var(--text)] text-center w-full block transition-colors"
                >
                  ← Back to sign in
                </button>
              </>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
