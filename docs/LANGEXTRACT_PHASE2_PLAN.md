# LangExtract Phase 2 Integration Plan

**Status:** Draft - Pending POC Results  
**Created:** [Date]  
**Last Updated:** [Date]

---

## Prerequisites

### POC Success Criteria (Must Pass)
- ✅ Extraction accuracy >= 90% on key elements
- ✅ Source grounding demonstrates clear value
- ✅ Interactive visualization is production-ready
- ✅ Cost analysis shows acceptable ROI
- ✅ No critical technical blockers identified

**POC Result:** [PASS / CONDITIONAL PASS / FAIL]

---

## Phase 2 Objectives

1. **Integrate LangExtract** as parallel extraction system alongside current OpenAI approach
2. **Implement source grounding** in database and UI
3. **Deploy interactive visualization** as new feature
4. **Migrate existing scripts** to new extraction format (optional)
5. **Measure production performance** and iterate

---

## Architecture Design

### Dual-System Approach (Recommended)

```
┌─────────────────────────────────────────────┐
│           Script Upload                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│     PDF Text Extraction (Existing)          │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  LangExtract │    │   Baseline   │
│  (New Path)  │    │ (Existing)   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       ▼                   ▼
┌──────────────────────────────────┐
│   Unified Storage Layer          │
│   (Extended Schema)               │
└──────────────────────────────────┘
```

**Benefits:**
- Zero risk to existing functionality
- A/B testing capability
- Gradual migration path
- Fallback option if issues arise

---

## Database Schema Changes

### New Tables

#### 1. `extraction_metadata`
```sql
CREATE TABLE extraction_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    scene_id UUID REFERENCES scenes(id) ON DELETE CASCADE,
    extraction_class TEXT NOT NULL,
    extraction_text TEXT NOT NULL,
    text_start INTEGER NOT NULL,
    text_end INTEGER NOT NULL,
    attributes JSONB DEFAULT '{}',
    confidence FLOAT,
    extraction_method TEXT, -- 'langextract' or 'baseline'
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_script_extractions (script_id),
    INDEX idx_scene_extractions (scene_id),
    INDEX idx_extraction_class (extraction_class)
);
```

#### 2. `extraction_visualizations`
```sql
CREATE TABLE extraction_visualizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    html_content TEXT NOT NULL,
    jsonl_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    
    INDEX idx_script_viz (script_id)
);
```

### Extended Columns

#### `scenes` table
```sql
ALTER TABLE scenes 
ADD COLUMN text_start INTEGER,
ADD COLUMN text_end INTEGER,
ADD COLUMN extraction_confidence FLOAT,
ADD COLUMN extraction_method TEXT DEFAULT 'baseline';
```

#### `scripts` table
```sql
ALTER TABLE scripts
ADD COLUMN extraction_method TEXT DEFAULT 'baseline',
ADD COLUMN langextract_version TEXT,
ADD COLUMN has_visualization BOOLEAN DEFAULT FALSE;
```

---

## Backend Implementation

### Phase 2.1: Core Service (Week 1-2)

#### Files to Create
1. **`backend/services/langextract_service.py`**
   - `extract_with_langextract()` - Main extraction function
   - `save_extractions()` - Save to database
   - `generate_visualization()` - Create HTML viz
   - `get_extraction_stats()` - Analytics

2. **`backend/routes/langextract_routes.py`**
   - `POST /api/scripts/:id/extract/langextract` - Trigger extraction
   - `GET /api/scripts/:id/extractions` - Get extractions
   - `GET /api/scripts/:id/visualization` - Get HTML viz
   - `GET /api/scripts/:id/extraction-stats` - Get stats

#### Integration Points
- Hook into existing `script_routes.py` upload flow
- Add feature flag: `ENABLE_LANGEXTRACT=true`
- Implement async job queue for long extractions

### Phase 2.2: Migration Utilities (Week 2)

#### Files to Create
1. **`backend/scripts/migrate_to_langextract.py`**
   - Batch re-extract existing scripts
   - Preserve baseline data
   - Progress tracking
   - Rollback capability

2. **`backend/scripts/compare_extractions.py`**
   - Compare LangExtract vs Baseline
   - Generate diff reports
   - Identify discrepancies

---

## Frontend Implementation

### Phase 2.3: UI Components (Week 3-4)

#### New Components

1. **`InteractiveScriptViewer.jsx`**
   - Embed LangExtract HTML visualization
   - Click-to-highlight functionality
   - Filter by extraction class
   - Export options

2. **`ExtractionSourceView.jsx`**
   - Show original text with highlights
   - Display extraction attributes
   - Edit/correct extractions
   - Confidence indicators

3. **`ExtractionComparison.jsx`** (Admin only)
   - Side-by-side LangExtract vs Baseline
   - Accuracy metrics
   - A/B test results

#### Modified Components

1. **`SceneDetail.jsx`**
   - Add "View Source" button
   - Show extraction confidence
   - Link to interactive viewer

2. **`ScriptUpload.jsx`**
   - Add extraction method selector
   - Show LangExtract progress
   - Preview visualization

3. **`Dashboard.jsx`**
   - Add extraction method stats
   - Show visualization availability

### Phase 2.4: Routes (Week 4)

```javascript
// New routes
/scripts/:scriptId/interactive-viewer
/scripts/:scriptId/extractions
/scripts/:scriptId/source-view/:extractionId
```

---

## API Endpoints

### New Endpoints

```typescript
// Extraction
POST   /api/scripts/:id/extract/langextract
GET    /api/scripts/:id/extractions
GET    /api/scripts/:id/extractions/:extractionId
PATCH  /api/scripts/:id/extractions/:extractionId
DELETE /api/scripts/:id/extractions/:extractionId

// Visualization
GET    /api/scripts/:id/visualization
POST   /api/scripts/:id/visualization/regenerate

// Analytics
GET    /api/scripts/:id/extraction-stats
GET    /api/admin/extraction-comparison
```

---

## Deployment Strategy

### Week 1-2: Backend Foundation
- [ ] Database migrations
- [ ] LangExtract service implementation
- [ ] API endpoints
- [ ] Unit tests
- [ ] Feature flag setup

### Week 3-4: Frontend Integration
- [ ] UI components
- [ ] Route setup
- [ ] Integration tests
- [ ] E2E tests

### Week 5: Beta Testing
- [ ] Deploy to staging
- [ ] Internal testing
- [ ] Fix critical bugs
- [ ] Performance optimization

### Week 6: Production Rollout
- [ ] Deploy to production (feature flag OFF)
- [ ] Enable for beta users (10%)
- [ ] Monitor metrics
- [ ] Gradual rollout (25% → 50% → 100%)

---

## Testing Strategy

### Unit Tests
- [ ] LangExtract service functions
- [ ] Database operations
- [ ] API endpoint handlers
- [ ] Frontend components

### Integration Tests
- [ ] Full extraction pipeline
- [ ] Database persistence
- [ ] API contract tests
- [ ] Visualization generation

### E2E Tests
- [ ] Upload → Extract → View flow
- [ ] Interactive viewer functionality
- [ ] Source grounding accuracy
- [ ] Error handling

### Performance Tests
- [ ] Extraction speed benchmarks
- [ ] Concurrent extraction handling
- [ ] Visualization rendering
- [ ] Database query performance

---

## Monitoring & Metrics

### Key Metrics to Track

#### Performance
- Extraction time per script
- API response times
- Visualization generation time
- Database query performance

#### Quality
- Extraction accuracy (manual review sample)
- User corrections per extraction
- Confidence score distribution
- Source grounding accuracy

#### Adoption
- % scripts using LangExtract
- Interactive viewer usage
- Feature engagement
- User feedback scores

### Alerting Thresholds
- Extraction failure rate > 5%
- Average extraction time > 5 minutes
- API error rate > 1%
- Visualization generation failures > 2%

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Dependency conflicts | High | Medium | Isolate in virtual env, version pinning |
| API rate limits | Medium | Low | Implement rate limiting, batch processing |
| Performance degradation | High | Low | Load testing, caching, async processing |
| Data migration issues | High | Medium | Rollback plan, backup data, gradual migration |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| User confusion | Medium | Medium | Clear UI, tooltips, documentation |
| Accuracy concerns | High | Low | A/B testing, manual review, confidence scores |
| Cost overruns | Medium | Low | Budget alerts, usage caps, cost monitoring |

---

## Rollback Plan

### Immediate Rollback (< 1 hour)
1. Disable feature flag: `ENABLE_LANGEXTRACT=false`
2. Route all traffic to baseline system
3. Monitor for stability
4. Investigate root cause

### Data Rollback (If needed)
1. Restore from backup
2. Re-run baseline extractions
3. Verify data integrity
4. Notify affected users

### Partial Rollback
1. Disable for specific user segments
2. Keep feature for beta testers
3. Fix issues in isolation
4. Gradual re-enable

---

## Success Criteria

### Phase 2 Complete When:
- ✅ LangExtract extraction available for all new uploads
- ✅ Interactive visualization accessible in UI
- ✅ Source grounding functional and accurate
- ✅ Performance meets SLA (< 5 min per script)
- ✅ User satisfaction >= 4/5 stars
- ✅ Zero critical bugs in production
- ✅ Documentation complete

---

## Cost Projection

### Development Costs
- Backend development: [X] hours @ $[X]/hr = $[X]
- Frontend development: [X] hours @ $[X]/hr = $[X]
- Testing & QA: [X] hours @ $[X]/hr = $[X]
- DevOps & deployment: [X] hours @ $[X]/hr = $[X]
- **Total:** $[X]

### Operational Costs (Annual)
- Gemini API: $[X] (based on POC projections)
- Infrastructure: $[X] (storage, compute)
- Monitoring: $[X]
- **Total:** $[X]

### ROI Analysis
- Development investment: $[X]
- Annual savings vs baseline: $[X]
- Payback period: [X] months
- 3-year ROI: [X]%

---

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **2.1: Backend** | 2 weeks | Service, API, DB schema |
| **2.2: Migration** | 1 week | Migration scripts, utilities |
| **2.3: Frontend** | 2 weeks | UI components, routes |
| **2.4: Testing** | 1 week | All test suites passing |
| **2.5: Beta** | 1 week | Staging deployment, fixes |
| **2.6: Production** | 1 week | Gradual rollout |
| **Total** | **8 weeks** | Full production deployment |

---

## Dependencies

### External
- Google Gemini API access
- Supabase database capacity
- Frontend hosting (Vercel/Netlify)

### Internal
- Backend team availability
- Frontend team availability
- QA resources
- DevOps support

### Blockers
- [ ] POC results approval
- [ ] Budget approval
- [ ] Resource allocation
- [ ] Stakeholder sign-off

---

## Next Steps

### If POC Passes
1. Present results to stakeholders
2. Get budget approval
3. Allocate development resources
4. Begin Phase 2.1 (Backend)

### If POC Conditional Pass
1. Address identified issues
2. Run targeted re-tests
3. Update plan based on findings
4. Re-evaluate go/no-go

### If POC Fails
1. Document failure reasons
2. Evaluate alternatives
3. Consider hybrid approach
4. Archive for future consideration

---

**Prepared by:** [Your name]  
**Approved by:** [Stakeholder]  
**Status:** Draft / Approved / In Progress / Complete
