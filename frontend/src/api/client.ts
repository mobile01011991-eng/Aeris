import type { AMRResultPayload, OrganismOption, ToolReport } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

export interface JobStep {
  id: string;
  label: string;
  status: "pending" | "running" | "done" | "failed" | "skipped";
  detail: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export type OrganismDecision =
  | "accept_system"
  | "keep_user"
  | "cancel"
  | "auto_match";

export interface SpeciesReport {
  identification?: Record<string, unknown>;
  match?: {
    match_status?: string;
    declared_name?: string | null;
    detected_name?: string | null;
    confidence?: number | null;
    reason?: string;
    amrfinder_organism?: string | null;
  };
}

export interface AnalysisJob {
  job_id: string;
  sample_id: string;
  status:
    | "queued"
    | "running"
    | "awaiting_organism_confirmation"
    | "completed"
    | "failed"
    | "cancelled";
  mode: string;
  error?: string | null;
  steps: JobStep[];
  /** Filled in per tool as it finishes, so a report opens before the run ends. */
  tool_reports?: Record<string, ToolReport>;
  result?: AMRResultPayload | null;
  declared_organism?: string | null;
  detected_organism?: string | null;
  confirmed_organism?: string | null;
  organism_decision?: OrganismDecision | null;
  species_report?: SpeciesReport | null;
}

async function parseError(res: Response): Promise<never> {
  let detail: unknown = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail ?? body;
  } catch {
    /* ignore */
  }
  throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
}

export async function fetchOrganisms(): Promise<{
  confidence_threshold: number;
  organisms: OrganismOption[];
}> {
  const res = await fetch(`${BASE}/api/v1/amr/organisms`);
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function startDemoJob(
  sampleId = "sampleA",
  declaredOrganism = "klebsiella_pneumoniae",
): Promise<AnalysisJob> {
  const params = new URLSearchParams({
    sample_id: sampleId,
    declared_organism: declaredOrganism,
  });
  const res = await fetch(`${BASE}/api/v1/amr/demo/async?${params}`, {
    method: "POST",
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function startAnalyzeJob(
  file: File,
  options: {
    sampleId?: string;
    tools?: string[];
    declaredOrganism: string;
  },
): Promise<AnalysisJob> {
  const params = new URLSearchParams();
  if (options.sampleId) params.set("sample_id", options.sampleId);
  if (options.tools?.length) params.set("tools", options.tools.join(","));
  params.set("declared_organism", options.declaredOrganism);

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE}/api/v1/amr/analyze/async?${params}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function confirmJob(
  jobId: string,
  decision: "accept_system" | "keep_user" | "cancel",
): Promise<AnalysisJob> {
  const res = await fetch(
    `${BASE}/api/v1/amr/jobs/${encodeURIComponent(jobId)}/confirm`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    },
  );
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function fetchJob(jobId: string): Promise<AnalysisJob> {
  const res = await fetch(`${BASE}/api/v1/amr/jobs/${encodeURIComponent(jobId)}`);
  if (!res.ok) await parseError(res);
  return res.json();
}

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export function isTerminalJob(job: AnalysisJob): boolean {
  return TERMINAL_STATUSES.has(job.status);
}

function speciesGateSettled(job: AnalysisJob): boolean {
  const species = job.steps.find((s) => s.id === "species_id");
  return species != null && (species.status === "done" || species.status === "skipped");
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Resolve once the species gate is settled and tool work has started.
 *
 * Tools run one by one, so the user should reach the report hub and watch
 * reports appear rather than wait for the whole job to finish.
 */
export async function pollJobUntilToolsStart(
  jobId: string,
  onUpdate: (job: AnalysisJob) => void,
  intervalMs = 700,
  options?: {
    /** Called when job pauses for organism confirmation; should confirm/cancel then resolve. */
    onAwaitingConfirmation?: (job: AnalysisJob) => Promise<void>;
  },
): Promise<AnalysisJob> {
  for (;;) {
    const job = await fetchJob(jobId);
    onUpdate(job);

    if (job.status === "awaiting_organism_confirmation") {
      if (options?.onAwaitingConfirmation) {
        await options.onAwaitingConfirmation(job);
        continue;
      }
      await sleep(intervalMs);
      continue;
    }

    if (isTerminalJob(job) || (job.status === "running" && speciesGateSettled(job))) {
      return job;
    }
    await sleep(intervalMs);
  }
}

export async function fetchResult(sampleId: string): Promise<AMRResultPayload> {
  const res = await fetch(
    `${BASE}/api/v1/amr/results/${encodeURIComponent(sampleId)}`,
  );
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function listResults() {
  const res = await fetch(`${BASE}/api/v1/amr/results`);
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export function sampleFastaUrl(): string {
  return `${BASE}/api/v1/amr/sample-fasta`;
}
