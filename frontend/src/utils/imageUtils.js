/**
 * AgriScan Image Utility
 * Provides resilient fallback placeholders and handlers for crop foliage imagery.
 */

// SVG Data URI for botanical leaf placeholder (100% offline, zero network requests)
export const DEFAULT_CROP_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160' fill='none'%3E%3Crect width='160' height='160' rx='80' fill='%23EDF7EE'/%3E%3Cpath d='M80 36C80 36 48 62 48 94C48 111.673 62.3269 126 80 126C97.6731 126 112 111.673 112 94C112 62 80 36 80 36Z' fill='%232D6A4F'/%3E%3Cpath d='M80 54V126' stroke='%23FAF8F5' stroke-width='4' stroke-linecap='round'/%3E%3Cpath d='M80 80C88 75 96 77 100 80' stroke='%23FAF8F5' stroke-width='3' stroke-linecap='round'/%3E%3Cpath d='M80 96C72 91 64 93 60 96' stroke='%23FAF8F5' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E";

export const handleImageError = (e) => {
  if (e && e.currentTarget) {
    e.currentTarget.onerror = null;
    e.currentTarget.src = DEFAULT_CROP_IMAGE;
  }
};
