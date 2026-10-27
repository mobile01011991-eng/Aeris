import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  confirmJob,
  fetchOrganisms,
  healthCheck,
  pollJobUntilToolsStart,
  sampleFastaUrl,
  startAnalyzeJob,
  startDemoJob,
  type AnalysisJob,
} from "../api/client";
import type { OrganismOption } from "../api/types";
import { TOOL_OPTIONS } from "../api/types";
import { AI_TOOL_KEYS, DATABASE_TOOL_KEYS } from "../api/reports";
import { useI18n } from "../i18n/I18nContext";
import type { TranslationKey } from "../i18n/translations";
import { PipelineProgress } from "../components/PipelineProgress";
import { BacteriaField } from "../components/BacteriaField";
import { SequenceReader } from "../components/SequenceReader";
import { OrganismConfirmModal } from "../components/OrganismConfirmModal";
import {
  StartBacteriaLaunch,
  rectFromEl,
  type LaunchRect,
} from "../components/StartBacteriaLaunch";

type Mode = "demo" | "upload";

const TOOL_GROUPS: {
  titleKey: TranslationKey;
  hintKey: TranslationKey;
  keys: readonly string[];
}[] = [
  {
    titleKey: "analyze.tools.database.title",
    hintKey: "analyze.tools.database.hint",
    keys: DATABASE_TOOL_KEYS,
  },
  {
    titleKey: "analyze.tools.ai.title",
    hintKey: "analyze.tools.ai.hint",
    keys: AI_TOOL_KEYS,
  },
];

export function AnalyzePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const startBtnRef = useRef<HTMLButtonElement>(null);
  const pipelineRef = useRef<HTMLDivElement>(null);

  const [mode, setMode] = useState<Mode>(params.get("demo") ? "demo" : "upload");
  const [file, setFile] = useState<File | null>(null);
  const [sampleId, setSampleId] = useState("sampleA");
  const [organisms, setOrganisms] = useState<OrganismOption[]>([]);
  const [declaredOrganism, setDeclaredOrganism] = useState("klebsiella_pneumoniae");
  const [selectedTools, setSelectedTools] = useState<string[]>(
    TOOL_OPTIONS.map((t) => t.key),
  );
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [awaitingJob, setAwaitingJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [popTool, setPopTool] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);
  const [pipelinePulse, setPipelinePulse] = useState(false);
  const [pipelineExpand, setPipelineExpand] = useState(false);
  const [revealWorking, setRevealWorking] = useState(false);
  const [launchPath, setLaunchPath] = useState<{
    from: LaunchRect;
    to: LaunchRect;
  } | null>(null);

  useEffect(() => {
    let alive = true;
    healthCheck().then((ok) => {
      if (alive) setApiOk(ok);
    });
    fetchOrganisms()
      .then((data) => {
        if (!alive) return;
        setOrganisms(data.organisms);
        if (
          data.organisms.length &&
          !data.organisms.some((o) => o.id === declaredOrganism)
        ) {
          setDeclaredOrganism(data.organisms[0].id);
        }
      })
      .catch(() => {
        if (alive) setOrganisms([]);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (params.get("demo") === "1") setMode("demo");
  }, [params]);

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      setMode("upload");
      setSampleId(f.name.replace(/\.(fasta|fastq|fa|fq|fna)(\.gz)?$/i, ""));
    }
  }

  function toggleTool(key: string) {
    setSelectedTools((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
    setPopTool(key);
    window.setTimeout(() => {
      setPopTool((cur) => (cur === key ? null : cur));
    }, 320);
  }

  function buildLaunchPath(): { from: LaunchRect; to: LaunchRect } | null {
    const btn = startBtnRef.current;
    const pipe = pipelineRef.current;
    if (!btn || !pipe) return null;
    return { from: rectFromEl(btn), to: rectFromEl(pipe) };
  }

  const confirmWaiter = useRef<{
    resolve: () => void;
    reject: (err: Error) => void;
  } | null>(null);

  async function handleOrganismDecision(
    decision: "accept_system" | "keep_user" | "cancel",
  ) {
    if (!awaitingJob) return;
    setConfirmBusy(true);
    try {
      const updated = await confirmJob(awaitingJob.job_id, decision);
      setJob(updated);
      setAwaitingJob(null);
      if (decision === "cancel") {
        confirmWaiter.current?.reject(
          new Error(updated.error || t("analyze.error.cancelled")),
        );
        confirmWaiter.current = null;
        return;
      }
      confirmWaiter.current?.resolve();
      confirmWaiter.current = null;
    } catch (err) {
      setAwaitingJob(null);
      confirmWaiter.current?.reject(
        err instanceof Error ? err : new Error(String(err)),
      );
      confirmWaiter.current = null;
    } finally {
      setConfirmBusy(false);
    }
  }

  async function submit() {
    setError(null);
    setBusy(true);
    setJob(null);
    setAwaitingJob(null);
    try {
      if (!declaredOrganism) {
        throw new Error(t("analyze.error.selectOrganism"));
      }
      const started =
        mode === "demo"
          ? await startDemoJob(sampleId || "sampleA", declaredOrganism)
          : await startAnalyzeJob(file!, {
              sampleId: sampleId || undefined,
              tools: selectedTools,
              declaredOrganism,
            });
      setJob(started);

      // Hand over to the report hub as soon as the species gate is settled;
      // tools keep running there and each report opens when it is ready.
      const ready = await pollJobUntilToolsStart(started.job_id, setJob, 700, {
        onAwaitingConfirmation: (j) =>
          new Promise<void>((resolve, reject) => {
            setAwaitingJob(j);
            confirmWaiter.current = { resolve, reject };
          }),
      });

      if (ready.status === "failed" || ready.status === "cancelled") {
        throw new Error(ready.error || t("analyze.error.stopped"));
      }

      const target = ready.sample_id || started.sample_id;
      navigate(
        `/results/${encodeURIComponent(target)}?job=${encodeURIComponent(started.job_id)}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
      setRevealWorking(false);
      setPipelineExpand(false);
      setAwaitingJob(null);
      confirmWaiter.current = null;
    }
  }

  const submitRef = useRef(submit);
  submitRef.current = submit;

  const finishLaunch = useCallback(() => {
    setLaunchPath(null);
    setLaunching(false);
    setPipelineExpand(false);
    setRevealWorking(true);
    void submitRef.current();
  }, []);

  const onLaunchArrive = useCallback(() => {
    setPipelinePulse(true);
    setPipelineExpand(true);
    window.setTimeout(() => setPipelinePulse(false), 1000);
  }, []);

  function onStartClick() {
    if (!canSubmit || launching) return;
    const path = buildLaunchPath();
    if (!path) {
      setRevealWorking(true);
      void submit();
      return;
    }
    setError(null);
    setPipelinePulse(false);
    setPipelineExpand(false);
    setRevealWorking(false);
    setLaunching(true);
    setLaunchPath(path);
  }

  const locked = busy || launching;
  const canSubmit =
    !locked &&
    apiOk !== false &&
    Boolean(declaredOrganism) &&
    (mode === "demo" ||
      (mode === "upload" && file != null && selectedTools.length > 0));

  const organismGroups = organisms.reduce<Record<string, OrganismOption[]>>(
    (acc, o) => {
      (acc[o.group] ||= []).push(o);
      return acc;
    },
    {},
  );

  return (
    <section className="workspace">
      {awaitingJob && (
        <OrganismConfirmModal
          job={awaitingJob}
          busy={confirmBusy}
          onDecide={(d) => void handleOrganismDecision(d)}
        />
      )}
      {launchPath && (
        <StartBacteriaLaunch
          from={launchPath.from}
          to={launchPath.to}
          onArrive={onLaunchArrive}
          onDone={finishLaunch}
        />
      )}

      <header className="workspace-head">
        <div>
          <p className="eyebrow">{t("analyze.eyebrow")}</p>
          <h1 className="workspace-title">{t("analyze.title")}</h1>
          <p className="workspace-lead">{t("analyze.lead")}</p>
        </div>
        <div className={`api-status ${apiOk ? "on" : apiOk === false ? "off" : ""}`}>
          {apiOk == null
            ? t("analyze.api.checking")
            : apiOk
              ? t("analyze.api.online")
              : t("analyze.api.offline")}
        </div>
      </header>

      <div className="workspace-grid">
        <div className="work-panel">
          <div className="seg-control" role="tablist">
            <button
              type="button"
              className={mode === "upload" ? "active" : ""}
              onClick={() => setMode("upload")}
              disabled={locked}
            >
              {t("analyze.mode.live")}
            </button>
            <button
              type="button"
              className={mode === "demo" ? "active" : ""}
              onClick={() => setMode("demo")}
              disabled={locked}
            >
              {t("analyze.mode.demo")}
            </button>
          </div>

          <div className="form-grid">
            <div className="field">
              <label htmlFor="declaredOrganism">
                {t("analyze.field.organism")}
              </label>
              <select
                id="declaredOrganism"
                value={declaredOrganism}
                disabled={locked}
                onChange={(e) => setDeclaredOrganism(e.target.value)}
              >
                {Object.entries(organismGroups).map(([group, items]) => (
                  <optgroup key={group} label={group}>
                    {items.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.display_name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="sampleId">{t("analyze.field.sampleId")}</label>
              <input
                id="sampleId"
                type="text"
                value={sampleId}
                disabled={locked}
                onChange={(e) => setSampleId(e.target.value)}
              />
            </div>
          </div>

          {mode === "upload" && (
            <>
              <div
                className={`dropzone ${dragOver ? "dragover" : ""} ${locked ? "disabled" : ""}`}
                onClick={() => !locked && inputRef.current?.click()}
                onDragOver={(e) => {
                  if (locked) return;
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={locked ? undefined : onDrop}
              >
                <h3>{file ? file.name : t("analyze.drop.title")}</h3>
                <p>
                  {file
                    ? `${(file.size / 1024).toFixed(1)} KB`
                    : t("analyze.drop.hint")}
                </p>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".fasta,.fastq,.fa,.fq,.fna,.gz"
                  hidden
                  disabled={locked}
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    setFile(f);
                    if (f) {
                      setSampleId(
                        f.name.replace(/\.(fasta|fastq|fa|fq|fna)(\.gz)?$/i, ""),
                      );
                    }
                  }}
                />
              </div>

              <p className="hint-row">
                <a href={sampleFastaUrl()} download="sample_amr.fasta">
                  {t("analyze.sample.download")}
                </a>
              </p>

              {TOOL_GROUPS.map((group) => (
                <div className="tool-picker" key={group.titleKey}>
                  <div className="field-label">{t(group.titleKey)}</div>
                  <p className="muted">{t(group.hintKey)}</p>
                  <div className="tool-check-grid">
                    {TOOL_OPTIONS.filter((t) =>
                      group.keys.includes(t.key),
                    ).map((t) => {
                      const on = selectedTools.includes(t.key);
                      return (
                        <label
                          key={t.key}
                          className={[
                            "tool-check",
                            on ? "selected" : "",
                            popTool === t.key ? "pop" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        >
                          <input
                            type="checkbox"
                            checked={on}
                            disabled={locked}
                            onChange={() => toggleTool(t.key)}
                          />
                          <span className="tool-check-label">{t.label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
            </>
          )}

          <div className="actions">
            <button
              ref={startBtnRef}
              type="button"
              className={`btn btn-primary start-btn ${launching ? "morphing" : ""}`}
              disabled={!canSubmit && !launching}
              onClick={onStartClick}
            >
              <span className="start-btn-label">
                {busy
                  ? awaitingJob
                    ? t("analyze.waitingOrganism")
                    : t("analyze.starting")
                  : launching
                    ? ""
                    : t("analyze.start")}
              </span>
            </button>
          </div>

          {error && <div className="error-banner">{error}</div>}
        </div>

        <div
          className={[
            "work-panel",
            "progress-side",
            pipelinePulse ? "pipeline-pulse" : "",
            pipelineExpand ? "pipeline-expand" : "",
            revealWorking ? "pipeline-working" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          ref={pipelineRef}
        >
          {revealWorking ? (
            <div className="run-stage pipeline-content-enter">
              <SequenceReader
                running={
                  busy ||
                  job?.status === "running" ||
                  job?.status === "awaiting_organism_confirmation"
                }
                activeLabel={
                  job?.steps.find((s) => s.status === "running")?.label
                }
              />
              {job ? (
                <PipelineProgress steps={job.steps} jobStatus={job.status} />
              ) : (
                <div className="pipeline-boot">
                  <span className="spinner" /> {t("analyze.pipeline.boot")}
                </div>
              )}
            </div>
          ) : (
            <div className="pipeline-placeholder">
              <h2 className="pipeline-title">{t("pipeline.title")}</h2>
              <p className="muted">{t("analyze.pipeline.placeholderLead")}</p>
              <BacteriaField />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
