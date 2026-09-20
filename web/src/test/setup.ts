import '@testing-library/jest-dom/vitest'

// Recharts measures its container; jsdom has no ResizeObserver.
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
