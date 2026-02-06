/**
 * Export extractions to JSON file
 */
export const exportToJSON = (data, filename = 'extractions') => {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}_${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Copy extraction text to clipboard
 */
export const copyToClipboard = async (extractions) => {
  try {
    const text = extractions
      .map(ext => `[${ext.class.toUpperCase()}] ${ext.text}`)
      .join('\n\n');
    
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Failed to copy to clipboard:', err);
    return false;
  }
};

/**
 * Generate statistics summary from extractions
 */
export const generateStatsSummary = (extractions) => {
  const classCounts = extractions.reduce((acc, ext) => {
    acc[ext.class] = (acc[ext.class] || 0) + 1;
    return acc;
  }, {});

  const confidenceScores = extractions.map(ext => ext.confidence || 0);
  const avgConfidence = confidenceScores.length > 0
    ? confidenceScores.reduce((sum, conf) => sum + conf, 0) / confidenceScores.length
    : 0;

  const minConfidence = confidenceScores.length > 0 ? Math.min(...confidenceScores) : 0;
  const maxConfidence = confidenceScores.length > 0 ? Math.max(...confidenceScores) : 0;

  return {
    summary: {
      total_extractions: extractions.length,
      unique_classes: Object.keys(classCounts).length,
      average_confidence: avgConfidence,
      min_confidence: minConfidence,
      max_confidence: maxConfidence
    },
    class_breakdown: classCounts,
    top_classes: Object.entries(classCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([className, count]) => ({ class: className, count })),
    confidence_distribution: {
      high: confidenceScores.filter(c => c >= 0.8).length,
      medium: confidenceScores.filter(c => c >= 0.6 && c < 0.8).length,
      low: confidenceScores.filter(c => c < 0.6).length
    },
    generated_at: new Date().toISOString()
  };
};

/**
 * Format extraction data for export
 */
export const formatExtractionsForExport = (extractions) => {
  return extractions.map(ext => ({
    id: ext.id,
    class: ext.class,
    text: ext.text,
    confidence: ext.confidence,
    scene_id: ext.scene_id,
    text_start: ext.text_start,
    text_end: ext.text_end,
    attributes: ext.attributes || {},
    created_at: ext.created_at
  }));
};
