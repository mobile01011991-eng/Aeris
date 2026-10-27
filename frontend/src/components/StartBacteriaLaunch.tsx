import { useEffect, useMemo, useState, type CSSProperties } from "react";

export type LaunchRect = {
  left: number;
  top: number;
  width: number;
  height: number;
  cx: number;
  cy: number;
};

function mockDnaChunk(len = 14): string {
  const bases = "ATGC";
  let out = "";
  for (let i = 0; i < len; i++) {
    out += bases[Math.floor(Math.random() * 4)];
  }
  return out;
}

/**
 * Bacterium winds up (slight reverse), then one smooth dash into the pipeline.
 * onArrive fires near impact; onDone after the panel can expand + swap content.
 */
export function StartBacteriaLaunch({
  from,
  to,
  onArrive,
  onDone,
}: {
  from: LaunchRect;
  to: LaunchRect;
  onArrive?: () => void;
  onDone: () => void;
}) {
  const [showDna, setShowDna] = useState(false);
  const [dna, setDna] = useState(() => mockDnaChunk());

  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;

  const style = useMemo(
    () =>
      ({
        left: from.cx,
        top: from.cy,
        width: Math.max(from.width, 148),
        height: Math.max(from.height, 42),
        ["--dx"]: `${dx}px`,
        ["--dy"]: `${dy}px`,
        ["--bw"]: `${Math.max(from.width, 148)}px`,
        ["--bh"]: `${Math.max(from.height, 42)}px`,
      }) as CSSProperties,
    [from, dx, dy],
  );

  useEffect(() => {
    const timers = [
      window.setTimeout(() => setShowDna(true), 180),
      // Near end of flight — expand frame while idle content still shows
      window.setTimeout(() => onArrive?.(), 1550),
      // After expand, swap content + start analysis
      window.setTimeout(() => onDone(), 2100),
    ];
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [onArrive, onDone]);

  useEffect(() => {
    if (!showDna) return;
    const id = window.setInterval(() => setDna(mockDnaChunk()), 150);
    return () => window.clearInterval(id);
  }, [showDna]);

  return (
    <div className="start-launch-layer" aria-hidden="true">
      <div className="start-bact-hero" data-dna={showDna ? "1" : "0"} style={style}>
        <span className="start-bact-body">
          <span className="start-bact-label">
            {showDna ? dna : "Start analysis"}
          </span>
        </span>
        <span className="start-bact-flagellum" />
        <span className="start-bact-flagellum secondary" />
      </div>
    </div>
  );
}

export function rectFromEl(el: HTMLElement): LaunchRect {
  const r = el.getBoundingClientRect();
  return {
    left: r.left,
    top: r.top,
    width: r.width,
    height: r.height,
    cx: r.left + r.width / 2,
    cy: r.top + r.height / 2,
  };
}
