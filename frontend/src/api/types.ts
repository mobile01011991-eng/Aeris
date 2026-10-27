export type ResistanceStatus =
  | "RESISTANT"
  | "AMBIGUOUS / SUSPECTED"
  | "SUSCEPTIBLE";

export interface ConsensusEntry {
  drug_class: string;
  status: ResistanceStatus;
  votes: string;
  supporting_tools: string[];
  detected_genes: string[];
  tool_count?: number;
}

export interface HarmonizedHit {
  gene_symbol?: string;
  gene_name?: string;
  drug_class?: string;
  antimicrobial_agent?: string;
  sequence_identity?: number | string;
  coverage_percentage?: number | string;
  reference_database_id?: string;
  reference_accession?: string;
  analysis_software_name?: string;
  tool_display_name?: string;
  normalized_drug_class?: string;
  passed_quality_filter?: boolean;
  input_sequence_id?: string;
  [key: string]: unknown;
}

export interface ToolRunStatus {
  tool_key: string;
  display_name: string;
  success: boolean;
  hit_count: number;
  filtered_hit_count: number;
  error?: string | null;
}

export interface OrganismInfo {
  declared?: string | null;
  detected?: string | null;
  confirmed?: string | null;
  decision?: string | null;
  match_status?: string | null;
  confidence?: number | null;
  amrfinder_organism?: string | null;
  resfinder_species?: string | null;
  warning?: string | null;
}

export interface OrganismOption {
  id: string;
  display_name: string;
  group: string;
  aliases: string[];
  amrfinder_organism?: string | null;
}

export type ToolKind = "database" | "ai";

/** One tool's own report: shared hAMRonized hits plus its native fields. */
export interface ToolReport {
  tool_key: string;
  display_name: string;
  kind: ToolKind;
  success: boolean;
  error?: string | null;
  hit_count: number;
  filtered_hit_count: number;
  hits: HarmonizedHit[];
  extras?: ToolExtras;
}

export type PointFinderStatus = "ran" | "skipped" | "failed";

export interface PointMutationRow {
  gene: string;
  mutation: string;
  nucleotide_change?: string;
  amino_acid_change?: string;
  antimicrobials?: string[];
  variation_type?: string;
  codon_position?: number | null;
  identity?: number | null;
  coverage?: number | null;
  contig?: string;
  pmids?: string[];
}

export interface ToolExtras {
  demo?: boolean;
  phenotypes?: ResFinderPhenotypeRow[];
  point_mutations?: PointMutationRow[];
  pointfinder_status?: PointFinderStatus;
  pointfinder_species?: string | null;
  pointfinder_reason?: string;
  hits?: RgiRow[] | AbricateRow[];
  amr?: AmrFinderRow[];
  point?: AmrFinderRow[];
  other?: AmrFinderRow[];
  predictions?: DeepArgRow[];
  source_file?: string;
}

export interface ResFinderPhenotypeRow {
  antimicrobial: string;
  drug_class: string;
  phenotype: string;
  match: string;
  genetic_background: string;
}

export interface RgiRow {
  contig: string;
  start?: string;
  stop?: string;
  orientation?: string;
  cut_off: string;
  best_hit_aro: string;
  aro?: string;
  model_type?: string;
  identity?: number | null;
  percent_length?: number | null;
  drug_class?: string;
  resistance_mechanism?: string;
  amr_gene_family?: string;
  antibiotic?: string;
  snps?: string;
}

export interface AmrFinderRow {
  contig: string;
  start?: string;
  stop?: string;
  strand?: string;
  element_symbol: string;
  element_name?: string;
  scope?: string;
  type?: string;
  subtype?: string;
  drug_class?: string;
  subclass?: string;
  method?: string;
  identity?: number | null;
  coverage?: number | null;
  accession?: string;
  reference_name?: string;
}

export interface AbricateRow {
  gene: string;
  gene_display: string;
  contig: string;
  start?: string;
  end?: string;
  strand?: string;
  identity?: number | null;
  coverage?: number | null;
  coverage_range?: string;
  gaps?: string;
  database?: string;
  accession?: string;
  product?: string;
  resistance?: string;
}

export interface DeepArgRow {
  gene_family: string;
  predicted_class: string;
  probability?: number | null;
  identity?: number | null;
  contig: string;
  best_hit?: string;
}

export interface AMRResultPayload {
  sample_id: string;
  processed_at: string;
  consensus_summary: ConsensusEntry[];
  tool_breakdown: Record<string, HarmonizedHit[]>;
  tool_reports?: Record<string, ToolReport>;
  tool_status?: ToolRunStatus[];
  filter_thresholds?: {
    sequence_identity_min: number;
    coverage_percentage_min: number;
  };
  total_tools?: number;
  majority_vote_threshold?: number;
  resistant_count?: number;
  ambiguous_count?: number;
  susceptible_count?: number;
  organism?: OrganismInfo | null;
}

export interface ResultSummary {
  id: number;
  sample_id: string;
  processed_at: string | null;
  status_summary: string | null;
  resistant_classes: number;
  ambiguous_classes: number;
}

export const TOOL_OPTIONS = [
  { key: "abricate", label: "ABRicate (ARG-ANNOT)" },
  { key: "amrfinderplus", label: "AMRFinderPlus" },
  { key: "resfinder", label: "ResFinder" },
  { key: "rgi", label: "CARD / RGI" },
  { key: "deeparg", label: "DeepARG" },
] as const;
