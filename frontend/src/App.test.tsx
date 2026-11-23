import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';

afterEach(() => cleanup());

describe('LeakLens workspace', () => {
  it('opens directly into the dashboard without an authentication screen', () => {
    render(<App />);
    expect(screen.getByText('Northstar Studio')).toBeInTheDocument();
    expect(screen.getByText(/See the bigger/i)).toBeInTheDocument();
    expect(screen.getByText(/Connecting|Local API connected|API offline/i)).toBeInTheDocument();
  });

  it('navigates to transaction management and exposes search', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /^Transactions$/ }));
    expect(screen.getByPlaceholderText(/Search transactions/i)).toBeInTheDocument();
    expect(screen.getByText(/LEDGER MANAGEMENT/)).toBeInTheDocument();
  });
});
