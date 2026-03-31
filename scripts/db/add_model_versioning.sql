-- HedgeVision model versioning hardening migration
-- Run against your Supabase/Postgres database.

ALTER TABLE IF EXISTS precomputed_analysis
  ADD COLUMN IF NOT EXISTS model_version TEXT NOT NULL DEFAULT 'prod-v1';

ALTER TABLE IF EXISTS correlation_matrix
  ADD COLUMN IF NOT EXISTS model_version TEXT NOT NULL DEFAULT 'prod-v1';

-- Optional indexes for version-scoped reads.
CREATE INDEX IF NOT EXISTS idx_precomputed_analysis_model_version
  ON precomputed_analysis (model_version);

CREATE INDEX IF NOT EXISTS idx_correlation_matrix_model_version
  ON correlation_matrix (model_version);

-- If your uniqueness constraints are version-scoped, create a multi-column unique index.
-- Remove old unique indexes only after validating query compatibility.
CREATE UNIQUE INDEX IF NOT EXISTS uq_correlation_matrix_versioned
  ON correlation_matrix (matrix_date, window_days, calculation_method, model_version);

