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

// Progress of one script as shown on a production card. scripts.analysis_status
// is not maintained (it stays 'pending' even when fully analysed), so progress
// comes from the per-scene counts the production payload carries. Payloads
// without counts fall back to the script-level status.
export const scriptProgress = (script) => {
  if (script.scene_count === undefined) return scriptStatusInfo(script.analysis_status);
  const { scene_count: total, analyzed_scenes: done = 0, analyzing_scenes = 0, failed_scenes = 0 } = script;
  if (failed_scenes > 0) {
    return { label: `${failed_scenes} scene${failed_scenes === 1 ? '' : 's'} failed`, tone: 'bad' };
  }
  if (analyzing_scenes > 0) return { label: `Analysing ${done}/${total}`, tone: 'info' };
  if (total > 0 && done === total) return { label: 'Analysis complete', tone: 'good' };
  if (done > 0) return { label: `${done}/${total} scenes analysed`, tone: 'warn' };
  return NOT_STARTED;
};

// Scripts the production team should look at: analysing, failed, or partly analysed.
export const scriptsNeedingAttention = (scripts) =>
  scripts.filter((s) => {
    const { tone } = scriptProgress(s);
    return tone === 'info' || tone === 'bad' || tone === 'warn';
  });
