import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Shield,
  FileCheck,
  Download,
  FileText,
  Copy,
  Check,
  AlertTriangle,
  Layers,
  Sliders,
  UserCheck,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';

import { api } from '../services/api';
import type { ExaminationDetail, IntegrityCheckResult, DetectorResult } from '../types/examination';
import { IndicatorBadge, ReviewBadge } from '../components/StatusBadge';

export const ExaminationResults: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [exam, setExam] = useState<ExaminationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Integrity Check State
  const [checkingIntegrity, setCheckingIntegrity] = useState<boolean>(false);
  const [integrityResult, setIntegrityResult] = useState<IntegrityCheckResult | null>(null);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  // Visual Laboratory Controls
  const [activeVisTab, setActiveVisTab] = useState<'side_by_side' | 'noise' | 'fft' | 'copymove' | 'ai_synthetic' | 'typography' | 'blend' | 'channels' | 'composite'>('side_by_side');
  const [blendOpacity, setBlendOpacity] = useState<number>(60);

  // Human Review Form State
  const [reviewerName, setReviewerName] = useState<string>('');
  const [reviewerDesignation, setReviewerDesignation] = useState<string>('');
  const [reviewerOrganization, setReviewerOrganization] = useState<string>('SCSS Forensic Laboratory');
  const [reviewDecision, setReviewDecision] = useState<string>('reviewed_no_indicators');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [reviewAttestation, setReviewAttestation] = useState<boolean>(false);
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);
  const [reviewSuccessMsg, setReviewSuccessMsg] = useState<string | null>(null);

  // Collapsible Sections
  const [metadataOpen, setMetadataOpen] = useState<boolean>(false);
  const [auditLogOpen, setAuditLogOpen] = useState<boolean>(false);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getExamination(id);
      setExam(data);
      if (data.human_review) {
        setReviewerName(data.human_review.reviewer_name || '');
        setReviewerDesignation(data.human_review.reviewer_designation || '');
        setReviewerOrganization(data.human_review.reviewer_organization || 'SCSS Forensic Laboratory');
        setReviewDecision(data.human_review.status !== 'pending' ? data.human_review.status : 'reviewed_no_indicators');
        setReviewNotes(data.human_review.notes || '');
        setReviewAttestation(data.human_review.attestation || false);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve examination record');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleCopyHash = () => {
    if (!exam) return;
    navigator.clipboard.writeText(exam.file_integrity.digest);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleRunIntegrityCheck = async () => {
    if (!id) return;
    setCheckingIntegrity(true);
    try {
      const res = await api.checkIntegrity(id);
      setIntegrityResult(res);
      // Reload examination data to update activity event log
      const updated = await api.getExamination(id);
      setExam(updated);
    } catch (err: any) {
      alert(err.message || 'Integrity check failed');
    } finally {
      setCheckingIntegrity(false);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !exam) return;

    if (!reviewAttestation) {
      alert('Examiner attestation checkbox must be confirmed.');
      return;
    }

    setSubmittingReview(true);
    setReviewSuccessMsg(null);
    try {
      const updated = await api.submitReview(id, {
        reviewer_name: reviewerName,
        reviewer_designation: reviewerDesignation,
        reviewer_organization: reviewerOrganization,
        decision: reviewDecision,
        notes: reviewNotes,
        attestation: reviewAttestation,
      });
      setExam(updated);
      setReviewSuccessMsg('Forensic review record attested and recorded successfully.');
      setTimeout(() => setReviewSuccessMsg(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to record human review');
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-[#0F1E36] border-t-[#C5A059] rounded-full animate-spin mx-auto" />
        <p className="text-xs text-slate-500 font-mono">Loading examination record {id}...</p>
      </div>
    );
  }

  if (error || !exam) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
          {error || 'Examination record could not be found.'}
        </div>
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-semibold text-[#0F1E36] hover:underline"
        >
          Return to Dashboard
        </Link>
      </div>
    );
  }

  // Channel Analytics data for Recharts
  const channelData = exam.artifacts?.channel_analytics
    ? [
        {
          name: 'Red Channel',
          Mean: exam.artifacts.channel_analytics.red?.mean ?? 0,
          StdDev: exam.artifacts.channel_analytics.red?.std ?? 0,
        },
        {
          name: 'Green Channel',
          Mean: exam.artifacts.channel_analytics.green?.mean ?? 0,
          StdDev: exam.artifacts.channel_analytics.green?.std ?? 0,
        },
        {
          name: 'Blue Channel',
          Mean: exam.artifacts.channel_analytics.blue?.mean ?? 0,
          StdDev: exam.artifacts.channel_analytics.blue?.std ?? 0,
        },
      ]
    : [];

  const originalImgUrl = api.getImageUrl(exam.examination_id);
  const elaArtifact = exam.artifacts?.ela_heatmap;
  const elaImgUrl = elaArtifact ? api.getVisualizationUrl(exam.examination_id, 'ela_heatmap') : null;
  const noiseArtifact = exam.artifacts?.noise_residual_map;
  const noiseImgUrl = noiseArtifact ? api.getVisualizationUrl(exam.examination_id, 'noise_residual_map') : null;
  const fftArtifact = exam.artifacts?.fft_spectrum;
  const fftImgUrl = fftArtifact ? api.getVisualizationUrl(exam.examination_id, 'fft_spectrum') : null;
  const copymoveArtifact = exam.artifacts?.copymove_map;
  const copymoveImgUrl = copymoveArtifact ? api.getVisualizationUrl(exam.examination_id, 'copymove_map') : null;
  const aiArtifact = exam.artifacts?.ai_synthetic_map;
  const aiImgUrl = aiArtifact ? api.getVisualizationUrl(exam.examination_id, 'ai_synthetic_map') : null;
  const typoArtifact = exam.artifacts?.typography_map;
  const typoImgUrl = typoArtifact ? api.getVisualizationUrl(exam.examination_id, 'typography_map') : null;
  const compositeHeatmapArtifact = exam.artifacts?.composite_evidence_map;
  const compositeHeatmapUrl = compositeHeatmapArtifact
    ? api.getVisualizationUrl(exam.examination_id, 'composite_evidence_map')
    : null;

  // v2 decision fields
  const decisionAssessment = exam.decision_assessment ?? null;
  const evidenceStrength = exam.evidence_strength ?? null;
  const decisionConfidence = exam.decision_confidence ?? null;
  const detectorResults: DetectorResult[] = exam.detector_results ?? [];
  const imageClass = exam.image_characterization?.image_class ?? null;

  return (
    <div className="space-y-6">
      {/* 1. Examination Header & Overview */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <div className="flex items-center space-x-2 text-xs text-slate-500 font-mono mb-1">
              <span>Case ID:</span>
              <strong className="text-slate-800 text-sm">{exam.examination_id}</strong>
              <span>•</span>
              <span>Pipeline: v{exam.analysis_pipeline_version}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>{exam.original_filename}</span>
            </h1>
          </div>

          {/* Action Buttons: Reports & Inspection */}
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={api.getReportPdfUrl(exam.examination_id)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 bg-[#0F1E36] hover:bg-[#162a4d] text-white text-xs font-medium px-3.5 py-2 rounded-lg shadow-xs transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>Download PDF Report</span>
            </a>
            <a
              href={api.getReportJsonUrl(exam.examination_id)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium px-3.5 py-2 rounded-lg border border-slate-200 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>JSON Data</span>
            </a>
          </div>
        </div>

        {/* 2. Evidence File Information Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 text-xs">
          <div>
            <span className="text-slate-400 block">File Size & Media Type</span>
            <span className="font-semibold text-slate-800">
              {(exam.file_size_bytes / 1024).toFixed(1)} KB • {exam.detected_media_type}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block">Pixel Geometry & Color</span>
            <span className="font-semibold text-slate-800">
              {exam.image_width} × {exam.image_height} px ({exam.color_mode})
            </span>
          </div>
          <div>
            <span className="text-slate-400 block">Ingestion Timestamp</span>
            <span className="font-semibold text-slate-800">
              {new Date(exam.upload_timestamp).toLocaleString('en-US', { timeZone: 'UTC', hour12: false })} UTC
            </span>
          </div>
          <div>
            <span className="text-slate-400 block">Human Review Status</span>
            <div className="mt-0.5">
              <ReviewBadge status={exam.human_review_status} size="sm" />
            </div>
          </div>
        </div>
      </div>

      {/* 2. v2 Decision Assessment Panel */}
      {decisionAssessment && (
        <div className={`rounded-xl border-2 shadow-xs p-5 ${
          decisionAssessment === 'LIKELY_TAMPERED' || decisionAssessment === 'MANIPULATION_INDICATORS_DETECTED' || decisionAssessment === 'PROVENANCE_CONFLICT'
            ? 'bg-rose-50 border-rose-300'
            : decisionAssessment === 'LIKELY_AUTHENTIC' || decisionAssessment === 'PROVENANCE_VERIFIED' || decisionAssessment === 'NO_MANIPULATION_INDICATORS_DETECTED'
            ? 'bg-emerald-50 border-emerald-300'
            : 'bg-amber-50 border-amber-300'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            {/* Left: Decision + Strength */}
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-lg ${
                decisionAssessment === 'LIKELY_TAMPERED' ? 'bg-rose-100' :
                decisionAssessment === 'LIKELY_AUTHENTIC' ? 'bg-emerald-100' : 'bg-amber-100'
              }`}>
                {decisionAssessment === 'LIKELY_TAMPERED' ? (
                  <AlertTriangle className="w-6 h-6 text-rose-600" />
                ) : decisionAssessment === 'LIKELY_AUTHENTIC' ? (
                  <Shield className="w-6 h-6 text-emerald-600" />
                ) : (
                  <Info className="w-6 h-6 text-amber-600" />
                )}
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-0.5">
                  SATYA v2 — Multi-Evidence Decision Engine
                </div>
                <div className={`text-lg font-bold tracking-tight ${
                  decisionAssessment === 'LIKELY_TAMPERED' ? 'text-rose-700' :
                  decisionAssessment === 'LIKELY_AUTHENTIC' ? 'text-emerald-700' : 'text-amber-700'
                }`}>
                  {(decisionAssessment === 'LIKELY_TAMPERED' || decisionAssessment === 'MANIPULATION_INDICATORS_DETECTED') && 'MANIPULATION INDICATORS DETECTED'}
                  {decisionAssessment === 'LIKELY_AUTHENTIC' && 'LEGACY: LIKELY AUTHENTIC'}
                  {decisionAssessment === 'PROVENANCE_VERIFIED' && 'PROVENANCE VERIFIED — Scope and claims require examiner review'}
                  {decisionAssessment === 'PROVENANCE_CONFLICT' && 'PROVENANCE CONFLICT — Requires Expert Review'}
                  {decisionAssessment === 'NO_MANIPULATION_INDICATORS_DETECTED' && 'NO MANIPULATION INDICATORS DETECTED — Not proof of authenticity'}
                  {decisionAssessment === 'AI_GENERATION_INDICATORS_DETECTED' && 'AI-GENERATION INDICATORS DETECTED — Heuristic screening only'}
                  {decisionAssessment === 'INSUFFICIENT_EVIDENCE' && 'INSUFFICIENT EVIDENCE — Detector coverage is limited'}
                  {decisionAssessment === 'UNSUPPORTED_FORMAT' && 'UNSUPPORTED FORMAT'}
                  {decisionAssessment === 'ERROR' && 'ANALYSIS ERROR'}
                  {decisionAssessment === 'INCONCLUSIVE' && 'INCONCLUSIVE — Requires Expert Review'}
                </div>
              </div>
            </div>

            {/* Right: Strength + Confidence + Image Class chips */}
            <div className="flex flex-wrap items-center gap-2">
              {evidenceStrength && (
                <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full border ${
                  evidenceStrength === 'STRONG' ? 'bg-rose-100 text-rose-700 border-rose-200' :
                  evidenceStrength === 'MODERATE' ? 'bg-amber-100 text-amber-700 border-amber-200' :
                  evidenceStrength === 'WEAK' ? 'bg-slate-100 text-slate-600 border-slate-200' :
                  'bg-emerald-100 text-emerald-700 border-emerald-200'
                }`}>
                  {evidenceStrength} EVIDENCE
                </span>
              )}
              {decisionConfidence !== null && decisionConfidence !== undefined && (
                <span className="inline-flex items-center text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-white border border-slate-200 text-slate-700">
                  {decisionConfidence.toFixed(0)}% confidence
                </span>
              )}
              {imageClass && (
                <span className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full bg-[#0F1E36]/10 text-[#0F1E36] border border-[#0F1E36]/20">
                  {imageClass}
                </span>
              )}
            </div>
          </div>

          {/* Composite Heatmap (if generated) */}
          {compositeHeatmapUrl && (
            <div className="mt-4 border-t border-current/10 pt-4 space-y-2">
              <div className="text-xs font-semibold text-slate-700">
                Composite Forensic Evidence Heatmap — Exhibit A (Multi-Detector Fusion)
              </div>
              <div className="max-h-48 bg-slate-950 rounded-lg border border-slate-300 flex items-center justify-center overflow-hidden">
                <img
                  src={compositeHeatmapUrl}
                  alt="Composite Evidence Heatmap"
                  className="max-h-full max-w-full object-contain"
                />
              </div>
              <p className="text-[11px] text-slate-500">
                Weighted superposition of spatial anomaly regions from all positive-firing detectors.
                Brighter regions indicate convergence of multiple independent evidence families.
              </p>
            </div>
          )}

          {/* Detector Results Table */}
          {detectorResults.length > 0 && (
            <div className="mt-4 border-t border-current/10 pt-4">
              <div className="text-xs font-semibold text-slate-700 mb-2">
                Normalized Detector Status ({detectorResults.length} detectors)
              </div>
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50 text-[11px] text-slate-500 uppercase font-semibold">
                    <tr>
                      <th className="px-3 py-2 text-left">Detector</th>
                      <th className="px-3 py-2 text-left">Family</th>
                      <th className="px-3 py-2 text-left">Status</th>
                      <th className="px-3 py-2 text-left">Strength</th>
                      <th className="px-3 py-2 text-left w-1/3">Technical Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {detectorResults.map((dr) => (
                      <tr key={dr.detector_name} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono text-slate-800 text-[11px]">
                          {dr.detector_name.replace(/_/g, ' ')}
                        </td>
                        <td className="px-3 py-2 text-slate-500 text-[11px]">
                          {dr.evidence_family}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            dr.status === 'POSITIVE'
                              ? 'bg-rose-100 text-rose-700'
                              : dr.status === 'NEGATIVE'
                              ? 'bg-emerald-100 text-emerald-700'
                              : dr.status === 'NOT_APPLICABLE'
                              ? 'bg-slate-100 text-slate-400'
                              : dr.status === 'ERROR'
                              ? 'bg-orange-100 text-orange-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}>
                            {dr.status}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className={`text-[10px] font-semibold ${
                            dr.evidence_strength === 'STRONG' ? 'text-rose-600' :
                            dr.evidence_strength === 'MODERATE' ? 'text-amber-600' :
                            dr.evidence_strength === 'WEAK' ? 'text-slate-500' :
                            'text-slate-400'
                          }`}>
                            {dr.evidence_strength}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-slate-600 text-[11px] leading-snug">
                          {dr.technical_reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Statutory Disclaimer Alert */}
      <div className="bg-amber-50/70 border-l-4 border-[#C5A059] p-3.5 rounded-r-lg text-xs text-amber-900 leading-relaxed flex items-start gap-2.5">
        <Info className="w-4 h-4 text-[#C5A059] shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold">Preliminary Automated Screening:</strong> Automated indicators do not
          constitute legal proof or definitive determination of authenticity. Findings require manual corroboration by a
          qualified examiner.
        </div>
      </div>

      {/* 3. Cryptographic SHA-256 Evidence Integrity Record Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-[#0F1E36]" />
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Evidence Bitstream Integrity (SHA-256)
            </h2>
          </div>
          <button
            onClick={handleRunIntegrityCheck}
            disabled={checkingIntegrity}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#0F1E36] hover:text-[#C5A059] bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-md border border-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checkingIntegrity ? 'animate-spin' : ''}`} />
            <span>{checkingIntegrity ? 'Recomputing Digest...' : 'Verify Vault Bitstream'}</span>
          </button>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="font-mono text-xs text-slate-700 break-all select-all">
            <span className="text-slate-400 select-none mr-2">SHA-256:</span>
            <strong>{exam.file_integrity.digest}</strong>
          </div>
          <button
            onClick={handleCopyHash}
            className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-300 px-2.5 py-1 rounded shadow-2xs shrink-0"
            title="Copy SHA-256 hash"
          >
            {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedHash ? 'Copied' : 'Copy Hash'}</span>
          </button>
        </div>

        {integrityResult && (
          <div
            className={`p-3 rounded-lg text-xs border flex items-start gap-2 ${
              integrityResult.match
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            {integrityResult.match ? (
              <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div className="leading-relaxed">
              <strong>{integrityResult.status}:</strong> {integrityResult.message}
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                Recomputed at {new Date(integrityResult.checked_at).toLocaleTimeString()} UTC • Recomputed: {integrityResult.recomputed_digest}
              </div>
            </div>
          </div>
        )}

        <p className="text-[11px] text-slate-500 leading-normal">
          Cryptographic hashes establish a tamper-evident reference to detect bit-level alteration in storage.
          A matching hash confirms that stored bytes remain identical to upload, but does not prove the original scene was genuine.
        </p>
      </div>

      {/* 4. Visual Laboratory & Examination Workspace */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-[#0F1E36]" />
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Visual Laboratory Inspection
            </h2>
          </div>

          {/* View Mode Selector */}
          <div className="flex flex-wrap items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs font-medium">
            <button
              onClick={() => setActiveVisTab('side_by_side')}
              className={`px-3 py-1 rounded transition-colors ${
                activeVisTab === 'side_by_side' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Side-by-Side Exhibits
            </button>
            {noiseImgUrl && (
              <button
                onClick={() => setActiveVisTab('noise')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'noise' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Noise Heatmap
              </button>
            )}
            {fftImgUrl && (
              <button
                onClick={() => setActiveVisTab('fft')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'fft' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2D Fourier Spectrum
              </button>
            )}
            {copymoveImgUrl && (
              <button
                onClick={() => setActiveVisTab('copymove')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'copymove' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Copy-Move Clones
              </button>
            )}
            {aiImgUrl && (
              <button
                onClick={() => setActiveVisTab('ai_synthetic')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'ai_synthetic' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                AI Generative Traces
              </button>
            )}
            {typoImgUrl && (
              <button
                onClick={() => setActiveVisTab('typography')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'typography' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Document Typography
              </button>
            )}
            {elaImgUrl && (
              <button
                onClick={() => setActiveVisTab('blend')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'blend' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                ELA Blend Overlay
              </button>
            )}
            {compositeHeatmapUrl && (
              <button
                onClick={() => setActiveVisTab('composite')}
                className={`px-3 py-1 rounded transition-colors ${
                  activeVisTab === 'composite' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Composite Heatmap
              </button>
            )}
            <button
              onClick={() => setActiveVisTab('channels')}
              className={`px-3 py-1 rounded transition-colors ${
                activeVisTab === 'channels' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Color Balance Metrics
            </button>
          </div>
        </div>

        {/* View 1: Side by Side Exhibits */}
        {activeVisTab === 'side_by_side' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span>Exhibit A: Original Evidence Bitstream</span>
                <span className="text-slate-400 font-mono">RGB Source</span>
              </div>
              <div className="aspect-4/3 bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2">
                <img
                  src={originalImgUrl}
                  alt="Original Evidence"
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span>
                  {elaImgUrl
                    ? 'Exhibit B: Error Level Analysis (ELA) Heatmap'
                    : noiseImgUrl
                    ? 'Exhibit B: Noise Inconsistency & Residual Heatmap'
                    : 'Exhibit B: Derived Analysis Artifact'}
                </span>
                <span className="text-slate-400 font-mono">
                  {elaImgUrl ? 'Q=90 Amplified' : noiseImgUrl ? 'High-Pass Median Filter' : 'Not Available'}
                </span>
              </div>
              <div className="aspect-4/3 bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2">
                {elaImgUrl ? (
                  <img
                    src={elaImgUrl}
                    alt="ELA Heatmap"
                    className="max-h-full max-w-full object-contain"
                  />
                ) : noiseImgUrl ? (
                  <img
                    src={noiseImgUrl}
                    alt="Noise Residual Heatmap"
                    className="max-h-full max-w-full object-contain"
                  />
                ) : (
                  <div className="text-center p-6 text-slate-400 text-xs">
                    <p className="font-semibold text-slate-300 mb-1">Visual exhibit not available</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* View 2: Noise Residual Heatmap */}
        {activeVisTab === 'noise' && noiseImgUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Multi-Scale Noise Residual & Local Variance Map</span>
              <span className="text-slate-400 font-mono">Inferno Colormap (Hot = Anomalous Noise)</span>
            </div>
            <div className="aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2 mx-auto">
              <img
                src={noiseImgUrl}
                alt="Noise Inconsistency Heatmap"
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              High-pass median noise residual mapped to local 16x16 macroblock variances. Color intensity reflects spatial noise variance discrepancies.
            </p>
          </div>
        )}

        {/* View 3: 2D Fourier Spectral Analysis */}
        {activeVisTab === 'fft' && fftImgUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>2D Fast Fourier Transform (FFT) Magnitude Spectrum</span>
              <span className="text-slate-400 font-mono">Viridis Colormap (Center = DC, Radial = Nyquist)</span>
            </div>
            <div className="aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2 mx-auto">
              <img
                src={fftImgUrl}
                alt="2D FFT Spectrum"
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              Computes 2D Fourier energy distribution. Periodic grid lattices or sharp high-frequency spikes indicate periodic resampling, interpolation, or AI generative artifacts.
            </p>
          </div>
        )}

        {/* View 4: Copy-Move Forgery Clones */}
        {activeVisTab === 'copymove' && copymoveImgUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Copy-Move Forgery Keypoint Matching Vectors</span>
              <span className="text-slate-400 font-mono">ORB Keypoints & Spatial Displacement Vectors</span>
            </div>
            <div className="aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2 mx-auto">
              <img
                src={copymoveImgUrl}
                alt="Copy-Move Detection"
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              Lines connect spatially-separated regions with matching feature descriptors. Coherent parallel vectors reveal duplicated or cloned content.
            </p>
          </div>
        )}

        {/* View 5: AI Generative Classifier */}
        {activeVisTab === 'ai_synthetic' && aiImgUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>AI Generative Classifier Probability Heatmap</span>
              <span className="text-slate-400 font-mono">
                Likelihood: {exam.artifacts?.ai_synthetic_analytics?.synthetic_likelihood_pct ?? 'N/A'}% (Spectral Decay & Residuals)
              </span>
            </div>
            <div className="aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2 mx-auto">
              <img
                src={aiImgUrl}
                alt="AI Generative Heatmap"
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              Evaluates 2D Fourier radial spectral power decay and cross-channel noise co-occurrence to identify latent diffusion (Midjourney, DALL-E) and GAN traces.
            </p>
          </div>
        )}

        {/* View 6: Document Typography & Alignment */}
        {activeVisTab === 'typography' && typoImgUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Document Typography & Character Alignment Map</span>
              <span className="text-slate-400 font-mono">
                {exam.artifacts?.typography_analytics?.anomalous_glyphs_count ?? 0} Displaced Glyphs (Green = Aligned, Red = Anomaly)
              </span>
            </div>
            <div className="aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2 mx-auto">
              <img
                src={typoImgUrl}
                alt="Document Typography Map"
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              Isolates character glyph baselines and edge gradients across text lines. Highlights spliced characters, altered dates, or pasted table numbers.
            </p>
          </div>
        )}

        {/* View 5: Blend Opacity Slider */}
        {activeVisTab === 'blend' && elaImgUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
              <div className="flex items-center space-x-2 text-slate-700 font-medium">
                <Sliders className="w-4 h-4 text-[#C5A059]" />
                <span>ELA Heatmap Blend Opacity:</span>
                <span className="font-mono font-bold text-slate-900">{blendOpacity}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={blendOpacity}
                onChange={(e) => setBlendOpacity(Number(e.target.value))}
                className="w-48 sm:w-64 accent-[#0F1E36]"
              />
            </div>

            <div className="relative aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center mx-auto">
              <img
                src={originalImgUrl}
                alt="Original"
                className="max-h-full max-w-full object-contain"
              />
              <img
                src={elaImgUrl}
                alt="ELA Overlay"
                style={{ opacity: blendOpacity / 100 }}
                className="absolute inset-0 m-auto max-h-full max-w-full object-contain pointer-events-none mix-blend-screen"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              Drag slider to correlate bright compression residual boundaries directly over physical objects in the image.
            </p>
          </div>
        )}

        {/* View C: Composite Multi-Detector Heatmap */}
        {activeVisTab === 'composite' && compositeHeatmapUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Composite Forensic Evidence Map (Multi-Detector Fusion)</span>
              <span className="text-slate-400 font-mono">Weighted Spatial Anomaly Superposition</span>
            </div>
            <div className="aspect-video max-h-[500px] bg-slate-950 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center p-2 mx-auto">
              <img
                src={compositeHeatmapUrl}
                alt="Composite Evidence Heatmap"
                className="max-h-full max-w-full object-contain"
              />
            </div>
            <p className="text-center text-[11px] text-slate-500">
              Weighted superposition of spatial anomaly contributions from all positive-firing detectors.
              Brighter regions reflect convergence of multiple independent evidence families at the same spatial location,
              substantially increasing confidence of localised manipulation.
            </p>
          </div>
        )}

        {/* View 6: Color Channel Analytics (Recharts) */}
        {activeVisTab === 'channels' && (
          <div className="space-y-4">
            <div className="h-64 w-full bg-slate-50 p-4 rounded-lg border border-slate-200">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channelData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#CBD5E1" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} />
                  <YAxis domain={[0, 255]} tick={{ fontSize: 11, fill: '#475569' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0F1E36', color: '#fff', borderRadius: '6px', fontSize: '11px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="Mean" fill="#0F1E36" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="StdDev" fill="#C5A059" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-slate-500 text-center">
              Evaluates color channel saturation and dynamic range distribution across 8-bit RGB channels.
            </p>
          </div>
        )}
      </div>

      {/* 5. Screening Tests & Individual Results */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
          <FileCheck className="w-5 h-5 text-[#0F1E36]" />
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Automated Screening Tests & Technical Findings
            </h2>
            <p className="text-xs text-slate-500">
              Methodological results executed under analysis pipeline v{exam.analysis_pipeline_version}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {exam.tests.map((test, index) => (
            <div
              key={test.method}
              className="border border-slate-200 rounded-lg p-4 bg-slate-50/50 space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-2">
                <div>
                  <span className="text-xs font-semibold text-slate-900">
                    Test {index + 1}: {test.method.replace(/_/g, ' ').toUpperCase()}
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono ml-2">v{test.version}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <IndicatorBadge indicator={test.indicator} label={test.indicator_label} />
                  <span className="text-[11px] text-slate-400 font-mono">{test.execution_time_ms} ms</span>
                </div>
              </div>

              {/* Technical Explanation */}
              <div className="text-xs text-slate-700 leading-relaxed bg-white p-3 rounded border border-slate-200/60">
                <strong className="text-slate-900 block mb-1">Technical Finding:</strong>
                {test.explanation}
              </div>

              {/* Observations Checklist */}
              {test.observations.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Observations Recorded:
                  </span>
                  <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
                    {test.observations.map((obs, oIdx) => (
                      <li key={oIdx}>{obs}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Method Limitations */}
              {test.limitations.length > 0 && (
                <div className="text-[11px] text-slate-500 bg-slate-100/80 p-2.5 rounded border border-slate-200/80 space-y-0.5">
                  <span className="font-semibold text-slate-600 block">Method Limitations:</span>
                  <ul className="list-disc list-inside space-y-0.5">
                    {test.limitations.map((lim, lIdx) => (
                      <li key={lIdx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 6. Extracted Metadata Drawer (Collapsible) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <button
          onClick={() => setMetadataOpen(!metadataOpen)}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-[#0F1E36]" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                Extracted EXIF & Image Header Metadata
              </h2>
              <p className="text-xs text-slate-500">
                {Object.keys(exam.extracted_metadata).length} tags extracted • Treated as untrusted & potentially editable
              </p>
            </div>
          </div>
          {metadataOpen ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </button>

        {metadataOpen && (
          <div className="px-6 pb-6 pt-2 border-t border-slate-200 space-y-3">
            {Object.keys(exam.extracted_metadata).length === 0 ? (
              <p className="text-xs text-slate-500 italic p-4 text-center">
                No EXIF tags found in image header. Metadata was stripped or absent at ingestion.
              </p>
            ) : (
              <div className="max-h-72 overflow-y-auto border border-slate-200 rounded-lg">
                <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                  <thead className="bg-slate-50 text-slate-600 font-semibold sticky top-0">
                    <tr>
                      <th className="px-4 py-2 w-1/3">Tag Name</th>
                      <th className="px-4 py-2">Parsed Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {Object.entries(exam.extracted_metadata).map(([tag, val]) => (
                      <tr key={tag} className="hover:bg-slate-50">
                        <td className="px-4 py-2 text-slate-700 font-medium">{tag}</td>
                        <td className="px-4 py-2 text-slate-600 break-all">{String(val)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-[11px] text-slate-500">
              Note: Exact GPS coordinates are redacted in automated overviews for privacy. Metadata absence or modification is not conclusive proof of tampering.
            </p>
          </div>
        )}
      </div>

      {/* 7. Suggested Manual Forensic Review Steps & Methodological Limitations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-3">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>Recommended Manual Checks</span>
          </h2>
          <ul className="text-xs text-slate-600 space-y-2 list-disc list-inside leading-relaxed">
            {exam.suggested_manual_checks.map((check, idx) => (
              <li key={idx}>{check}</li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-3">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Methodological Limitations</span>
          </h2>
          <ul className="text-xs text-slate-600 space-y-2 list-disc list-inside leading-relaxed">
            {exam.known_limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* 8. Qualified Human Forensic Review Certification */}
      <div className="bg-white rounded-xl border-2 border-[#C5A059]/40 shadow-xs p-6 space-y-4">
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
          <UserCheck className="w-5 h-5 text-[#0F1E36]" />
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Layer 4: Qualified Human Forensic Review & Attestation
            </h2>
            <p className="text-xs text-slate-500">
              The tool screens. The certified expert decides.
            </p>
          </div>
        </div>

        {reviewSuccessMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>{reviewSuccessMsg}</span>
          </div>
        )}

        <form onSubmit={handleReviewSubmit} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Examiner Full Name *</label>
              <input
                type="text"
                required
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                placeholder="e.g., Dr. A. Dixit"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#C5A059] focus:border-[#C5A059]"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Professional Designation *</label>
              <input
                type="text"
                required
                value={reviewerDesignation}
                onChange={(e) => setReviewerDesignation(e.target.value)}
                placeholder="e.g., Senior Digital Forensics Examiner"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#C5A059] focus:border-[#C5A059]"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Organization</label>
              <input
                type="text"
                value={reviewerOrganization}
                onChange={(e) => setReviewerOrganization(e.target.value)}
                placeholder="e.g., Sure Clue Scientific Solutions"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#C5A059] focus:border-[#C5A059]"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-700 font-semibold mb-1">Forensic Decision & Opinion *</label>
            <select
              value={reviewDecision}
              onChange={(e) => setReviewDecision(e.target.value)}
              className="w-full sm:w-80 px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#C5A059] focus:border-[#C5A059] font-medium"
            >
              <option value="reviewed_no_indicators">Reviewed — No Tampering Indicators Found</option>
              <option value="requires_further_examination">Requires Further Examination (Lab Hardware Review)</option>
              <option value="reviewed_manipulation_suspected">Reviewed — Image Manipulation Suspected</option>
              <option value="reviewed_inconclusive">Reviewed — Inconclusive Evidence</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-700 font-semibold mb-1">Examiner Qualitative Notes & Findings *</label>
            <textarea
              required
              rows={3}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Record detailed observations regarding lighting direction, edge sharpness, EXIF provenance, and manual optical verifications..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#C5A059] focus:border-[#C5A059]"
            />
          </div>

          {/* Attestation Checkbox */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
            <label className="flex items-start space-x-2.5 cursor-pointer">
              <input
                type="checkbox"
                required
                checked={reviewAttestation}
                onChange={(e) => setReviewAttestation(e.target.checked)}
                className="mt-0.5 h-4 w-4 text-[#0F1E36] focus:ring-[#C5A059] border-slate-300 rounded"
              />
              <span className="text-[11px] text-slate-700 leading-relaxed select-none">
                <strong className="text-slate-900">Examiner Attestation:</strong> I attest that I have reviewed the
                automated technical screening results, inspected the derived exhibits, and conducted appropriate manual
                evaluations. This record represents my independent professional opinion and will be embedded in the official
                traceable forensic report.
              </span>
            </label>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="text-[11px] text-slate-400">
              {exam.human_review.timestamp && (
                <span>
                  Last attested: {new Date(exam.human_review.timestamp).toLocaleString('en-US', { timeZone: 'UTC', hour12: false })} UTC
                </span>
              )}
            </div>
            <button
              type="submit"
              disabled={submittingReview || !reviewAttestation}
              className={`inline-flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-semibold shadow-xs transition-colors ${
                submittingReview || !reviewAttestation
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-[#0F1E36] hover:bg-[#162a4d] text-white'
              }`}
            >
              <UserCheck className="w-4 h-4 text-[#C5A059]" />
              <span>{submittingReview ? 'Recording Attestation...' : 'Attest & Update Review'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* 9. Evidence Activity Audit Trail (Collapsible) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <button
          onClick={() => setAuditLogOpen(!auditLogOpen)}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Clock className="w-5 h-5 text-[#0F1E36]" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                Evidentiary Activity Log
              </h2>
              <p className="text-xs text-slate-500">
                {exam.activity_events.length} chronological audit events recorded for Case {exam.examination_id}
              </p>
            </div>
          </div>
          {auditLogOpen ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </button>

        {auditLogOpen && (
          <div className="px-6 pb-6 pt-2 border-t border-slate-200 space-y-2">
            <div className="space-y-2">
              {exam.activity_events.map((ev) => (
                <div
                  key={ev.id}
                  className="flex items-start justify-between bg-slate-50 p-2.5 rounded border border-slate-200 text-xs font-mono"
                >
                  <div className="space-y-0.5">
                    <span className="font-semibold text-slate-800">{ev.event_type}</span>
                    <div className="text-[11px] text-slate-500">
                      {JSON.stringify(ev.details)}
                    </div>
                  </div>
                  <span className="text-slate-400 text-[11px] shrink-0 ml-4">
                    {new Date(ev.timestamp).toLocaleTimeString()} UTC
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Standard local database activity log for preliminary prototype screening. A full production institutional deployment requires dedicated hardware HSM access controls.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
