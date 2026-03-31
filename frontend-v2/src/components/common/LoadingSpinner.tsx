import React from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { ErrorDisplay } from "./ErrorDisplay";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  text?: string;
  className?: string;
}

export function LoadingSpinner({
  size = "md",
  text,
  className = "",
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  };

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="flex flex-col items-center gap-3">
        <Loader2
          className={`${sizeClasses[size]} animate-spin text-blue-600`}
        />
        {text && <span className="text-sm text-gray-600">{text}</span>}
      </div>
    </div>
  );
}

interface RefreshButtonProps {
  onClick: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  text?: string;
  className?: string;
}

export function RefreshButton({
  onClick,
  isLoading = false,
  disabled = false,
  text = "Refresh",
  className = "",
}: RefreshButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${className}`}
    >
      <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
      {isLoading ? "Refreshing..." : text}
    </button>
  );
}

interface DataStateWrapperProps {
  isLoading: boolean;
  error: unknown;
  data: any;
  onRetry?: () => void;
  loadingText?: string;
  errorTitle?: string;
  emptyStateText?: string;
  children: React.ReactNode;
  className?: string;
}

export function DataStateWrapper({
  isLoading,
  error,
  data,
  onRetry,
  loadingText = "Loading...",
  errorTitle = "Error",
  emptyStateText = "No data available",
  children,
  className = "",
}: DataStateWrapperProps) {
  if (isLoading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <LoadingSpinner text={loadingText} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorDisplay
        error={error}
        onRetry={onRetry}
        context={errorTitle}
        className={className}
      />
    );
  }

  if (!data || (Array.isArray(data) && data.length === 0)) {
    return (
      <div className={`text-center py-12 text-gray-500 ${className}`}>
        {emptyStateText}
      </div>
    );
  }

  return <>{children}</>;
}
