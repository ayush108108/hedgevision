import { useRef, useCallback } from "react";

/**
 * Custom hook for throttling function calls
 * Ensures a function is not called more than once per specified delay
 *
 * @param callback - Function to throttle
 * @param delay - Minimum delay between calls in milliseconds (default: 300ms)
 * @returns Throttled function
 *
 * @example
 * const throttledResize = useThrottle(() => {
 *   console.log('Window resized');
 * }, 500);
 */
export function useThrottle<T extends (...args: any[]) => any>(
  callback: T,
  delay: number = 300,
): (...args: Parameters<T>) => void {
  const lastRan = useRef<number>(Date.now());
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  return useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now();

      if (now - lastRan.current >= delay) {
        // Execute immediately if enough time has passed
        callback(...args);
        lastRan.current = now;
      } else {
        // Schedule for later
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        timeoutRef.current = setTimeout(
          () => {
            callback(...args);
            lastRan.current = Date.now();
          },
          delay - (now - lastRan.current),
        );
      }
    },
    [callback, delay],
  );
}
