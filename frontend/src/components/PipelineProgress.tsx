import type { JobStep } from "../api/client";
import { useI18n } from "../i18n/I18nContext";
import type { TranslationKey } from "../i18n/translations";

const STATUS_KEYS: Record<JobStep["status"], TranslationKey> = {
  pending: "step.status.pending",
  running: "step.status.running",
  done: "step.status.done",
  failed: "step.status.failed",
  skipped: "step.status.skipped",
};

const TOOL_KEYS = new Set([
  "resfinder",
  "rgi",
  "amrfinderplus",
  "abricate",
  "deeparg",
]);

const AI_TOOL_KEYS = new Set(["deeparg"]);

/** Short tool names for the compact stage cards. */
const TOOL_SHORT_LABEL: Record<string, string> = {
  resfinder: "ResFinder",
  rgi: "RGI",
  amrfinderplus: "AMRFinderPlus",
  abricate: "ABRicate",
  deeparg: "DeepARG",
};

/** Step ids are stable; server labels are not translated. */
const STEP_LABEL_KEYS: Record<string, TranslationKey> = {
  ingest: "pipeline.step.ingest",
  species_id: "pipeline.step.species",
  consensus: "pipeline.step.aggregate",
  persist: "pipeline.step.save",
};

type Translate = (key: TranslationKey, vars?: Record<string, string | number>) => string;

function stepLabel(step: JobStep, t: Translate): string {
  if (isToolStep(step)) {
    const key = toolKeyOf(step);
    return TOOL_SHORT_LABEL[key] ?? key;
  }
  const labelKey = STEP_LABEL_KEYS[step.id];
  return labelKey ? t(labelKey) : step.label;
}

function toolKeyOf(step: JobStep): string {
  return step.id.replace(/^tool:/, "");
}

function isToolStep(step: JobStep): boolean {
  if (step.id.startsWith("tool:")) return true;
  return TOOL_KEYS.has(toolKeyOf(step));
}

function isAiStep(step: JobStep): boolean {
  return isToolStep(step) && AI_TOOL_KEYS.has(toolKeyOf(step));
}

type Stage = {
  id: "input" | "tools" | "ai" | "output";
  steps: { step: JobStep; index: number }[];
};

const STAGE_TITLE_KEYS: Record<Stage["id"], TranslationKey> = {
  input: "pipeline.stage.input",
  tools: "pipeline.stage.tools",
  ai: "pipeline.stage.ai",
  output: "pipeline.stage.output",
};

function groupStages(steps: JobStep[]): Stage[] {
  const input: Stage = { id: "input", steps: [] };
  const tools: Stage = { id: "tools", steps: [] };
  const ai: Stage = { id: "ai", steps: [] };
  const output: Stage = { id: "output", steps: [] };

  steps.forEach((step, index) => {
    const item = { step, index };
    if (isAiStep(step)) {
      ai.steps.push(item);
    } else if (isToolStep(step)) {
      tools.steps.push(item);
    } else if (
      step.id === "ingest" ||
      step.id === "species_id" ||
      tools.steps.length === 0
    ) {
      input.steps.push(item);
    } else {
      output.steps.push(item);
    }
  });

  return [input, tools, ai, output].filter((s) => s.steps.length > 0);
}

function stageStatus(stage: Stage): JobStep["status"] {
  const statuses = stage.steps.map((s) => s.step.status);
  if (statuses.some((s) => s === "failed")) return "failed";
  if (statuses.some((s) => s === "running")) return "running";
  if (statuses.every((s) => s === "done" || s === "skipped")) return "done";
  if (statuses.some((s) => s === "done" || s === "skipped")) return "running";
  return "pending";
}

function StepOrb({
  step,
  index,
  compact = false,
}: {
  step: JobStep;
  index: number;
  compact?: boolean;
}) {
  return (
    <div className={`flow-orb ${compact ? "compact" : ""}`} aria-hidden="true">
      {step.status === "running" && (
        <>
          <span className="orb-ring" />
          <span className="orb-ring delay" />
        </>
      )}
      {step.status === "done" && <span className="orb-burst" />}
      <span className="orb-core">
        {step.status === "done" ? (
          <svg viewBox="0 0 24 24" className="orb-icon check">
            <path
              d="M5 13l4 4L19 7"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : step.status === "failed" ? (
          <span className="orb-bang">!</span>
        ) : step.status === "running" ? (
          <span className="orb-dot" />
        ) : (
          <span className="orb-index">{index + 1}</span>
        )}
      </span>
    </div>
  );
}

function VerticalStep({
  step,
  index,
  showLink,
  linkOn,
  linkPulse,
}: {
  step: JobStep;
  index: number;
  showLink: boolean;
  linkOn: boolean;
  linkPulse: boolean;
}) {
  const { t } = useI18n();

  return (
    <li className={`flow-node ${step.status}`}>
      <div className="flow-col">
        <StepOrb step={step} index={index} />
        {showLink && (
          <div
            className={`flow-link ${linkOn ? "on" : ""} ${linkPulse ? "pulse" : ""}`}
            aria-hidden="true"
          >
            <span className="flow-link-fill" />
            {linkPulse && <span className="flow-spark" />}
          </div>
        )}
      </div>
      <div className="flow-copy">
        <div className="flow-copy-top">
          <strong>{stepLabel(step, t)}</strong>
          <span className={`flow-chip ${step.status}`}>
            {t(STATUS_KEYS[step.status])}
          </span>
        </div>
        <p className="flow-detail">
          {step.detail ||
            (step.status === "pending"
              ? t("pipeline.detail.queued")
              : step.status === "running"
                ? t("pipeline.detail.inProgress")
                : "")}
        </p>
      </div>
    </li>
  );
}

export function PipelineProgress({
  steps,
  jobStatus,
}: {
  steps: JobStep[];
  jobStatus: string;
}) {
  const { t } = useI18n();
  const done = steps.filter((s) => s.status === "done" || s.status === "skipped").length;
  const total = steps.length || 1;
  const pct = Math.round((done / total) * 100);
  const active = steps.find((s) => s.status === "running");
  const stages = groupStages(steps);

  return (
    <div className="pipeline-panel" aria-live="polite">
      <div className="pipeline-head">
        <div>
          <h2 className="pipeline-title">{t("pipeline.title")}</h2>
          <p className="muted">
            {jobStatus === "completed"
              ? t("pipeline.state.complete")
              : jobStatus === "failed" || jobStatus === "cancelled"
                ? t("pipeline.state.stopped")
                : jobStatus === "awaiting_organism_confirmation"
                  ? t("pipeline.state.awaiting")
                  : active
                    ? t("pipeline.state.working", {
                        step: stepLabel(active, t),
                      })
                    : t("pipeline.state.idle")}
          </p>
        </div>
        <div className="pipeline-pct" data-complete={jobStatus === "completed"}>
          {pct}%
        </div>
      </div>

      <div className="flow-stages">
        {stages.map((stage, stageIdx) => {
          const nextStage = stages[stageIdx + 1];
          const st = stageStatus(stage);
          const bridgeOn =
            st === "done" ||
            (nextStage != null &&
              nextStage.steps.some(
                (s) => s.step.status === "running" || s.step.status === "done",
              ));
          const bridgePulse =
            st === "done" &&
            nextStage?.steps.some((s) => s.step.status === "running");

          return (
            <section
              key={stage.id}
              className={`flow-stage flow-stage-${stage.id} ${st}`}
            >
              <div className="flow-stage-label">
                <span>{t(STAGE_TITLE_KEYS[stage.id])}</span>
              </div>

              {stage.id === "tools" || stage.id === "ai" ? (
                <ul className="flow-tools-row">
                  {stage.steps.map(({ step, index }, i) => {
                    const next = stage.steps[i + 1]?.step;
                    const hOn =
                      step.status === "done" || step.status === "skipped";
                    const hPulse =
                      step.status === "done" && next?.status === "running";
                    return (
                      <li key={step.id} className={`flow-tool ${step.status}`}>
                        <StepOrb step={step} index={index} compact />
                        <strong>{stepLabel(step, t)}</strong>
                        <span className={`flow-chip ${step.status}`}>
                          {t(STATUS_KEYS[step.status])}
                        </span>
                        <p className="flow-detail">
                          {step.detail ||
                            (step.status === "pending"
                              ? t("pipeline.detail.queued")
                              : "")}
                        </p>
                        {i < stage.steps.length - 1 && (
                          <div
                            className={`flow-h-link ${hOn ? "on" : ""} ${hPulse ? "pulse" : ""}`}
                            aria-hidden="true"
                          >
                            <span className="flow-h-link-fill" />
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <ol className="flow-rail">
                  {stage.steps.map(({ step, index }, i) => {
                    const next = stage.steps[i + 1]?.step;
                    return (
                      <VerticalStep
                        key={step.id}
                        step={step}
                        index={index}
                        showLink={i < stage.steps.length - 1}
                        linkOn={
                          step.status === "done" || step.status === "skipped"
                        }
                        linkPulse={
                          step.status === "done" && next?.status === "running"
                        }
                      />
                    );
                  })}
                </ol>
              )}

              {nextStage && (
                <div
                  className={`flow-stage-bridge ${bridgeOn ? "on" : ""} ${bridgePulse ? "pulse" : ""}`}
                  aria-hidden="true"
                >
                  <span className="flow-stage-bridge-fill" />
                  {bridgePulse && <span className="flow-spark" />}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
