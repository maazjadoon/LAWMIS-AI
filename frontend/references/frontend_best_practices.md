# Frontend Technical Best Practices

Core development standards and guidelines for senior engineers.

## Technology Stack

- **Framework**: React / Vite (TypeScript)
- **State**: React Hooks (useState, useEffect) + Custom Stores (Zustand)
- **API Fetching**: Native Fetch API / Axios / React Query
- **Styling**: Vanilla CSS (Variables, Flexbox, Grid, CSS Modules)

---

## Security Guidelines

### 1. XSS Prevention
- Never use `dangerouslySetInnerHTML` unless parsing sanitized content.
- Escape all dynamic user input.

### 2. Authentication & API Safety
- Keep API tokens out of local storage if sensitive (use HttpOnly cookies).
- Use dynamic configuration from `.env` for all API endpoints.

---

## Quality Checklist

- [ ] Strict TypeScript configuration (`noImplicitAny: true`, `strict: true`).
- [ ] Responsive design verified (Mobile, Tablet, Desktop).
- [ ] Lighthouse accessibility score &gt; 90.
- [ ] No unhandled React console errors or warnings in production console.
