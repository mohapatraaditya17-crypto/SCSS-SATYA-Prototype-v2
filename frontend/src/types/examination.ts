type DecisionAssessment =
  | 'MANIPULATION_INDICATORS_DETECTED'
  | 'AI_GENERATION_INDICATORS_DETECTED'
  | 'PROVENANCE_VERIFIED'
  | 'PROVENANCE_CONFLICT'
  | 'NO_MANIPULATION_INDICATORS_DETECTED'
  | 'INCONCLUSIVE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'UNSUPPORTED_FORMAT'
  | 'ERROR'
  // Legacy values remain readable for earlier records.
  | 'LIKELY_AUTHENTIC'
  | 'LIKELY_TAMPERED'
  | null;
export interface FileIntegrityInfo {
  algorithm: string;
  digest: string;
  sha1?: string;
  md5?: string;
  verified?: boolean;
}

export interface ScreeningTestResult {
  method: string;
  version: string;
  status: 'completed' | 'not_applicable' | 'failed';
  indicator: 'indicator_detected' | 'no_indicator_detected' | 'inconclusive' | 'test_unavailable' | 'test_failed';
  indicator_label: string;
  observations: string[];
  explanation: string;
  limitations: string[];
  execution_time_ms: number;
  // v2 normalized fields (optional for backward compat)
  score?: number | null;
  confidence?: number | null;
  evidence_strength?: string | null;
  normalized_status?: 'POSITIVE' | 'NEGATIVE' | 'INCONCLUSIVE' | 'NOT_APPLICABLE' | 'ERROR' | null;
  affected_regions?: Array<{
    x: number; y: number; w: number; h: number;
    confidence: number; label: string;
  }> | null;
}

/** v2 — Normalized per-detector result from the fusion engine */
export interface DetectorResult {
  detector_name: string;
  status: 'POSITIVE' | 'NEGATIVE' | 'INCONCLUSIVE' | 'NOT_APPLICABLE' | 'ERROR';
  score: number | null;
  confidence: number | null;
  evidence_strength: 'STRONG' | 'MODERATE' | 'WEAK' | 'NONE' | 'UNKNOWN';
  evidence_family: string;
  technical_reason: string;
  affected_regions: Array<{
    x: number; y: number; w: number; h: number;
    confidence: number; label: string;
  }>;
  execution_time_ms: number;
  detector_version: string;
}

/** v2 — Image characterization block */
export interface ImageCharacterization {
  format: string;
  mime_type: string;
  dimensions: { width: number; height: number };
  megapixels: number;
  aspect_ratio: number;
  has_camera_exif: boolean;
  camera_make?: string | null;
  camera_model?: string | null;
  software_tag?: string | null;
  image_class: 'PHOTOGRAPH' | 'DOCUMENT' | 'SCREENSHOT' | 'GRAPHIC' | 'AI_CANDIDATE' | 'UNKNOWN';
  applicable_detectors: string[];
  inapplicable_detectors: Record<string, string>;
  characterization_version: string;
}

export interface ActivityEvent {
  id: number;
  event_type: string;
  timestamp: string;
  details: Record<string, any>;
}

export interface HumanReview {
  status: 'pending' | 'requires_further_examination' | 'reviewed_no_indicators' | 'reviewed_manipulation_suspected' | 'reviewed_inconclusive';
  reviewer_name?: string | null;
  reviewer_designation?: string | null;
  reviewer_organization?: string | null;
  notes?: string | null;
  timestamp?: string | null;
  attestation: boolean;
}

export interface ExaminationDetail {
  examination_id: string;
  status: string;
  original_filename: string;
  file_size_bytes: number;
  detected_media_type: string;
  image_width: number;
  image_height: number;
  color_mode: string;
  upload_timestamp: string;
  capture_timestamp?: string | null;
  application_version: string;
  analysis_pipeline_version: string;

  file_integrity: FileIntegrityInfo;
  tests: ScreeningTestResult[];
  overall_assessment: string;
  human_review_status: string;
  human_review: HumanReview;
  extracted_metadata: Record<string, any>;
  known_limitations: string[];
  suggested_manual_checks: string[];
  artifacts: Record<string, any>;
  activity_events: ActivityEvent[];
  report_generated_at?: string | null;
  disclaimer: string;

  // v2 fields
  decision_assessment?: DecisionAssessment;
  evidence_strength?: 'VERY_STRONG' | 'STRONG' | 'MODERATE' | 'LOW' | 'NONE' | 'WEAK' | 'UNKNOWN' | null;
  decision_confidence?: number | null;
  detector_results?: DetectorResult[] | null;
  image_characterization?: ImageCharacterization | null;
}

export interface ExaminationOverview {
  examination_id: string;
  original_filename: string;
  file_size_bytes: number;
  detected_media_type: string;
  sha256_digest: string;
  upload_timestamp: string;
  capture_timestamp?: string | null;
  application_version: string;
  analysis_pipeline_version: string;
  image_width: number;
  image_height: number;
  color_mode: string;
  status: string;
  overall_assessment: string;
  human_review_status: string;
  // v2 fields
  decision_assessment?: 'LIKELY_AUTHENTIC' | 'LIKELY_TAMPERED' | 'INCONCLUSIVE' | null;
  evidence_strength?: 'STRONG' | 'MODERATE' | 'WEAK' | 'NONE' | 'UNKNOWN' | null;
}

export interface DashboardStats {
  total_examinations: number;
  recent_examinations_count: number;
  pending_review_count: number;
  reviewed_count: number;
  requires_further_review_count: number;
  reports_generated_count: number;
  preliminary_notice: string;
}

export interface IntegrityCheckResult {
  examination_id: string;
  stored_digest: string;
  recomputed_digest: string;
  match: boolean;
  algorithm: string;
  checked_at: string;
  status: string;
  message: string;
}
