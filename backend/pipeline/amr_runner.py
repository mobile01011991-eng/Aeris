"""
CLI / Docker wrappers for five AMR tools + hAMRonize standardization.

Tools:
  1. ResFinder
  2. CARD / RGI
  3. NCBI AMRFinderPlus
  4. ARG-ANNOT via ABRicate
  5. DeepARG

Raw tool parsers are NOT implemented here — outputs are converted with the
``hamronize`` CLI (pha4ge/hAMRonization).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .tool_reports import POINTFINDER_CONTEXT_FILE

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tools.yaml"

TOOL_KEYS = ("resfinder", "rgi", "amrfinderplus", "abricate", "deeparg")

# Paths inside genomicepidemiology/resfinder
RESFINDER_DB_PATH = "/databases/resfinder_db"
POINTFINDER_DB_PATH = "/databases/pointfinder_db"


def _resolve_hamronize_bin(preferred: str = "hamronize") -> str:
    """Locate hamronize even when Scripts/ is not on PATH (common on Windows)."""
    found = shutil.which(preferred)
    if found:
        return found
    scripts = Path(sys.executable).resolve().parent / "Scripts" / "hamronize.exe"
    if scripts.exists():
        return str(scripts)
    appdata = Path(os.environ.get("APPDATA", "")) / "Python"
    if appdata.exists():
        matches = sorted(appdata.glob("Python*/Scripts/hamronize.exe"))
        if matches:
            return str(matches[-1])
    return preferred


def _docker_path(path: Path) -> str:
    """Docker Desktop on Windows accepts forward-slash absolute paths."""
    return str(path.resolve()).replace("\\", "/")


_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def safe_path_name(name: str, fallback: str = "sample") -> str:
    """
    Shell-safe path segment.

    ResFinder, RGI and ABRicate build their own shell commands inside the
    container, so spaces or parentheses in a path break them.
    """
    cleaned = _UNSAFE_NAME_CHARS.sub("_", str(name)).strip("._-")
    return cleaned or fallback


def safe_file_name(filename: str, fallback: str = "input.fasta") -> str:
    """Sanitize a sequence filename while keeping its (compound) extension."""
    name = Path(str(filename).replace("\\", "/")).name
    if not name:
        return fallback

    gz_suffix = ""
    if name.lower().endswith(".gz"):
        gz_suffix = name[-3:]
        name = name[:-3]

    inner = Path(name)
    ext = inner.suffix
    base = inner.stem if ext else inner.name
    return f"{safe_path_name(base, 'input')}{ext}{gz_suffix}"


@dataclass
class ToolRunResult:
    tool_key: str
    display_name: str
    success: bool
    raw_output: Optional[Path] = None
    hamronized_json: Optional[Path] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


@dataclass
class PipelineRunResult:
    sample_id: str
    work_dir: Path
    input_file: Path
    tools: dict[str, ToolRunResult] = field(default_factory=dict)

    @property
    def hamronized_reports(self) -> dict[str, Path]:
        return {
            k: v.hamronized_json
            for k, v in self.tools.items()
            if v.success and v.hamronized_json and v.hamronized_json.exists()
        }


class AMRToolRunner:
    """Execute AMR containers (or local binaries) and hamronize their reports."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        use_docker: Optional[bool] = None,
        dry_run: bool = False,
        hamronize_bin: Optional[str] = None,
        docker_bin: str = "docker",
    ) -> None:
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        docker_cfg = self.config.get("docker", {})
        self.use_docker = (
            bool(docker_cfg.get("enabled", True)) if use_docker is None else use_docker
        )
        self.dry_run = dry_run
        self.hamronize_bin = hamronize_bin or _resolve_hamronize_bin()
        self.docker_bin = docker_bin
        self.tools_cfg: dict[str, Any] = self.config.get("tools", {})

    def run_all(
        self,
        input_path: Path | str,
        sample_id: Optional[str] = None,
        work_dir: Optional[Path | str] = None,
        tools: Optional[list[str]] = None,
        *,
        on_tool_start: Optional[Any] = None,
        on_tool_done: Optional[Any] = None,
        amrfinder_organism: Optional[str] = None,
        resfinder_species: Optional[str] = None,
    ) -> PipelineRunResult:
        input_path = Path(input_path).resolve()
        self._validate_input(input_path)

        sample_id = sample_id or input_path.stem
        base_work = Path(work_dir) if work_dir else Path(self.config.get("work_dir", "./work"))
        run_dir = (base_work / safe_path_name(sample_id) / uuid.uuid4().hex[:8]).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)

        selected = tools or [
            k
            for k in TOOL_KEYS
            if self.tools_cfg.get(k, {}).get("enabled", True) is not False
        ]
        result = PipelineRunResult(
            sample_id=sample_id,
            work_dir=run_dir,
            input_file=input_path,
        )
        self._amrfinder_organism = amrfinder_organism
        self._resfinder_species = resfinder_species

        runners = {
            "resfinder": self.run_resfinder,
            "rgi": self.run_rgi,
            "amrfinderplus": self.run_amrfinderplus,
            "abricate": self.run_abricate,
            "deeparg": self.run_deeparg,
        }

        for key in selected:
            if key not in runners:
                raise ValueError(f"Unknown tool key: {key}. Expected one of {TOOL_KEYS}")
            tool_dir = run_dir / key
            tool_dir.mkdir(parents=True, exist_ok=True)
            if on_tool_start:
                on_tool_start(key)
            try:
                result.tools[key] = runners[key](input_path, tool_dir)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool %s failed", key)
                cfg = self.tools_cfg.get(key, {})
                result.tools[key] = ToolRunResult(
                    tool_key=key,
                    display_name=cfg.get("display_name", key),
                    success=False,
                    error=str(exc),
                )
            if on_tool_done:
                on_tool_done(key, result.tools[key])

        return result

    def hamronize_report(
        self,
        tool_key: str,
        raw_report: Path,
        output_json: Path,
        *,
        analysis_software_version: Optional[str] = None,
        reference_database_version: Optional[str] = None,
        input_file_name: Optional[str] = None,
    ) -> Path:
        cfg = self.tools_cfg.get(tool_key, {})
        hamronize_name = cfg.get("hamronize_name", tool_key)
        asv = analysis_software_version or cfg.get("analysis_software_version", "unknown")
        rdv = reference_database_version or cfg.get("reference_database_version", "unknown")

        cmd = [
            self.hamronize_bin,
            hamronize_name,
            str(raw_report),
            "--format",
            "json",
            "--output",
            str(output_json),
        ]

        # Tool CLIs differ: abricate needs versions; resfinder often does not.
        if tool_key != "resfinder":
            cmd.extend(["--analysis_software_version", str(asv)])
            cmd.extend(["--reference_database_version", str(rdv)])

        if cfg.get("hamronize_input_file_name") and input_file_name:
            cmd.extend(["--input_file_name", input_file_name])

        self._run_command(cmd, cwd=output_json.parent)
        if not self.dry_run and not output_json.exists():
            raise FileNotFoundError(f"hamronize did not produce {output_json}")
        return output_json

    # ------------------------------------------------------------------
    # Per-tool runners
    # ------------------------------------------------------------------

    def resfinder_commands(
        self,
        input_path: Path,
        out_dir: Path,
        raw: Path,
        point_species: Optional[str] = None,
    ) -> tuple[list[str], list[str]]:
        """
        Local command and Docker inner command for ResFinder.

        ``-acq`` always runs. When ``point_species`` is a PointFinder db_prefix,
        ``-c`` adds chromosomal point mutations for that species;
        ``--ignore_missing_species`` keeps acquired results even if the image
        turns out to have no panel for it.
        """
        local_cmd = [
            "python",
            "-m",
            "resfinder",
            "-ifa",
            str(input_path),
            "-o",
            str(out_dir),
            "-j",
            str(raw),
            "-acq",
        ]
        # Image entrypoint is already ``python -m resfinder``.
        docker_inner = [
            "-ifa",
            f"/data/input/{input_path.name}",
            "-o",
            "/data/out",
            "-j",
            f"/data/out/{raw.name}",
            "-acq",
            "-db_res",
            RESFINDER_DB_PATH,
        ]

        if point_species:
            point_flags = ["-c", "-s", point_species, "--ignore_missing_species"]
            local_cmd.extend(point_flags)
            docker_inner.extend([*point_flags, "-db_point", POINTFINDER_DB_PATH])

        return local_cmd, docker_inner

    @staticmethod
    def _write_pointfinder_context(
        out_dir: Path,
        status: str,
        species: Optional[str],
        reason: str = "",
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / POINTFINDER_CONTEXT_FILE).write_text(
            json.dumps({"status": status, "species": species, "reason": reason}),
            encoding="utf-8",
        )

    def run_resfinder(self, input_path: Path, out_dir: Path) -> ToolRunResult:
        key = "resfinder"
        cfg = self.tools_cfg[key]
        # ResFinder writes JSON; hamronize expects the ResFinder JSON report.
        raw = out_dir / "data_resfinder.json"
        ham = out_dir / "hamronized.json"
        species = getattr(self, "_resfinder_species", None)

        def execute(point_species: Optional[str]) -> ToolRunResult:
            local_cmd, docker_inner = self.resfinder_commands(
                input_path, out_dir, raw, point_species
            )
            docker_cmd = self._docker_cmd(
                cfg["image"], out_dir, input_path, docker_inner
            )
            return self._execute_tool(
                key, cfg, raw, ham, local_cmd, docker_cmd, input_path
            )

        if not species:
            self._write_pointfinder_context(
                out_dir,
                "skipped",
                None,
                "No PointFinder database for the confirmed organism",
            )
            return execute(None)

        result = execute(species)
        if result.success:
            self._write_pointfinder_context(out_dir, "ran", species)
            return result

        # Acquired genes must still be reported, so retry without PointFinder.
        logger.warning(
            "ResFinder with PointFinder (%s) failed; retrying acquired-only: %s",
            species,
            result.error,
        )
        for stale in out_dir.glob("PointFinder_*"):
            stale.unlink(missing_ok=True)

        fallback = execute(None)
        self._write_pointfinder_context(
            out_dir,
            "failed",
            species,
            f"PointFinder run failed, acquired genes re-run without it: {result.error}",
        )
        return fallback

    def run_rgi(self, input_path: Path, out_dir: Path) -> ToolRunResult:
        key = "rgi"
        cfg = self.tools_cfg[key]
        prefix = out_dir / "rgi"
        raw = out_dir / "rgi.txt"
        ham = out_dir / "hamronized.json"
        card_db = Path(
            cfg.get("card_db_path")
            or os.environ.get("CARD_DB_PATH")
            or (Path(__file__).resolve().parents[2] / "data" / "card_db")
        ).resolve()

        local_cmd = [
            "rgi",
            "main",
            "--input_sequence",
            str(input_path),
            "--output_file",
            str(prefix),
            "--input_type",
            "contig",
            "--local",
            "--clean",
        ]
        docker_cmd = self._docker_cmd(
            cfg["image"],
            out_dir,
            input_path,
            [
                "rgi",
                "main",
                "--input_sequence",
                f"/data/input/{input_path.name}",
                "--output_file",
                "/data/out/rgi",
                "--input_type",
                "contig",
                "--local",
                "--clean",
            ],
            extra_volumes=[(card_db, "/card")],
            workdir="/card",
        )
        return self._execute_tool(key, cfg, raw, ham, local_cmd, docker_cmd, input_path)

    def run_amrfinderplus(self, input_path: Path, out_dir: Path) -> ToolRunResult:
        key = "amrfinderplus"
        cfg = self.tools_cfg[key]
        raw = out_dir / "amrfinder.tsv"
        ham = out_dir / "hamronized.json"
        organism = getattr(self, "_amrfinder_organism", None)

        local_cmd = ["amrfinder", "-n", str(input_path), "-o", str(raw)]
        docker_inner = [
            "amrfinder",
            "-n",
            f"/data/input/{input_path.name}",
            "-o",
            f"/data/out/{raw.name}",
        ]
        if organism:
            local_cmd.extend(["-O", str(organism)])
            docker_inner.extend(["-O", str(organism)])

        docker_cmd = self._docker_cmd(
            cfg["image"],
            out_dir,
            input_path,
            docker_inner,
        )
        return self._execute_tool(key, cfg, raw, ham, local_cmd, docker_cmd, input_path)

    def run_abricate(self, input_path: Path, out_dir: Path) -> ToolRunResult:
        """ABRicate with ARG-ANNOT — write TSV inside the container (no BOM)."""
        key = "abricate"
        cfg = self.tools_cfg[key]
        raw = out_dir / "abricate_argannot.tsv"
        ham = out_dir / "hamronized.json"

        local_cmd = ["abricate", "--db", "argannot", str(input_path)]
        # Redirect inside container to avoid Windows BOM / encoding issues.
        docker_cmd = self._docker_cmd(
            cfg["image"],
            out_dir,
            input_path,
            [
                "bash",
                "-lc",
                "abricate --db argannot {} > {}".format(
                    shlex.quote(f"/data/input/{input_path.name}"),
                    shlex.quote(f"/data/out/{raw.name}"),
                ),
            ],
        )
        return self._execute_tool(
            key,
            cfg,
            raw,
            ham,
            local_cmd,
            docker_cmd,
            input_path,
            capture_stdout_to=raw if not self.use_docker else None,
        )

    def run_deeparg(self, input_path: Path, out_dir: Path) -> ToolRunResult:
        """
        Modern DeepARG (gaarangoa/deeparg) via Docker.

        Writes ``deeparg.mapping.ARG``, converts to legacy columns for
        ``hamronize deeparg``, then returns the hAMRonized JSON.
        """
        from .deeparg_convert import convert_deeparg_report

        key = "deeparg"
        cfg = self.tools_cfg[key]
        raw_modern = out_dir / "deeparg.mapping.ARG"
        raw_legacy = out_dir / "deeparg.legacy.mapping.ARG"
        ham = out_dir / "hamronized.json"
        hf_cache = Path(
            cfg.get("hf_cache_path")
            or os.environ.get("DEEPARG_HF_CACHE")
            or (Path(__file__).resolve().parents[2] / "data" / "hf_cache")
        ).resolve()
        hf_cache.mkdir(parents=True, exist_ok=True)

        device = str(cfg.get("hf_device", "cpu"))
        gpus = cfg.get("gpus")
        if gpus in (None, "") and device.lower() not in {"cpu", ""}:
            gpus = "all"

        local_cmd = [
            "deeparg",
            "predict",
            "--model",
            str(cfg.get("model", "LS")),
            "--type",
            "nucl",
            "-i",
            str(input_path),
            "-o",
            str(out_dir / "deeparg"),
            "--hf-device",
            device,
        ]
        docker_cmd = self._docker_cmd(
            cfg["image"],
            out_dir,
            input_path,
            [
                "predict",
                "--model",
                str(cfg.get("model", "LS")),
                "--type",
                "nucl",
                "-i",
                f"/data/input/{input_path.name}",
                "-o",
                "/data/out/deeparg",
                "--hf-device",
                device,
            ],
            extra_volumes=[(hf_cache, "/root/.cache/huggingface")],
            env_vars={"HF_FORCE_IPV4": "1"},
            gpus=None if device.lower() in {"cpu", ""} else str(gpus or "all"),
        )

        display = cfg.get("display_name", key)
        cmd = docker_cmd if self.use_docker else local_cmd
        try:
            completed = self._run_command(cmd, cwd=out_dir)
            matches = sorted(out_dir.glob("*.mapping.ARG"))
            # Prefer the primary ARG file (not potential.ARG)
            primary = [m for m in matches if "potential" not in m.name.lower()]
            src = primary[0] if primary else (matches[0] if matches else None)
            if src is None:
                raise FileNotFoundError(
                    f"{display} did not produce *.mapping.ARG in {out_dir}"
                )
            convert_deeparg_report(src, raw_legacy)
            self.hamronize_report(
                key,
                raw_legacy,
                ham,
                input_file_name=input_path.name,
            )
            return ToolRunResult(
                tool_key=key,
                display_name=display,
                success=True,
                raw_output=src,
                hamronized_json=ham,
                stdout=completed.stdout if completed else "",
                stderr=completed.stderr if completed else "",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("%s failed: %s", display, exc)
            return ToolRunResult(
                tool_key=key,
                display_name=display,
                success=False,
                raw_output=raw_modern if raw_modern.exists() else None,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------

    def _execute_tool(
        self,
        tool_key: str,
        cfg: dict[str, Any],
        raw_path: Path,
        ham_path: Path,
        local_cmd: list[str],
        docker_cmd: list[str],
        input_path: Path,
        capture_stdout_to: Optional[Path] = None,
    ) -> ToolRunResult:
        display = cfg.get("display_name", tool_key)
        cmd = docker_cmd if self.use_docker else local_cmd
        try:
            completed = self._run_command(
                cmd,
                cwd=raw_path.parent,
                capture_stdout_to=capture_stdout_to,
            )
            if not self.dry_run and not raw_path.exists():
                raise FileNotFoundError(
                    f"{display} did not produce expected output: {raw_path}"
                )

            if self.dry_run:
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                if not raw_path.exists():
                    raw_path.write_text("", encoding="utf-8")

            self.hamronize_report(
                tool_key,
                raw_path,
                ham_path,
                input_file_name=input_path.name,
            )
            if self.dry_run and not ham_path.exists():
                ham_path.write_text("[]", encoding="utf-8")

            return ToolRunResult(
                tool_key=tool_key,
                display_name=display,
                success=True,
                raw_output=raw_path,
                hamronized_json=ham_path,
                stdout=completed.stdout if completed else "",
                stderr=completed.stderr if completed else "",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("%s failed: %s", display, exc)
            return ToolRunResult(
                tool_key=tool_key,
                display_name=display,
                success=False,
                raw_output=raw_path if raw_path.exists() else None,
                error=str(exc),
            )

    def _docker_cmd(
        self,
        image: str,
        out_dir: Path,
        input_path: Path,
        inner_cmd: list[str],
        capture_stdout_to: Optional[Path] = None,
        extra_volumes: Optional[list[tuple[Path, str]]] = None,
        workdir: Optional[str] = None,
        env_vars: Optional[dict[str, str]] = None,
        gpus: Optional[str] = None,
    ) -> list[str]:
        out_dir = out_dir.resolve()
        input_dir = input_path.parent.resolve()
        _ = capture_stdout_to
        cmd = [
            self.docker_bin,
            "run",
            "--rm",
        ]
        if gpus:
            cmd.extend(["--gpus", str(gpus)])
        cmd.extend(
            [
                "-v",
                f"{_docker_path(input_dir)}:/data/input:ro",
                "-v",
                f"{_docker_path(out_dir)}:/data/out",
            ]
        )
        for host_path, container_path in extra_volumes or []:
            cmd.extend(["-v", f"{_docker_path(host_path)}:{container_path}"])
        for env_key, env_val in (env_vars or {}).items():
            cmd.extend(["-e", f"{env_key}={env_val}"])
        if workdir:
            cmd.extend(["-w", workdir])
        cmd.append(image)
        cmd.extend(inner_cmd)
        return cmd

    def _run_command(
        self,
        cmd: list[str],
        cwd: Optional[Path] = None,
        capture_stdout_to: Optional[Path] = None,
    ) -> Optional[subprocess.CompletedProcess[str]]:
        logger.info("Running: %s", " ".join(cmd))
        if self.dry_run:
            logger.info("[dry-run] skipped execution")
            return None

        if capture_stdout_to is not None:
            # utf-8 without BOM — critical for hamronize TSV parsers
            with capture_stdout_to.open("w", encoding="utf-8", newline="\n") as fh:
                proc = subprocess.run(
                    cmd,
                    cwd=str(cwd) if cwd else None,
                    stdout=fh,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}"
                )
            return subprocess.CompletedProcess(
                proc.args, proc.returncode, stdout="", stderr=proc.stderr or ""
            )

        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}"
            )
        return proc

    @staticmethod
    def _validate_input(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Input sequence file not found: {path}")
        suffix = path.suffix.lower()
        allowed = {".fasta", ".fastq", ".fa", ".fq", ".fna", ".ffa", ".gz"}
        if suffix == ".gz":
            inner = Path(path.stem).suffix.lower()
            if inner not in {".fasta", ".fastq", ".fa", ".fq", ".fna"}:
                raise ValueError(f"Unsupported compressed input type: {path.name}")
        elif suffix not in allowed:
            raise ValueError(
                f"Unsupported input type '{suffix}'. Expected .fasta or .fastq."
            )

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.warning("Config %s missing; using empty defaults", path)
            return {"tools": {}, "docker": {"enabled": True}}
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    @staticmethod
    def which_or_none(binary: str) -> Optional[str]:
        return shutil.which(binary)
