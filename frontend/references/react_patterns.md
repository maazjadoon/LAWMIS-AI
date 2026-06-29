# React Patterns & Practices

Guidelines for building clean, maintainable React components.

## Component Design

### 1. Functional Components
Always use functional components with arrow functions and TypeScript:
```tsx
import React from 'react';

interface ButtonProps {
  label: string;
  onClick: () => void;
}

export const Button: React.FC<ButtonProps> = ({ label, onClick }) => {
  return (
    <button className="btn" onClick={onClick}>
      {label}
    </button>
  );
};
```

### 2. Container vs Presentational Components
Separate logic (fetching, state management) from presentational components (pure UI):
- **Presentational**: Receives props, renders UI, styles, no state dependencies.
- **Container**: Handles queries, mutations, passes data down as props.

---

## State Management

### 1. Local State
Use `useState` for simple local UI state. Keep state as close to where it's needed as possible.

### 2. Global State
Use Zustand for global, lightweight application state:
```ts
import create from 'zustand';

interface ChatStore {
  messages: string[];
  addMessage: (msg: string) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
}));
```

---

## Best Practices

- **Props destructuring**: Always destructure props in the component signature.
- **Keys in loops**: Always provide a unique `key` when rendering lists (never use array index).
- **TypeScript**: Define explicit interfaces for all props and state variables.
- **CSS Modules / Vanilla CSS**: Use isolated class selectors instead of global styles.
