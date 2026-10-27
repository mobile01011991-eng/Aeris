import { useCallback, useEffect, useState } from "react";
import {
  fetchJob,
  fetchResult,
  isTerminalJob,
  type AnalysisJob,
} from "./client";
import type { AMRResultPayload } from "./types";

const CACHE_PREFIX = "aeris:result:";

function readCache(sampleId: string): AMRResultPayload | null {
  const raw = sessionStorage.getItem(`${CACHE_PREFIX}${sampleId}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AMRResultPayload;
  } catch {
    return null;
  }
}

function writeCache(payload: AMRResultPayload): void {
  sessionStorage.setItem(
    `${CACHE_PREFIX}${payload.sample_id}`,
    JSON.stringify(payload),
  );
}

/**
 * Report data for one sample, from a live job when `jobId` is given and from
 * the stored payload otherwise.
 *
 * Both sources expose `tool_reports`, so pages render the same way whether the
 * run is still going or was finished long ago.
 */
export function useSampleReports(sampleId?: string, jobId?: string | null) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [payload, setPayload] = useState<AMRResultPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(sampleId));

  const applyPayload = useCallback((data: AMRResultPayload) => {
    setPayload(data);
    writeCache(data);
    setError(null);
  }, []);

  // Stored payload (previous runs, or the run that just finished).
  useEffect(() => {
    if (!sampleId) {
      setPayload(null);
      setLoading(false);
      return;
    }

    let alive = true;
    const cached = readCache(sampleId);
    if (cached) {
      setPayload(cached);
      setLoading(false);
    }

    fetchResult(sampleId)
      .then((data) => {
        if (alive) applyPayload(data);
      })
      .catch((err) => {
        if (!alive) return;
        // A live job has nothing stored yet — that is not an error.
        if (!cached && !jobId) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [sampleId, jobId, applyPayload]);

  // Live job: keep polling so cards flip as each tool finishes.
  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }

    let alive = true;
    let timer: number | undefined;

    const tick = async () => {
      try {
        const next = await fetchJob(jobId);
        if (!alive) return;
        setJob(next);

        if (isTerminalJob(next)) {
          if (next.result) {
            applyPayload(next.result);
          } else if (next.sample_id) {
            fetchResult(next.sample_id)
              .then((data) => {
                if (alive) applyPayload(data);
              })
              .catch(() => undefined);
          }
          setLoading(false);
          return;
        }

        setLoading(false);
        timer = window.setTimeout(tick, 900);
      } catch {
        // Job store is in-memory; if it is gone, fall back to stored results.
        if (alive) setJob(null);
      }
    };

    void tick();

    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId, applyPayload]);

  return { job, payload, error, loading };
}
