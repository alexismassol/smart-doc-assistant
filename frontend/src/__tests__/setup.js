/**
 * setup.js — Test setup for Vitest + React Testing Library
 * Uses: @testing-library/jest-dom (custom matchers), jsdom (browser-like environment)
 */
import '@testing-library/jest-dom'

// jsdom ne supporte pas scrollIntoView — on le mock globalement
window.HTMLElement.prototype.scrollIntoView = vi.fn()
