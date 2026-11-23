import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('LeakLens application shell', () => {
  it('opens directly into the demo dashboard without authentication', () => {
    render(<App />);
    expect(screen.getByText('Northstar Studio')).toBeInTheDocument();
    expect(screen.getByText(/See the bigger/i)).toBeInTheDocument();
    expect(screen.getByText('Demo data active')).toBeInTheDocument();
  });
});