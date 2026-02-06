import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import FilterPanel from '../FilterPanel';

const mockExtractions = [
  { id: '1', class: 'character', text: 'John' },
  { id: '2', class: 'character', text: 'Jane' },
  { id: '3', class: 'location', text: 'Office' },
  { id: '4', class: 'props', text: 'Laptop' },
  { id: '5', class: 'props', text: 'Phone' }
];

describe('FilterPanel', () => {
  const mockOnToggleFilter = vi.fn();
  const mockOnSearchChange = vi.fn();
  const mockOnClearFilters = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders filter panel with search input', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set()}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    expect(screen.getByPlaceholderText(/search extractions/i)).toBeInTheDocument();
    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('displays correct class counts', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set()}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    expect(screen.getByText('2')).toBeInTheDocument(); // character count
    expect(screen.getByText('1')).toBeInTheDocument(); // location count
  });

  it('calls onToggleFilter when filter is clicked', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set()}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    const characterFilter = screen.getByText('Characters').closest('button');
    fireEvent.click(characterFilter);

    expect(mockOnToggleFilter).toHaveBeenCalledWith('character');
  });

  it('calls onSearchChange when search input changes', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set()}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    const searchInput = screen.getByPlaceholderText(/search extractions/i);
    fireEvent.change(searchInput, { target: { value: 'John' } });

    expect(mockOnSearchChange).toHaveBeenCalledWith('John');
  });

  it('shows clear filters button when filters are active', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set(['character'])}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    const clearButton = screen.getByText('Clear');
    expect(clearButton).toBeInTheDocument();

    fireEvent.click(clearButton);
    expect(mockOnClearFilters).toHaveBeenCalled();
  });

  it('shows active filters summary', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set(['character', 'location'])}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    expect(screen.getByText('2 filters active')).toBeInTheDocument();
  });

  it('applies active styling to selected filters', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set(['character'])}
        searchQuery=""
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    const characterFilter = screen.getByText('Characters').closest('button');
    expect(characterFilter).toHaveClass('active');
  });

  it('shows clear search button when search query exists', () => {
    render(
      <FilterPanel
        extractions={mockExtractions}
        activeFilters={new Set()}
        searchQuery="test"
        onToggleFilter={mockOnToggleFilter}
        onSearchChange={mockOnSearchChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    const clearSearchButton = screen.getByLabelText('Clear search');
    expect(clearSearchButton).toBeInTheDocument();

    fireEvent.click(clearSearchButton);
    expect(mockOnSearchChange).toHaveBeenCalledWith('');
  });
});
