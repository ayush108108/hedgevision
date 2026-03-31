import React from "react";
import { AlertCircle, XCircle, AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorDisplayProps {
  error: Error | unknown;
  context?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorDisplay({
  error,
  context,
  onRetry,
  className = "",
}: ErrorDisplayProps) {
  const errorMessage =
    error instanceof Error ? error.message : "An unexpected error occurred";
  const errorType = getErrorType(errorMessage);

  return (
    <div
      className={`p-6 rounded-2xl border ${getErrorStyles(errorType)} ${className}`}
    >
      <div className="flex items-start gap-4">
        {getErrorIcon(errorType)}
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-2">
            {getErrorTitle(errorType, context)}
          </h3>
          <p className="text-sm text-gray-300 mb-4">{errorMessage}</p>
          {getErrorSuggestion(errorType) && (
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 mb-4">
              <p className="text-sm text-gray-400">
                <strong className="text-white">Suggestion:</strong>{" "}
                {getErrorSuggestion(errorType)}
              </p>
            </div>
          )}
          {onRetry && (
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface InlineErrorProps {
  message: string;
  className?: string;
}

export function InlineError({ message, className = "" }: InlineErrorProps) {
  return (
    <div
      className={`flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm ${className}`}
    >
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
}

interface ValidationErrorProps {
  errors: Record<string, string>;
  className?: string;
}

export function ValidationError({
  errors,
  className = "",
}: ValidationErrorProps) {
  const errorEntries = Object.entries(errors);

  if (errorEntries.length === 0) return null;

  return (
    <div
      className={`p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 ${className}`}
    >
      <div className="flex items-start gap-2 mb-2">
        <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium text-yellow-300 mb-2">
            Please fix the following errors:
          </p>
          <ul className="space-y-1">
            {errorEntries.map(([field, message]) => (
              <li key={field} className="text-sm text-yellow-300/80">
                <strong className="capitalize">{field}:</strong> {message}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// Helper functions
type ErrorType =
  | "network"
  | "validation"
  | "not-found"
  | "server"
  | "timeout"
  | "unknown";

function getErrorType(message: string): ErrorType {
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes("network") || lowerMessage.includes("fetch")) {
    return "network";
  }
  if (lowerMessage.includes("validation") || lowerMessage.includes("invalid")) {
    return "validation";
  }
  if (lowerMessage.includes("not found") || lowerMessage.includes("404")) {
    return "not-found";
  }
  if (lowerMessage.includes("timeout") || lowerMessage.includes("timed out")) {
    return "timeout";
  }
  if (lowerMessage.includes("500") || lowerMessage.includes("server error")) {
    return "server";
  }

  return "unknown";
}

function getErrorStyles(type: ErrorType): string {
  switch (type) {
    case "network":
    case "timeout":
      return "bg-orange-500/10 border-orange-500/30";
    case "validation":
      return "bg-yellow-500/10 border-yellow-500/30";
    case "not-found":
      return "bg-blue-500/10 border-blue-500/30";
    case "server":
      return "bg-red-500/10 border-red-500/30";
    default:
      return "bg-gray-500/10 border-gray-500/30";
  }
}

function getErrorIcon(type: ErrorType) {
  const iconClass = "w-6 h-6 flex-shrink-0";

  switch (type) {
    case "network":
    case "timeout":
      return <AlertTriangle className={`${iconClass} text-orange-400`} />;
    case "validation":
      return <AlertCircle className={`${iconClass} text-yellow-400`} />;
    case "not-found":
      return <AlertCircle className={`${iconClass} text-blue-400`} />;
    case "server":
      return <XCircle className={`${iconClass} text-red-400`} />;
    default:
      return <AlertCircle className={`${iconClass} text-gray-400`} />;
  }
}

function getErrorTitle(type: ErrorType, context?: string): string {
  const prefix = context ? `${context}: ` : "";

  switch (type) {
    case "network":
      return `${prefix}Network Connection Error`;
    case "timeout":
      return `${prefix}Request Timeout`;
    case "validation":
      return `${prefix}Validation Error`;
    case "not-found":
      return `${prefix}Resource Not Found`;
    case "server":
      return `${prefix}Server Error`;
    default:
      return `${prefix}Error`;
  }
}

function getErrorSuggestion(type: ErrorType): string | null {
  switch (type) {
    case "network":
      return "Check your internet connection and try again. If the problem persists, the server may be down.";
    case "timeout":
      return "The request took too long. Try again or check your connection speed.";
    case "validation":
      return "Review the form fields and ensure all required information is provided correctly.";
    case "not-found":
      return "The requested resource could not be found. It may have been moved or deleted.";
    case "server":
      return "Our server encountered an error. Please try again later or contact support if the issue persists.";
    default:
      return null;
  }
}
