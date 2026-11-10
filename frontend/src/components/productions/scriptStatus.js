// Maps scripts.analysis_status (backend values) to a display label and tone.
const INFO = {
  complete: { label: 'Analysis complete', tone: 'good' },
  analyzing: { label: 'Analysing', tone: 'info' },
  analysis_queued: { label: 'Analysing', tone: 'info' },
  in_progress: { label: 'Analysing', tone: 'info' },
  partial: { label: 'Partly analysed', tone: 'warn' },
  failed: { label: 'Analysis failed', tone: 'bad' },
  error: { label: 'Analysis failed', tone: 'bad' },
  cancelled: { label: 'Analysis cancelled', tone: 'warn' },
};
const NOT_STARTED = { label: 'Not analysed yet', tone: 'neutral' };

export const scriptStatusInfo = (status) => INFO[status] || NOT_STARTED;

// Scripts the production team should look at: still analysing, failed, or
// only partly analysed. (Cancelled and not-started are labelled, not flagged.)
export const scriptsNeedingAttention = (scripts) =>
  scripts.filter((s) => {
    const tone = scriptStatusInfo(s.analysis_status).tone;
    return tone === 'info' || tone === 'bad' || s.analysis_status === 'partial';
  });
