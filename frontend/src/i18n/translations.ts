export type Lang = "en" | "th";

export const LANGUAGES: { code: Lang; label: string; title: string }[] = [
  { code: "en", label: "EN", title: "English" },
  { code: "th", label: "ไทย", title: "ภาษาไทย" },
];

export const LOCALES: Record<Lang, string> = {
  en: "en-US",
  th: "th-TH",
};

/**
 * UI copy. English is the source language; missing Thai keys fall back to it.
 *
 * Tool names (ResFinder, CARD/RGI, …) and gene symbols stay untranslated.
 */
const en = {
  "lang.label": "Language",

  "nav.analyze": "Analyze",
  "nav.results": "Results",
  "footer.brand": "AERIS · resistance-gene screening",
  "footer.filters":
    "Database tools + DeepARG AI screen · ID ≥ 90% · Cov ≥ 80%",

  "analyze.eyebrow": "Resistance-gene screening",
  "analyze.title": "Analyze",
  "analyze.lead":
    "Select the expected organism and upload a sequence. Four database tools compare it against resistance-gene databases, and DeepARG adds a deep-learning screen. Each tool gets its own report.",
  "analyze.api.checking": "Checking API…",
  "analyze.api.online": "API online",
  "analyze.api.offline": "API offline",
  "analyze.mode.live": "Live sequence",
  "analyze.mode.demo": "Fixture demo",
  "analyze.field.organism": "Expected organism",
  "analyze.field.sampleId": "Sample ID",
  "analyze.drop.title": "Drop FASTA / FASTQ",
  "analyze.drop.hint": "Click to browse · contig assemblies preferred",
  "analyze.sample.download": "Download sample_amr.fasta",
  "analyze.tools.database.title": "Database tools",
  "analyze.tools.database.hint":
    "Compare the sequence against resistance-gene databases.",
  "analyze.tools.ai.title": "AI screen",
  "analyze.tools.ai.hint":
    "DeepARG uses deep learning to predict resistance-gene families.",
  "analyze.start": "Start analysis",
  "analyze.starting": "Starting pipeline…",
  "analyze.waitingOrganism": "Waiting for organism confirmation…",
  "analyze.error.selectOrganism": "Select an organism before starting analysis",
  "analyze.error.stopped": "Analysis stopped",
  "analyze.error.cancelled": "Cancelled at organism confirmation",
  "analyze.pipeline.placeholderLead":
    "Choose an organism first. Analysis stages the sequence, identifies the species, then runs the database tools followed by the DeepARG AI screen.",
  "analyze.pipeline.boot": "Starting pipeline…",

  "pipeline.title": "Pipeline",
  "pipeline.stage.input": "Input",
  "pipeline.stage.tools": "Database tools",
  "pipeline.stage.ai": "AI screen",
  "pipeline.stage.output": "Output",
  "pipeline.state.complete": "All nodes complete",
  "pipeline.state.stopped": "Pipeline stopped",
  "pipeline.state.awaiting": "Waiting for organism confirmation",
  "pipeline.state.working": "Working: {step}",
  "pipeline.state.idle": "Waiting to start",
  "pipeline.step.ingest": "Ingest",
  "pipeline.step.species": "Species ID",
  "pipeline.step.aggregate": "Aggregate",
  "pipeline.step.save": "Save",
  "pipeline.detail.queued": "Queued",
  "pipeline.detail.inProgress": "In progress…",

  "step.status.pending": "Waiting",
  "step.status.running": "Running",
  "step.status.done": "Done",
  "step.status.failed": "Failed",
  "step.status.skipped": "Skipped",

  "report.status.pending": "Queued",
  "report.status.running": "Running",
  "report.status.done": "Report ready",
  "report.status.failed": "Failed",
  "report.status.skipped": "Skipped",

  "job.status.queued": "queued",
  "job.status.running": "running",
  "job.status.awaiting_organism_confirmation": "waiting for organism confirmation",
  "job.status.completed": "completed",
  "job.status.failed": "failed",
  "job.status.cancelled": "cancelled",

  "organism.eyebrow": "Species gate",
  "organism.title": "Organism confirmation needed",
  "organism.body":
    "Species ID (Mash / markers) does not clearly match the organism you selected. Choose which organism profile to continue with — it is passed to AMRFinderPlus and shown on every tool report.",
  "organism.youSelected": "You selected",
  "organism.detected": "Detected from sequence",
  "organism.status": "Status",
  "organism.confidence": "Confidence",
  "organism.accept": "Accept detected",
  "organism.keep": "Keep my choice",
  "organism.cancel": "Cancel",

  "seq.tag": "SEQUENCE STREAM",
  "seq.standby": "standby",
  "seq.frame": "frame {n}",

  "idle.title": "Waiting for sequence",
  "idle.hint": "Culture field idle · press Start analysis",

  "hub.eyebrow": "Genotypic screening",
  "hub.title": "Tool reports",
  "hub.sample": "Sample",
  "hub.jobStatus": "job {status}",
  "hub.newAnalysis": "New analysis",
  "hub.download": "Download JSON",
  "hub.loading": "Loading tool reports…",
  "hub.demoNote":
    "Fixture demo — tool-native fields are derived from the demo reports.",
  "hub.awaiting": "This run is paused for organism confirmation.",
  "hub.awaiting.link": "Go back to Analyze",
  "hub.awaiting.tail":
    "to accept the detected organism, keep your choice, or cancel.",
  "hub.database.title": "Database screening",
  "hub.database.lead":
    "These tools compare the sequence against resistance-gene databases. Each report opens as soon as that tool finishes.",
  "hub.ai.title": "AI prediction",
  "hub.ai.lead":
    "Deep learning screen, reported separately from the database tools.",
  "hub.disclaimer":
    "These reports show which resistance genes were detected in the sequence. They are not a susceptibility test: a tool finding no gene does not mean the isolate is susceptible.",

  "card.aiBadge": "Deep Learning (AI) prediction",
  "card.counts": "{passed} of {total} hits pass filter",
  "card.waiting": "Waiting for this tool",
  "card.failed": "Tool run failed",
  "card.open": "Open report",
  "card.running": "Running…",
  "card.notReady": "Not ready",

  "tool.resfinder.blurb":
    "Acquired resistance genes by BLAST/KMA, with a predicted phenotype per antimicrobial.",
  "tool.rgi.blurb":
    "Protein search against CARD with ontology: mechanism, gene family, Perfect/Strict.",
  "tool.amrfinderplus.blurb":
    "NCBI reference genes with class/subclass, ALLELEX vs BLASTX, and mutations when the organism is set.",
  "tool.abricate.blurb": "BLASTN gene screen against the ARG-ANNOT database.",
  "tool.deeparg.blurb":
    "Deep Learning (AI) — predicts resistance-gene families; not a BLAST allele call.",
  "tool.generic.blurb": "Resistance-gene screen.",

  "context.organism": "Organism used",
  "context.declaredDetected": "Declared / detected",
  "context.decision": "Species decision",
  "context.filters": "Hit filters",

  "toolPage.back": "← All tool reports",
  "toolPage.backBtn": "Back to hub",
  "toolPage.badge.database": "Database screen",
  "toolPage.badge.ai": "Deep Learning (AI) prediction",
  "toolPage.loading": "Loading report…",
  "toolPage.notInRun": "“{tool}” was not part of this run.",
  "toolPage.stillRunning":
    "This tool is still running. The report appears here as soon as it finishes.",
  "toolPage.failedNoReport": "This tool failed, so no report was produced.",
  "toolPage.notRunYet": "This tool has not run yet.",
  "toolPage.failedBanner": "This tool failed during the run.",
  "toolPage.demoNote":
    "Fixture demo — fields below are derived from the demo report.",
  "toolPage.noView": "No report view for “{tool}”.",

  "table.gene": "Gene",
  "table.drugClass": "Drug class",
  "table.identity": "Identity",
  "table.coverage": "Coverage",
  "table.contig": "Contig",
  "table.accession": "Accession",
  "table.filter": "Filter",
  "table.pass": "PASS",
  "table.fail": "FAIL",
  "table.empty": "No genes reported by this tool.",

  "resfinder.genes.title": "Acquired resistance genes",
  "resfinder.genes.lead":
    "BLAST/KMA hits against the ResFinder database, grouped by contig.",
  "resfinder.genes.empty": "No acquired genes were reported.",
  "resfinder.altAllele": "alternative allele on the same contig",
  "resfinder.pheno.title": "Predicted phenotype per antimicrobial",
  "resfinder.pheno.lead":
    "ResFinder maps detected genes to antimicrobials. This is a genotypic prediction from gene content, not a laboratory susceptibility test.",
  "resfinder.pheno.empty": "No phenotype table was produced for this run.",
  "resfinder.pheno.toggle":
    "Show all {count} antimicrobials (default: only predicted resistance)",
  "resfinder.pheno.none": "No antimicrobial reached a resistance prediction.",
  "resfinder.col.antimicrobial": "Antimicrobial",
  "resfinder.col.class": "Class",
  "resfinder.col.phenotype": "WGS-predicted phenotype",
  "resfinder.col.match": "Match",
  "resfinder.col.background": "Genetic background",
  "resfinder.legend.0": "0 — no match",
  "resfinder.legend.1":
    "1 — below 100% identity and shorter than the reference",
  "resfinder.legend.2": "2 — 100% identity but shorter than the reference",
  "resfinder.legend.3": "3 — 100% identity over the full reference length",

  "pointfinder.title": "Chromosomal point mutations (PointFinder)",
  "pointfinder.lead":
    "Requires a supported species. These are mutations in the organism's own genes, not acquired gene cassettes.",
  "pointfinder.species": "PointFinder panel: {species}",
  "pointfinder.skipped":
    "PointFinder is not available for this organism, so only acquired genes were screened.",
  "pointfinder.noHits": "No chromosomal resistance mutations found.",
  "pointfinder.failed":
    "PointFinder did not complete. Acquired-gene results above are unaffected.",
  "pointfinder.codon": "codon {position}",
  "pointfinder.col.mutation": "Mutation",
  "pointfinder.col.change": "Nucleotide / amino acid change",
  "pointfinder.col.antimicrobials": "Linked antimicrobials",
  "pointfinder.note":
    "Absence of a mutation is not clinical susceptibility. PointFinder only checks the genes in its panel for this species.",

  "rgi.title": "CARD hits",
  "rgi.lead":
    "Each hit carries CARD ontology: resistance mechanism, AMR gene family, and how closely it matched the CARD model.",
  "rgi.fallbackLead":
    "RGI's own table was not available for this run; showing the shared hAMRonized fields instead.",
  "rgi.col.bestHit": "Best hit (ARO)",
  "rgi.col.cutOff": "Cut-off",
  "rgi.col.refLength": "% of reference length",
  "rgi.col.mechanism": "Resistance mechanism",
  "rgi.col.family": "AMR gene family",
  "rgi.aro": "ARO {id}",
  "rgi.legend.perfect":
    "Perfect — identical to a curated CARD reference model.",
  "rgi.legend.strict":
    "Strict — above CARD's curated bitscore cut-off but not an exact match.",

  "amr.title": "AMR elements (NCBI reference genes)",
  "amr.lead":
    "ALLELEX means an exact allele match; BLASTX means the closest reference protein was found by alignment.",
  "amr.fallbackLead":
    "AMRFinderPlus's own table was not available for this run; showing the shared hAMRonized fields instead.",
  "amr.empty": "No AMR elements were reported.",
  "amr.col.element": "Element",
  "amr.col.subclass": "Subclass",
  "amr.col.method": "Method",
  "amr.col.closestRef": "Closest reference",
  "amr.point.title": "Chromosomal mutations",
  "amr.point.lead":
    "Point mutations reported for the confirmed organism, kept separate from acquired elements.",
  "amr.other.title": "Non-AMR elements",
  "amr.other.lead":
    "Virulence and stress-response elements. Reported for completeness and not part of the AMR screen.",

  "abricate.title": "ARG-ANNOT gene screen",
  "abricate.lead":
    "BLASTN hits against ARG-ANNOT, with the coordinates ABRicate found on each contig.",
  "abricate.fallbackLead":
    "ABRicate's own table was not available for this run; showing the shared hAMRonized fields instead.",
  "abricate.col.position": "Position",
  "abricate.note":
    "ARG-ANNOT usually ships no antibiotic annotation, so no drug list is shown here. Use the ResFinder, CARD/RGI or AMRFinderPlus report for class-level detail.",

  "deeparg.title": "Predicted resistance-gene families",
  "deeparg.lead":
    "DeepARG runs a neural network (LS model) over the assembled nucleotide sequence together with a database alignment. It reports a gene family such as KPC, TEM or NDM and a broad class such as beta-lactam — not an allele-level call like blaKPC-2.",
  "deeparg.empty": "DeepARG returned no predictions for this sequence.",
  "deeparg.col.family": "Gene family",
  "deeparg.col.class": "Predicted class",
  "deeparg.col.probability": "Model probability",
  "deeparg.col.identity": "Alignment identity",
  "deeparg.aiOnly": "AI-only — review",
  "deeparg.note":
    "DeepARG is not counted in the database-tool agreement. A family flagged AI-only was predicted here but not called by ResFinder, CARD/RGI, AMRFinderPlus or ABRicate, so it needs review.",

  "agreement.summary": "Agreement across database tools ({count} gene families)",
  "agreement.lead":
    "How many of the {total} database tools called each gene family, after the identity and coverage filters. DeepARG is excluded.",
  "agreement.col.family": "Gene family",
  "agreement.col.seenBy": "Seen by",
  "agreement.col.tools": "Tools",
  "agreement.col.genes": "Gene calls",
  "agreement.seenBy": "{n} of {total}",

  "samples.title": "Samples",
  "samples.lead":
    "Open a sample to read its per-tool resistance-gene reports, or start a new analysis.",
  "samples.runDemo": "Run demo",
  "samples.upload": "Upload sequence",
  "samples.recent": "Recent samples",
  "samples.empty": "No stored results yet.",
  "samples.open": "Open reports →",
};

export type TranslationKey = keyof typeof en;

/** Typed as complete, so a missing Thai string fails the build. */
const th: Record<TranslationKey, string> = {
  "lang.label": "ภาษา",

  "nav.analyze": "วิเคราะห์",
  "nav.results": "ผลลัพธ์",
  "footer.brand": "AERIS · ระบบตรวจหายีนดื้อยา",
  "footer.filters":
    "เครื่องมือฐานข้อมูล + DeepARG (AI) · ID ≥ 90% · Cov ≥ 80%",

  "analyze.eyebrow": "การตรวจหายีนดื้อยา",
  "analyze.title": "วิเคราะห์",
  "analyze.lead":
    "เลือกชนิดเชื้อที่คาดว่าเป็น แล้วอัปโหลดลำดับพันธุกรรม ระบบจะใช้เครื่องมือฐานข้อมูล 4 ชนิดเทียบกับฐานข้อมูลยีนดื้อยา และเพิ่มการตรวจด้วย DeepARG ซึ่งเป็น deep learning โดยแต่ละเครื่องมือมีรายงานของตัวเอง",
  "analyze.api.checking": "กำลังตรวจสอบ API…",
  "analyze.api.online": "API พร้อมใช้งาน",
  "analyze.api.offline": "API ไม่ตอบสนอง",
  "analyze.mode.live": "ลำดับพันธุกรรมจริง",
  "analyze.mode.demo": "โหมดสาธิต",
  "analyze.field.organism": "เชื้อที่คาดว่าเป็น",
  "analyze.field.sampleId": "รหัสตัวอย่าง",
  "analyze.drop.title": "ลากไฟล์ FASTA / FASTQ มาวาง",
  "analyze.drop.hint": "คลิกเพื่อเลือกไฟล์ · แนะนำไฟล์ contig assembly",
  "analyze.sample.download": "ดาวน์โหลดไฟล์ตัวอย่าง sample_amr.fasta",
  "analyze.tools.database.title": "เครื่องมือฐานข้อมูล",
  "analyze.tools.database.hint":
    "เทียบลำดับพันธุกรรมกับฐานข้อมูลยีนดื้อยา",
  "analyze.tools.ai.title": "การตรวจด้วย AI",
  "analyze.tools.ai.hint":
    "DeepARG ใช้ deep learning ทำนายกลุ่มยีนดื้อยา",
  "analyze.start": "เริ่มวิเคราะห์",
  "analyze.starting": "กำลังเริ่มไปป์ไลน์…",
  "analyze.waitingOrganism": "รอยืนยันชนิดเชื้อ…",
  "analyze.error.selectOrganism": "เลือกชนิดเชื้อก่อนเริ่มวิเคราะห์",
  "analyze.error.stopped": "การวิเคราะห์หยุดลง",
  "analyze.error.cancelled": "ยกเลิกที่ขั้นยืนยันชนิดเชื้อ",
  "analyze.pipeline.placeholderLead":
    "เลือกชนิดเชื้อก่อน เมื่อเริ่มวิเคราะห์ ระบบจะเตรียมไฟล์ ระบุชนิดเชื้อ แล้วรันเครื่องมือฐานข้อมูล ตามด้วยการตรวจด้วย DeepARG",
  "analyze.pipeline.boot": "กำลังเริ่มไปป์ไลน์…",

  "pipeline.title": "ไปป์ไลน์",
  "pipeline.stage.input": "ข้อมูลเข้า",
  "pipeline.stage.tools": "เครื่องมือฐานข้อมูล",
  "pipeline.stage.ai": "การตรวจด้วย AI",
  "pipeline.stage.output": "ผลลัพธ์",
  "pipeline.state.complete": "เสร็จทุกขั้นตอน",
  "pipeline.state.stopped": "ไปป์ไลน์หยุดทำงาน",
  "pipeline.state.awaiting": "รอยืนยันชนิดเชื้อ",
  "pipeline.state.working": "กำลังทำงาน: {step}",
  "pipeline.state.idle": "รอเริ่มทำงาน",
  "pipeline.step.ingest": "รับไฟล์",
  "pipeline.step.species": "ระบุชนิดเชื้อ",
  "pipeline.step.aggregate": "รวมรายงาน",
  "pipeline.step.save": "บันทึก",
  "pipeline.detail.queued": "รอคิว",
  "pipeline.detail.inProgress": "กำลังดำเนินการ…",

  "step.status.pending": "รอคิว",
  "step.status.running": "กำลังรัน",
  "step.status.done": "เสร็จ",
  "step.status.failed": "ล้มเหลว",
  "step.status.skipped": "ข้าม",

  "report.status.pending": "รอคิว",
  "report.status.running": "กำลังรัน",
  "report.status.done": "รายงานพร้อม",
  "report.status.failed": "ล้มเหลว",
  "report.status.skipped": "ข้าม",

  "job.status.queued": "รอคิว",
  "job.status.running": "กำลังรัน",
  "job.status.awaiting_organism_confirmation": "รอยืนยันชนิดเชื้อ",
  "job.status.completed": "เสร็จสิ้น",
  "job.status.failed": "ล้มเหลว",
  "job.status.cancelled": "ถูกยกเลิก",

  "organism.eyebrow": "ด่านตรวจชนิดเชื้อ",
  "organism.title": "ต้องยืนยันชนิดเชื้อ",
  "organism.body":
    "การระบุชนิดเชื้อ (Mash / markers) ไม่ตรงกับเชื้อที่คุณเลือกไว้ชัดเจน กรุณาเลือกว่าจะวิเคราะห์ต่อด้วยชนิดเชื้อใด ค่านี้จะถูกส่งให้ AMRFinderPlus และแสดงบนรายงานทุกเครื่องมือ",
  "organism.youSelected": "คุณเลือกไว้",
  "organism.detected": "ตรวจได้จากลำดับพันธุกรรม",
  "organism.status": "สถานะ",
  "organism.confidence": "ความมั่นใจ",
  "organism.accept": "ใช้เชื้อที่ตรวจได้",
  "organism.keep": "คงเชื้อที่เลือกไว้",
  "organism.cancel": "ยกเลิก",

  "seq.tag": "สตรีมลำดับพันธุกรรม",
  "seq.standby": "รอทำงาน",
  "seq.frame": "เฟรม {n}",

  "idle.title": "รอลำดับพันธุกรรม",
  "idle.hint": "ยังไม่เริ่มทำงาน · กดเริ่มวิเคราะห์",

  "hub.eyebrow": "การตรวจระดับพันธุกรรม",
  "hub.title": "รายงานรายเครื่องมือ",
  "hub.sample": "ตัวอย่าง",
  "hub.jobStatus": "สถานะงาน {status}",
  "hub.newAnalysis": "วิเคราะห์ใหม่",
  "hub.download": "ดาวน์โหลด JSON",
  "hub.loading": "กำลังโหลดรายงาน…",
  "hub.demoNote":
    "โหมดสาธิต — ข้อมูลเฉพาะของแต่ละเครื่องมือถูกสร้างจากรายงานตัวอย่าง",
  "hub.awaiting": "งานนี้หยุดรอการยืนยันชนิดเชื้อ",
  "hub.awaiting.link": "กลับไปหน้าวิเคราะห์",
  "hub.awaiting.tail":
    "เพื่อใช้เชื้อที่ตรวจได้ คงเชื้อที่เลือกไว้ หรือยกเลิก",
  "hub.database.title": "การตรวจด้วยฐานข้อมูล",
  "hub.database.lead":
    "เครื่องมือกลุ่มนี้เทียบลำดับพันธุกรรมกับฐานข้อมูลยีนดื้อยา รายงานจะเปิดอ่านได้ทันทีที่เครื่องมือนั้นทำงานเสร็จ",
  "hub.ai.title": "การทำนายด้วย AI",
  "hub.ai.lead":
    "การตรวจด้วย deep learning ซึ่งรายงานแยกจากเครื่องมือฐานข้อมูล",
  "hub.disclaimer":
    "รายงานเหล่านี้แสดงว่าตรวจพบยีนดื้อยาใดในลำดับพันธุกรรม ไม่ใช่การทดสอบความไวต่อยา การที่เครื่องมือไม่พบยีนไม่ได้แปลว่าเชื้อไวต่อยา",

  "card.aiBadge": "การทำนายด้วย Deep Learning (AI)",
  "card.counts": "ผ่านเกณฑ์ {passed} จาก {total} รายการ",
  "card.waiting": "รอเครื่องมือนี้ทำงาน",
  "card.failed": "เครื่องมือทำงานไม่สำเร็จ",
  "card.open": "เปิดรายงาน",
  "card.running": "กำลังรัน…",
  "card.notReady": "ยังไม่พร้อม",

  "tool.resfinder.blurb":
    "ค้นหายีนดื้อยาแบบ acquired ด้วย BLAST/KMA พร้อมทำนายฟีโนไทป์รายยา",
  "tool.rgi.blurb":
    "ค้นหาโปรตีนเทียบกับฐาน CARD พร้อม ontology: กลไก กลุ่มยีน และระดับ Perfect/Strict",
  "tool.amrfinderplus.blurb":
    "ยีนอ้างอิงของ NCBI พร้อมกลุ่มยา/กลุ่มย่อย วิธี ALLELEX หรือ BLASTX และการกลายพันธุ์เมื่อระบุชนิดเชื้อ",
  "tool.abricate.blurb": "สแกนยีนด้วย BLASTN เทียบฐานข้อมูล ARG-ANNOT",
  "tool.deeparg.blurb":
    "Deep Learning (AI) — ทำนายกลุ่มยีนดื้อยา ไม่ใช่การระบุอัลลีลด้วย BLAST",
  "tool.generic.blurb": "การตรวจหายีนดื้อยา",

  "context.organism": "เชื้อที่ใช้วิเคราะห์",
  "context.declaredDetected": "ที่ระบุ / ที่ตรวจได้",
  "context.decision": "การตัดสินชนิดเชื้อ",
  "context.filters": "เกณฑ์กรองผล",

  "toolPage.back": "← รายงานทั้งหมด",
  "toolPage.backBtn": "กลับหน้ารวมรายงาน",
  "toolPage.badge.database": "ตรวจด้วยฐานข้อมูล",
  "toolPage.badge.ai": "การทำนายด้วย Deep Learning (AI)",
  "toolPage.loading": "กำลังโหลดรายงาน…",
  "toolPage.notInRun": "ไม่ได้ใช้ “{tool}” ในการรันครั้งนี้",
  "toolPage.stillRunning":
    "เครื่องมือนี้กำลังทำงาน รายงานจะแสดงที่นี่ทันทีที่เสร็จ",
  "toolPage.failedNoReport": "เครื่องมือนี้ทำงานไม่สำเร็จ จึงไม่มีรายงาน",
  "toolPage.notRunYet": "เครื่องมือนี้ยังไม่ได้เริ่มทำงาน",
  "toolPage.failedBanner": "เครื่องมือนี้ทำงานไม่สำเร็จระหว่างการรัน",
  "toolPage.demoNote":
    "โหมดสาธิต — ข้อมูลด้านล่างสร้างจากรายงานตัวอย่าง",
  "toolPage.noView": "ไม่มีมุมมองรายงานสำหรับ “{tool}”",

  "table.gene": "ยีน",
  "table.drugClass": "กลุ่มยา",
  "table.identity": "ความเหมือน",
  "table.coverage": "ความครอบคลุม",
  "table.contig": "Contig",
  "table.accession": "รหัสอ้างอิง",
  "table.filter": "ตัวกรอง",
  "table.pass": "ผ่าน",
  "table.fail": "ไม่ผ่าน",
  "table.empty": "เครื่องมือนี้ไม่พบยีน",

  "resfinder.genes.title": "ยีนดื้อยาแบบ acquired",
  "resfinder.genes.lead":
    "ผลการเทียบด้วย BLAST/KMA กับฐานข้อมูล ResFinder จัดกลุ่มตาม contig",
  "resfinder.genes.empty": "ไม่พบยีนดื้อยาแบบ acquired",
  "resfinder.altAllele": "อัลลีลทางเลือกบน contig เดียวกัน",
  "resfinder.pheno.title": "ฟีโนไทป์ที่ทำนายไว้รายยา",
  "resfinder.pheno.lead":
    "ResFinder จับคู่ยีนที่พบกับยาต้านจุลชีพ ผลนี้เป็นการทำนายจากยีนที่ตรวจพบ ไม่ใช่การทดสอบความไวต่อยาในห้องปฏิบัติการ",
  "resfinder.pheno.empty": "การรันครั้งนี้ไม่มีตารางฟีโนไทป์",
  "resfinder.pheno.toggle":
    "แสดงยาทั้ง {count} รายการ (ค่าเริ่มต้น: แสดงเฉพาะที่ทำนายว่าดื้อ)",
  "resfinder.pheno.none": "ไม่มียาใดที่ทำนายว่าดื้อ",
  "resfinder.col.antimicrobial": "ยาต้านจุลชีพ",
  "resfinder.col.class": "กลุ่มยา",
  "resfinder.col.phenotype": "ฟีโนไทป์ที่ทำนายจาก WGS",
  "resfinder.col.match": "ระดับ Match",
  "resfinder.col.background": "ยีนที่เป็นเหตุ",
  "resfinder.legend.0": "0 — ไม่พบผลตรงกัน",
  "resfinder.legend.1":
    "1 — ความเหมือนต่ำกว่า 100% และสั้นกว่ายีนอ้างอิง",
  "resfinder.legend.2": "2 — ความเหมือน 100% แต่สั้นกว่ายีนอ้างอิง",
  "resfinder.legend.3": "3 — ความเหมือน 100% ครบความยาวยีนอ้างอิง",

  "pointfinder.title": "การกลายพันธุ์บนโครโมโซม (PointFinder)",
  "pointfinder.lead":
    "ต้องเป็นชนิดเชื้อที่ฐานข้อมูลรองรับ ผลส่วนนี้คือการกลายพันธุ์ในยีนของเชื้อเอง ไม่ใช่ยีนที่ได้รับมาเพิ่ม",
  "pointfinder.species": "ชุดยีนที่ใช้ตรวจ: {species}",
  "pointfinder.skipped":
    "ฐานข้อมูล PointFinder ไม่รองรับเชื้อชนิดนี้ จึงตรวจเฉพาะยีนที่ได้รับมาเพิ่ม",
  "pointfinder.noHits": "ไม่พบการกลายพันธุ์ที่เกี่ยวข้องกับการดื้อยาบนโครโมโซม",
  "pointfinder.failed":
    "PointFinder ทำงานไม่สำเร็จ แต่ผลยีนที่ได้รับมาเพิ่มด้านบนยังใช้ได้ตามปกติ",
  "pointfinder.codon": "โคดอนที่ {position}",
  "pointfinder.col.mutation": "การกลายพันธุ์",
  "pointfinder.col.change": "การเปลี่ยนนิวคลีโอไทด์ / กรดอะมิโน",
  "pointfinder.col.antimicrobials": "ยาที่เกี่ยวข้อง",
  "pointfinder.note":
    "การไม่พบการกลายพันธุ์ไม่ได้แปลว่าเชื้อไวต่อยา PointFinder ตรวจเฉพาะยีนที่อยู่ในชุดข้อมูลของเชื้อชนิดนั้น",

  "rgi.title": "ผลการเทียบกับ CARD",
  "rgi.lead":
    "แต่ละผลมี ontology ของ CARD ได้แก่ กลไกการดื้อยา กลุ่มยีน AMR และความใกล้เคียงกับโมเดลของ CARD",
  "rgi.fallbackLead":
    "การรันครั้งนี้ไม่มีตารางของ RGI จึงแสดงข้อมูลชุดมาตรฐานจาก hAMRonization แทน",
  "rgi.col.bestHit": "ผลที่ตรงที่สุด (ARO)",
  "rgi.col.cutOff": "ระดับความตรง",
  "rgi.col.refLength": "% ความยาวเทียบยีนอ้างอิง",
  "rgi.col.mechanism": "กลไกการดื้อยา",
  "rgi.col.family": "กลุ่มยีน AMR",
  "rgi.aro": "ARO {id}",
  "rgi.legend.perfect": "Perfect — ตรงกับโมเดลอ้างอิงของ CARD ทั้งหมด",
  "rgi.legend.strict":
    "Strict — สูงกว่าเกณฑ์ bitscore ที่ CARD กำหนด แต่ไม่ตรงทั้งหมด",

  "amr.title": "องค์ประกอบ AMR (ยีนอ้างอิงของ NCBI)",
  "amr.lead":
    "ALLELEX หมายถึงตรงกับอัลลีลแบบเป๊ะ ส่วน BLASTX หมายถึงหาโปรตีนอ้างอิงที่ใกล้ที่สุดด้วยการเทียบลำดับ",
  "amr.fallbackLead":
    "การรันครั้งนี้ไม่มีตารางของ AMRFinderPlus จึงแสดงข้อมูลชุดมาตรฐานจาก hAMRonization แทน",
  "amr.empty": "ไม่พบองค์ประกอบ AMR",
  "amr.col.element": "องค์ประกอบ",
  "amr.col.subclass": "กลุ่มย่อย",
  "amr.col.method": "วิธีตรวจ",
  "amr.col.closestRef": "ยีนอ้างอิงที่ใกล้ที่สุด",
  "amr.point.title": "การกลายพันธุ์บนโครโมโซม",
  "amr.point.lead":
    "จุดกลายพันธุ์ที่รายงานตามชนิดเชื้อที่ยืนยัน แยกจากยีนแบบ acquired",
  "amr.other.title": "องค์ประกอบที่ไม่ใช่ AMR",
  "amr.other.lead":
    "องค์ประกอบด้านความรุนแรงของเชื้อและการตอบสนองต่อความเครียด แสดงไว้ให้ครบถ้วน ไม่ใช่ส่วนของการตรวจ AMR",

  "abricate.title": "การสแกนยีนด้วย ARG-ANNOT",
  "abricate.lead":
    "ผลการเทียบด้วย BLASTN กับ ARG-ANNOT พร้อมตำแหน่งที่ ABRicate พบบนแต่ละ contig",
  "abricate.fallbackLead":
    "การรันครั้งนี้ไม่มีตารางของ ABRicate จึงแสดงข้อมูลชุดมาตรฐานจาก hAMRonization แทน",
  "abricate.col.position": "ตำแหน่ง",
  "abricate.note":
    "ARG-ANNOT มักไม่ระบุยาที่เกี่ยวข้อง จึงไม่แสดงรายการยาที่นี่ หากต้องการข้อมูลระดับกลุ่มยา ให้ดูรายงานของ ResFinder, CARD/RGI หรือ AMRFinderPlus",

  "deeparg.title": "กลุ่มยีนดื้อยาที่ทำนายได้",
  "deeparg.lead":
    "DeepARG ใช้โครงข่ายประสาทเทียม (โมเดล LS) วิเคราะห์ลำดับนิวคลีโอไทด์ที่ประกอบแล้ว ร่วมกับการเทียบฐานข้อมูล ผลที่ได้เป็นกลุ่มยีน เช่น KPC, TEM หรือ NDM และกลุ่มยากว้าง ๆ เช่น beta-lactam ไม่ใช่ชื่ออัลลีลอย่าง blaKPC-2",
  "deeparg.empty": "DeepARG ไม่ได้ทำนายผลจากลำดับนี้",
  "deeparg.col.family": "กลุ่มยีน",
  "deeparg.col.class": "กลุ่มยาที่ทำนาย",
  "deeparg.col.probability": "ความน่าจะเป็นจากโมเดล",
  "deeparg.col.identity": "ความเหมือนจากการเทียบลำดับ",
  "deeparg.aiOnly": "พบเฉพาะ AI — ควรตรวจสอบ",
  "deeparg.note":
    "DeepARG ไม่ถูกนับในความสอดคล้องของเครื่องมือฐานข้อมูล กลุ่มยีนที่ติดป้ายว่าพบเฉพาะ AI คือกลุ่มที่ DeepARG ทำนายไว้ แต่ ResFinder, CARD/RGI, AMRFinderPlus และ ABRicate ไม่พบ จึงควรตรวจสอบเพิ่ม",

  "agreement.summary": "ความสอดคล้องระหว่างเครื่องมือฐานข้อมูล ({count} กลุ่มยีน)",
  "agreement.lead":
    "จำนวนเครื่องมือฐานข้อมูลจากทั้งหมด {total} ตัวที่พบแต่ละกลุ่มยีน หลังผ่านเกณฑ์ความเหมือนและความครอบคลุม โดยไม่นับ DeepARG",
  "agreement.col.family": "กลุ่มยีน",
  "agreement.col.seenBy": "พบโดย",
  "agreement.col.tools": "เครื่องมือ",
  "agreement.col.genes": "ยีนที่รายงาน",
  "agreement.seenBy": "{n} จาก {total}",

  "samples.title": "ตัวอย่าง",
  "samples.lead":
    "เลือกตัวอย่างเพื่อดูรายงานยีนดื้อยาของแต่ละเครื่องมือ หรือเริ่มวิเคราะห์ใหม่",
  "samples.runDemo": "รันโหมดสาธิต",
  "samples.upload": "อัปโหลดลำดับพันธุกรรม",
  "samples.recent": "ตัวอย่างล่าสุด",
  "samples.empty": "ยังไม่มีผลที่บันทึกไว้",
  "samples.open": "เปิดรายงาน →",
};

export const TRANSLATIONS: Record<Lang, Record<TranslationKey, string>> = {
  en,
  th,
};
