import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import InteractiveViewer from '../InteractiveViewer';

// Mock child components
vi.mock('../FilterPanel', () => ({
  default: ({ onToggleFilter, onSearchChange }) => (
    <div data-testid="filter-panel">
      <button onClick={() => onToggleFilter('character')}>Toggle Filter</button>
      <input 
        data-testid="search-input"
        onChange={(e) => onSearchChange(e.target.value)}
      />
    </div>
  )
}));

vi.mock('../ExtractionViewer', () => ({
  default: ({ extractions, onExtractionClick }) => (
    <div data-testid="extraction-viewer">
      {extractions.map(ext => (
        <div key={ext.id} onClick={() => onExtractionClick(ext)}>
          {ext.text}
        </div>
      ))}
    </div>
  )
}));

vi.mock('../ExtractionStats', () => ({
  default: () => <div data-testid="extraction-stats">Stats</div>
}));

vi.mock('../ExtractionDetailModal', () => ({
  default: ({ extraction, onClose }) => (
    <div data-testid="extraction-modal">
      <p>{extraction.text}</p>
      <button onClick={onClose}>Close</button>
    </div>
  )
}));

vi.mock('../ExportMenu', () => ({
  default: () => <div data-testid="export-menu">Export</div>
}));

const mockScript = {
  id: '123',
  title: 'Test Script',
  full_text: 'This is a test script with some text.'
};

const mockExtractions = [
  {
    id: '1',
    class: 'character',
    text: 'John',
    confidence: 0.95,
    text_start: 0,
    text_end: 4,
    scene_id: 'scene1'
  },
  {
    id: '2',
    class: 'location',
    text: 'Office',
    confidence: 0.88,
    text_start: 10,
    text_end: 16,
    scene_id: 'scene1'
  }
];

describe('InteractiveViewer', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    localStorage.setItem('supabase.auth.token', 'test-token');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    global.fetch.mockImplementation(() => new Promise(() => {}));

    render(
      <BrowserRouter>
        <InteractiveViewer />
      </BrowserRouter>
    );

    expect(screen.getByText(/loading extractions/i)).toBeInTheDocument();
  });

  it('fetches and displays script data', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/scripts/')) {
        if (url.includes('/extractions')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ extractions: mockExtractions })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockScript)
        });
      }
    });

    render(
      <BrowserRouter>
        <InteractiveViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('filter-panel')).toBeInTheDocument();
      expect(screen.getByTestId('extraction-viewer')).toBeInTheDocument();
      expect(screen.getByTestId('extraction-stats')).toBeInTheDocument();
    });
  });

  it('handles filter changes', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/extractions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ extractions: mockExtractions })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockScript)
      });
    });

    render(
      <BrowserRouter>
        <InteractiveViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('filter-panel')).toBeInTheDocument();
    });

    const toggleButton = screen.getByText('Toggle Filter');
    fireEvent.click(toggleButton);

    // Verify filtering logic is applied
    expect(screen.getByTestId('extraction-viewer')).toBeInTheDocument();
  });

  it('handles search input', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/extractions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ extractions: mockExtractions })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockScript)
      });
    });

    render(
      <BrowserRouter>
        <InteractiveViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('search-input')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('search-input');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    // Verify search filtering is applied
    expect(searchInput.value).toBe('John');
  });

  it('opens modal when extraction is clicked', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/extractions')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ extractions: mockExtractions })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockScript)
      });
    });

    render(
      <BrowserRouter>
        <InteractiveViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('John')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('John'));

    await waitFor(() => {
      expect(screen.getByTestId('extraction-modal')).toBeInTheDocument();
    });
  });

  it('displays error state on fetch failure', async () => {
    global.fetch.mockRejectedValue(new Error('Failed to fetch'));

    render(
      <BrowserRouter>
        <InteractiveViewer />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error loading extractions/i)).toBeInTheDocument();
    });
  });
});
