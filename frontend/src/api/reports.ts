import type { AnalysisJob, JobStep } from "./client";
import type { TranslationKey } from "../i18n/translations";
import type {
  AMRResultPayload,
  HarmonizedHit,
  ToolKind,
  ToolReport,
} from "./types";

/** Tools that compare the sequence against a resistance-gene database. */
export const DATABASE_TOOL_KEYS = [
  "resfinder",
  "rgi",
  "amrfinderplus",
  "abricate",
] as const;

/** Deep learning screen — kept out of any database-tool agreement count. */
export const AI_TOOL_KEYS = ["deeparg"] as const;

export const ALL_TOOL_KEYS = [...DATABASE_TOOL_KEYS, ...AI_TOOL_KEYS];

export interface ToolMeta {
  /** Tool names are product names and stay untranslated. */
  label: string;
  kind: ToolKind;
  blurbKey: TranslationKey;
}

export const TOOL_META: Record<string, ToolMeta> = {
  resfinder: {
    label: "ResFinder",
    kind: "database",
    blurbKey: "tool.resfinder.blurb",
  },
  rgi: {
    label: "CARD / RGI",
    kind: "database",
    blurbKey: "tool.rgi.blurb",
  },
  amrfinderplus: {
    label: "AMRFinderPlus",
    kind: "database",
    blurbKey: "tool.amrfinderplus.blurb",
  },
  abricate: {
    label: "ABRicate (ARG-ANNOT)",
    kind: "database",
    blurbKey: "tool.abricate.blurb",
  },
  deeparg: {
    label: "DeepARG",
    kind: "ai",
    blurbKey: "tool.deeparg.blurb",
  },
};

export function toolMeta(key: string): ToolMeta {
  return (
    TOOL_META[key] ?? {
      label: key,
      kind: "database",
      blurbKey: "tool.generic.blurb",
    }
  );
}

export type ToolViewStatus = JobStep["status"];

export interface ToolView {
  key: string;
  label: string;
  kind: ToolKind;
  blurbKey: TranslationKey;
  status: ToolViewStatus;
  detail: string;
  report?: ToolReport;
}

function toolKeysFrom(
  job: AnalysisJob | null,
  reports: Record<string, ToolReport>,
): string[] {
  const fromSteps = (job?.steps ?? [])
    .filter((s) => s.id.startsWith("tool:"))
    .map((s) => s.id.slice("tool:".length));
  if (fromSteps.length) return fromSteps;

  const fromReports = Object.keys(reports);
  return fromReports.length ? fromReports : ALL_TOOL_KEYS;
}

/**
 * Merge live job steps with finished tool reports.
 *
 * A card can therefore show "running" for one tool while another is already
 * openable.
 */
export function buildToolViews(
  job: AnalysisJob | null,
  payload: AMRResultPayload | null,
): ToolView[] {
  const reports: Record<string, ToolReport> = {
    ...(payload?.tool_reports ?? {}),
    ...(job?.tool_reports ?? {}),
  };
  const steps = new Map(
    (job?.steps ?? []).map((s) => [s.id, s] as const),
  );

  return toolKeysFrom(job, reports).map((key) => {
    const meta = toolMeta(key);
    const report = reports[key];
    const step = steps.get(`tool:${key}`);

    let status: ToolViewStatus;
    if (step) {
      status = step.status;
    } else if (report) {
      status = report.success ? "done" : "failed";
    } else {
      status = "pending";
    }

    return {
      key,
      label: report?.display_name || meta.label,
      kind: report?.kind ?? meta.kind,
      blurbKey: meta.blurbKey,
      status,
      detail: step?.detail ?? "",
      report,
    };
  });
}

export function findToolView(views: ToolView[], key: string): ToolView | null {
  return views.find((v) => v.key === key) ?? null;
}

export function splitToolViews(views: ToolView[]) {
  return {
    database: views.filter((v) => v.kind !== "ai"),
    ai: views.filter((v) => v.kind === "ai"),
  };
}

/** ARG-ANNOT ships genes as `(Bla)blaKPC-2`; show the bare symbol. */
export function stripGenePrefix(gene?: string | null): string {
  const text = (gene ?? "").trim();
  if (text.startsWith("(") && text.includes(")")) {
    return text.slice(text.indexOf(")") + 1).trim() || text;
  }
  return text;
}

/**
 * Family-level symbol shared by allele callers and DeepARG.
 *
 * `blaKPC-2` and `(Bla)blaKPC-2` both become `KPC`, the level DeepARG predicts.
 */
export function geneFamily(gene?: string | null): string {
  const bare = stripGenePrefix(gene);
  if (!bare) return "";
  const trimmed = bare
    .replace(/^bla/i, "")
    .replace(/[-_]?\d+[A-Za-z]?$/, "")
    .replace(/^[-_]+|[-_]+$/g, "");
  return (trimmed || bare).toUpperCase();
}

export function contigOf(hit: HarmonizedHit): string {
  const raw = String(hit.input_sequence_id ?? "").trim();
  if (!raw) return "—";
  return raw.split(/\s+/)[0] || "—";
}

export function passesFilter(
  hit: HarmonizedHit,
  idMin: number,
  covMin: number,
): boolean {
  if (typeof hit.passed_quality_filter === "boolean") {
    return hit.passed_quality_filter;
  }
  const id = Number(hit.sequence_identity);
  const cov =
    hit.coverage_percentage == null || hit.coverage_percentage === ""
      ? null
      : Number(hit.coverage_percentage);
  if (!Number.isFinite(id) || id < idMin) return false;
  if (cov == null) return true;
  return Number.isFinite(cov) && cov >= covMin;
}

export function pct(value: unknown, digits = 2): string {
  if (value == null || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  return `${Number(n.toFixed(digits))}%`;
}

export function plain(value: unknown): string {
  if (value == null || value === "") return "—";
  return String(value);
}

const REPORT_STATUS_KEYS: Record<ToolViewStatus, TranslationKey> = {
  pending: "report.status.pending",
  running: "report.status.running",
  done: "report.status.done",
  failed: "report.status.failed",
  skipped: "report.status.skipped",
};

export function reportStatusKey(status: ToolViewStatus): TranslationKey {
  return REPORT_STATUS_KEYS[status];
}
