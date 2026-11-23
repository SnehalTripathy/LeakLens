import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';

afterEach(() => cleanup());

describe('LeakLens workspace', () => {
  it('opens directly into the dashboard without an authentication screen', () => {
    render(<App />);
    expect(screen.getByText('Northstar Studio')).toBeInTheDocument();
    expect(screen.getByText(/See the bigger/i)).toBeInTheDocument();
  });

  it('navigates to transaction management and exposes search', async () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /^Transactions$/ }));
    expect(await screen.findByPlaceholderText(/Search transactions/i)).toBeInTheDocument();
    expect(screen.getByText(/LEDGER MANAGEMENT/)).toBeInTheDocument();
  });
});


  it('reaches every implemented workspace module from the sidebar', () => {
    render(<App />);
    const routes = [
      'Overview', 'Transactions', 'Revenue intelligence', 'Expense intelligence',
      'Leak detection', 'Anomaly intelligence', 'Forecasting', 'Business health',
      'Recommendations', 'What-if simulator', 'Vendor intelligence',
      'Subscription intelligence', 'Alerts centre', 'AI assistant', 'Reports',
      'Data quality', 'Settings',
    ];
    for (const route of routes) {
      const link = screen.getByRole('button', { name: new RegExp('^' + route + '$') });
      fireEvent.click(link);
      expect(link.className).toContain('selected');
    }
  });
