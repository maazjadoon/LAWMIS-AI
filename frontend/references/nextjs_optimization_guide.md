# Next.js & React Performance Optimization Guide

Technical guide for optimization strategies in modern React and Next.js applications.

## Asset Optimization

### 1. Image Optimization
- Always use `next/image` in Next.js, or proper `srcset` and responsive sizes in Vite React.
- Preload critical above-the-fold images (`priority` attribute).
- Use modern formats like WebP or AVIF.

### 2. Fonts
- Use self-hosted web fonts or Google Fonts with `font-display: swap`.
- Preload woff2 files.

---

## Code Splitting & Dynamic Imports

### 1. Lazy Loading Components
Use `React.lazy` (Vite) or `next/dynamic` (Next.js) for large, conditionally-rendered components (e.g. Modals, Charts):

```tsx
import React, { Suspense } from 'react';

const LargeChartComponent = React.lazy(() => import('./LargeChart'));

export const Dashboard = () => {
  return (
    <div>
      <Suspense fallback={<div>Loading chart...</div>}>
        <LargeChartComponent />
      </Suspense>
    </div>
  );
};
```

---

## Render Optimizations

- **`useMemo`**: Cache expensive computations.
- **`useCallback`**: Cache function instances passed to optimized child components.
- **Virtualization**: Use `react-window` or `react-virtualized` for lists exceeding 500 rows.
- **Bundle Analysis**: Regularly analyze chunk sizes to prevent large libraries (like `lodash` or `moment`) from bloat.
