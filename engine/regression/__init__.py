"""ASTRA Phase 8: Selective Regression Engine & Impact Analysis.
"""

from engine.regression.git_diff_parser import GitDiffParser, FileDiff, ChangedSymbol
from engine.regression.ast_change_analyzer import ASTChangeAnalyzer, SymbolIdentity
from engine.regression.impact_analyzer import PKGImpactAnalyzer, ImpactedEndpoint
from engine.regression.test_impact_mapper import TestImpactMapper
from engine.regression.safety_gate import SafetyGate, UnknownImpactCategory
from engine.regression.selective_selector import SelectiveSelector, SelectionResult
from engine.regression.evaluators import RegressionOracleEvaluator

__all__ = [
    "GitDiffParser",
    "FileDiff",
    "ChangedSymbol",
    "ASTChangeAnalyzer",
    "SymbolIdentity",
    "PKGImpactAnalyzer",
    "ImpactedEndpoint",
    "TestImpactMapper",
    "SafetyGate",
    "UnknownImpactCategory",
    "SelectiveSelector",
    "SelectionResult",
    "RegressionOracleEvaluator",
]
