import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import ExtractionViewer from '../ExtractionViewer';

const mockScriptText = 'John walks into the Office. He picks up his Laptop.';

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
    text_start: 19,
    text_end: 25,
    scene_id: 'scene1'
  },
  {
    id: '3',
    class: 'props',
    text: 'Laptop',
    confidence: 0.92,
    text_start: 44,
    text_end: 50,
    scene_id: 'scene1'
  }
];

describe('ExtractionViewer', () => {
  const mockOnExtractionClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders script text', () => {
    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={[]}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    expect(screen.getByText(mockScriptText)).toBeInTheDocument();
  });

  it('highlights extractions in text', () => {
    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={mockExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    const highlights = document.querySelectorAll('.extraction-highlight');
    expect(highlights).toHaveLength(3);
  });

  it('calls onExtractionClick when extraction is clicked', () => {
    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={mockExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    const highlights = document.querySelectorAll('.extraction-highlight');
    fireEvent.click(highlights[0]);

    expect(mockOnExtractionClick).toHaveBeenCalledWith(mockExtractions[0]);
  });

  it('shows tooltip with class and confidence on hover', () => {
    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={mockExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    const highlights = document.querySelectorAll('.extraction-highlight');
    expect(highlights[0]).toHaveAttribute('title', 'character (95% confidence)');
  });

  it('applies correct color to each extraction class', () => {
    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={mockExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    const highlights = document.querySelectorAll('.extraction-highlight');
    
    // Character should have blue color
    expect(highlights[0].style.getPropertyValue('--highlight-color')).toBe('#3b82f6');
    
    // Location should have green color
    expect(highlights[1].style.getPropertyValue('--highlight-color')).toBe('#10b981');
    
    // Props should have cyan color
    expect(highlights[2].style.getPropertyValue('--highlight-color')).toBe('#06b6d4');
  });

  it('shows no extractions message when filtered list is empty', () => {
    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={[]}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    expect(screen.getByText(/no extractions match your current filters/i)).toBeInTheDocument();
  });

  it('handles overlapping extractions correctly', () => {
    const overlappingExtractions = [
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
        class: 'action',
        text: 'John walks',
        confidence: 0.85,
        text_start: 0,
        text_end: 10,
        scene_id: 'scene1'
      }
    ];

    render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={overlappingExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    // Should only render the first extraction (no overlap)
    const highlights = document.querySelectorAll('.extraction-highlight');
    expect(highlights).toHaveLength(1);
  });

  it('memoizes highlighted text computation', () => {
    const { rerender } = render(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={mockExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    const initialHighlights = document.querySelectorAll('.extraction-highlight');

    // Rerender with same props
    rerender(
      <ExtractionViewer
        scriptText={mockScriptText}
        extractions={mockExtractions}
        onExtractionClick={mockOnExtractionClick}
      />
    );

    const afterHighlights = document.querySelectorAll('.extraction-highlight');
    expect(afterHighlights).toHaveLength(initialHighlights.length);
  });
});
