"""
Compatibility module for the design brief name ``amr_consensus_engine``.

Prefer importing ``AMRConsensusAnalyzer`` from ``backend.pipeline.consensus``.
"""

from .consensus import AMRConsensusAnalyzer, amr_consensus_engine

__all__ = ["AMRConsensusAnalyzer", "amr_consensus_engine"]
