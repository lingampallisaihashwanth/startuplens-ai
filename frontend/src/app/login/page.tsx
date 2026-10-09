"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading, login, startOAuth } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);

  // If already authenticated, redirect to workspace
  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/");
    }
  }, [user, authLoading, router]);

  // Derive error banner from searchParams without cascading renders
  const queryError = searchParams.get("error");
  let queryErrorMsg: string | null = null;
  if (queryError) {
    if (queryError === "google_failed") {
      queryErrorMsg = "Google sign-in could not be completed.";
    } else if (queryError === "github_failed") {
      queryErrorMsg = "GitHub sign-in could not be completed.";
    } else if (queryError === "linkedin_failed") {
      queryErrorMsg = "LinkedIn sign-in could not be completed.";
    } else if (queryError === "cancelled") {
      queryErrorMsg = "Sign-in was cancelled.";
    } else if (queryError === "email_unverified") {
      queryErrorMsg = "Your email address is not verified by the provider.";
    } else if (queryError === "missing_email") {
      queryErrorMsg = "Your provider account does not have an accessible email address.";
    } else {
      queryErrorMsg = "Sign-in could not be completed.";
    }
  }

  const errorMsg = formError || queryErrorMsg;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setFormError("Please enter both email and password.");
      return;
    }
    setFormError(null);
    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      router.replace("/");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to sign in. Please verify your credentials.";
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleOAuth = (provider: "google" | "github" | "linkedin") => {
    setFormError(null);
    setOauthLoading(provider);
    startOAuth(provider);
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-2xl backdrop-blur-sm transition-all duration-200">
      {/* Brand Header */}
      <div className="mb-6 text-center">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] text-sm font-bold text-[var(--accent)] font-mono mb-3 shadow-inner">
          SL
        </div>
        <h1 className="text-xl font-bold tracking-tight text-[var(--foreground)]">StartupLens AI</h1>
        <p className="mt-1 text-xs text-[var(--muted)]">Welcome back</p>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div
          role="alert"
          aria-live="polite"
          className="mb-5 flex items-start gap-2.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 p-3 text-xs text-[var(--danger)] animate-in fade-in duration-200"
        >
          <svg className="h-4 w-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="flex-1 leading-relaxed">{errorMsg}</span>
        </div>
      )}

      {/* Social Logins */}
      <div className="space-y-2.5">
        <button
          type="button"
          id="btn-google-login"
          disabled={submitting || oauthLoading !== null}
          onClick={() => handleOAuth("google")}
          className="relative flex w-full items-center justify-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-4 py-2.5 text-xs font-semibold text-[var(--foreground)] transition-all hover:bg-[var(--surface-hover)] hover:border-[var(--border)]/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)] disabled:opacity-50 cursor-pointer"
        >
          {oauthLoading === "google" ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--muted)] border-t-[var(--accent)]" />
          ) : (
            <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
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
          )}
          <span>Continue with Google</span>
        </button>

        <button
          type="button"
          id="btn-github-login"
          disabled={submitting || oauthLoading !== null}
          onClick={() => handleOAuth("github")}
          className="relative flex w-full items-center justify-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-4 py-2.5 text-xs font-semibold text-[var(--foreground)] transition-all hover:bg-[var(--surface-hover)] hover:border-[var(--border)]/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)] disabled:opacity-50 cursor-pointer"
        >
          {oauthLoading === "github" ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--muted)] border-t-[var(--accent)]" />
          ) : (
            <svg className="h-4 w-4 shrink-0 fill-current" viewBox="0 0 24 24">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
              />
            </svg>
          )}
          <span>Continue with GitHub</span>
        </button>

        <button
          type="button"
          id="btn-linkedin-login"
          disabled={submitting || oauthLoading !== null}
          onClick={() => handleOAuth("linkedin")}
          className="relative flex w-full items-center justify-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-4 py-2.5 text-xs font-semibold text-[var(--foreground)] transition-all hover:bg-[var(--surface-hover)] hover:border-[var(--border)]/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)] disabled:opacity-50 cursor-pointer"
        >
          {oauthLoading === "linkedin" ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--muted)] border-t-[var(--accent)]" />
          ) : (
            <svg className="h-4 w-4 shrink-0 fill-[#0A66C2]" viewBox="0 0 24 24">
              <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
            </svg>
          )}
          <span>Continue with LinkedIn</span>
        </button>
      </div>

      {/* Divider */}
      <div className="relative my-6 flex items-center justify-center">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-[var(--border)]" />
        </div>
        <div className="relative bg-[var(--surface)] px-3 text-[10px] font-semibold tracking-wider text-[var(--muted)] uppercase">
          OR
        </div>
      </div>

      {/* Email / Password Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="founder@example.com"
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-3.5 py-2 text-xs text-[var(--foreground)] placeholder:text-[var(--muted)] focus-visible:outline-none focus:border-[var(--focus)] transition-colors"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-3.5 py-2 text-xs text-[var(--foreground)] placeholder:text-[var(--muted)] focus-visible:outline-none focus:border-[var(--focus)] transition-colors"
          />
        </div>

        <button
          type="submit"
          id="btn-sign-in"
          disabled={submitting || oauthLoading !== null}
          className="w-full rounded-xl bg-[var(--accent)] py-2.5 text-xs font-semibold text-white shadow-md transition-all hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)] disabled:opacity-50 cursor-pointer mt-2"
        >
          {submitting ? "Signing in..." : "Sign In"}
        </button>
      </form>

      {/* Footer link */}
      <div className="mt-6 text-center text-xs text-[var(--muted)]">
        <span>Don&apos;t have an account? </span>
        <Link
          href="/signup"
          className="font-medium text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus)] rounded"
        >
          Create account
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--background)]">
      <Suspense
        fallback={
          <div className="text-xs text-[var(--muted)] animate-pulse">Loading sign-in...</div>
        }
      >
        <LoginForm />
      </Suspense>
    </div>
  );
}
