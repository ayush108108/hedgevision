import React, { useMemo, useState } from "react";
import { Mail, CheckCircle2, Loader2 } from "lucide-react";
import { submitWaitlistSignup } from "../../services/waitlist";

interface WaitlistCTAProps {
  title: string;
  description: string;
  sourcePage: string;
  sourceLabel?: string;
  id?: string;
  className?: string;
}

export function WaitlistCTA({
  title,
  description,
  sourcePage,
  sourceLabel,
  id,
  className = "",
}: WaitlistCTAProps) {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageTone, setMessageTone] = useState<"success" | "neutral" | "error">("success");

  const containerClassName = useMemo(
    () =>
      [
        "rounded-xl sm:rounded-2xl border border-blue-500/20 bg-gradient-to-r from-blue-500/10 to-purple-500/10",
        "px-4 py-5 sm:px-6 sm:py-8 text-center",
        className,
      ]
        .filter(Boolean)
        .join(" "),
    [className],
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim()) {
      return;
    }

    setIsSubmitting(true);
    setMessage(null);

    try {
      const viewport = typeof window !== "undefined" && window.innerWidth < 640 ? "mobile" : "desktop";
      const response = await submitWaitlistSignup({
        email: email.trim(),
        source_page: sourcePage,
        source_label: sourceLabel,
        metadata: { viewport },
      });

      setMessage(response.message);
      setMessageTone(response.status === "duplicate" ? "neutral" : "success");
      if (response.status === "created") {
        setEmail("");
      }
    } catch (error: any) {
      setMessage(
        error?.response?.data?.detail ||
          error?.message ||
          "Couldn’t save your email just yet. Please try again in a moment.",
      );
      setMessageTone("error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id={id} className={containerClassName}>
      <h3 className="text-xl sm:text-2xl font-bold text-white mb-2 sm:mb-3">{title}</h3>
      <p className="text-sm sm:text-base text-gray-300 mb-5 sm:mb-6 max-w-2xl mx-auto">{description}</p>

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row justify-center gap-3 max-w-2xl mx-auto">
        <label className="sr-only" htmlFor={`${sourcePage}-waitlist-email`}>
          Email address
        </label>
        <input
          id={`${sourcePage}-waitlist-email`}
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Enter your email"
          autoComplete="email"
          className="w-full sm:min-w-[280px] px-4 py-3 bg-white/5 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          disabled={isSubmitting}
          required
        />
        <button
          type="submit"
          disabled={isSubmitting || !email.trim()}
          className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40"
        >
          {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
          <span>{isSubmitting ? "Joining..." : "Join Waitlist"}</span>
        </button>
      </form>

      {message && (
        <div
          aria-live="polite"
          className={`mt-4 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
            messageTone === "error"
              ? "bg-red-500/10 text-red-300 border border-red-500/20"
              : messageTone === "neutral"
                ? "bg-blue-500/10 text-blue-200 border border-blue-500/20"
                : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
          }`}
        >
          {messageTone !== "error" && <CheckCircle2 className="h-4 w-4" />}
          <span>{message}</span>
        </div>
      )}

      <p className="text-xs text-gray-500 mt-4">No spam. Unsubscribe anytime. We respect your privacy.</p>
    </div>
  );
}
