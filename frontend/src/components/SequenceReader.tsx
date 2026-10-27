import { useEffect, useState } from "react";
import { useI18n } from "../i18n/I18nContext";

const BASES = "ATGCGTAACCTGGAATCCTAGCTAGGCTAACCGGTTAAACGGTTCCATG";
const CHUNK = 48;

/** Live sequence-reading strip shown while the pipeline runs. */
export function SequenceReader({
  activeLabel,
  running,
}: {
  activeLabel?: string;
  running: boolean;
}) {
  const { t } = useI18n();
  const [offset, setOffset] = useState(0);
  const [reads, setReads] = useState(0);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      setOffset((o) => (o + 3) % BASES.length);
      setReads((r) => r + 1);
    }, 90);
    return () => window.clearInterval(id);
  }, [running]);

  const windowSeq = (BASES + BASES).slice(offset, offset + CHUNK);

  return (
    <div className={`seq-reader ${running ? "live" : ""}`} aria-hidden="true">
      <div className="seq-reader-top">
        <span className="seq-tag">{t("seq.tag")}</span>
        <span className="seq-meta">
          {running ? t("seq.frame", { n: reads }) : t("seq.standby")}
          {activeLabel ? ` · ${activeLabel}` : ""}
        </span>
      </div>

      <div className="seq-track">
        <div className="seq-scan" />
        <div className="seq-bases">
          {windowSeq.split("").map((b, i) => (
            <span key={`${offset}-${i}`} className={`base base-${b}`}>
              {b}
            </span>
          ))}
        </div>
      </div>

      <div className="seq-rail">
        <span className="seq-rail-fill" style={{ width: running ? "72%" : "8%" }} />
        <span className="seq-rail-head" />
      </div>

      <div className="seq-orfs">
        <span className="orf hit">ORF · blaKPC</span>
        <span className="orf">ORF · scan</span>
        <span className={`orf ${running ? "pulse" : ""}`}>alignment</span>
      </div>
    </div>
  );
}
