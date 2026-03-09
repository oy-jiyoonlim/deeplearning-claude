# Frontend Changes: Theme Toggle Button

## Summary
Added a dark/light theme toggle button with sun/moon icons, positioned in the top-right corner.

## Files Changed

### `frontend/index.html`
- Added theme toggle `<button>` with sun and moon SVG icons before the main container
- `aria-label` and `title` attributes for accessibility
- Bumped CSS/JS cache versions

### `frontend/style.css`
- Added `[data-theme="light"]` CSS variables for the light theme
- Added `.theme-toggle` button styles (fixed position, top-right, circular, z-index: 1000)
- Added `.theme-icon` transition animations (opacity + rotation for icon swap)
- Added transition rules on major elements for smooth theme switching (0.3s ease)
- Replaced hardcoded `rgba(0,0,0,0.2)` code block backgrounds with `var(--code-bg)` variable

### `frontend/script.js`
- `initTheme()`: restores saved theme from `localStorage` on page load
- `toggleTheme()`: toggles `data-theme` attribute on `<html>` and persists to `localStorage`
- Registered click event listener on the toggle button

## Design Details
- **Position**: Fixed, top-right (1rem from edges)
- **Size**: 44x44px circular button
- **Animation**: 0.3s ease rotation + opacity transition between sun/moon icons
- **Persistence**: Theme preference saved in `localStorage`
- **Accessibility**: Keyboard-navigable, focus ring, aria-label, title attribute
