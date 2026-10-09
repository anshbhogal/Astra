import pytest
from engine.regression.ast_change_analyzer import ASTChangeAnalyzer
from engine.regression.git_diff_parser import FileDiff, ChangedSymbol


def test_ast_change_analyzer_symbol_extraction():
    code = """
class UserService:
    def get_user(self, user_id: int):
        return {"id": user_id}

def top_level_helper():
    pass
"""
    analyzer = ASTChangeAnalyzer()
    symbols = analyzer.extract_symbols(code, "app/services/user.py")

    assert len(symbols) == 2
    sym_ids = [s.symbol_id for s in symbols]
    assert "python:app.services.user.UserService.get_user" in sym_ids
    assert "python:app.services.user.top_level_helper" in sym_ids


def test_ast_change_analyzer_diff_mapping():
    old_code = """
class UserService:
    def get_user(self, user_id: int):
        return {"id": user_id}
"""
    new_code = """
class UserService:
    def get_user(self, user_id: int, include_profile: bool = False):
        return {"id": user_id, "profile": include_profile}
"""
    fd = FileDiff(
        old_path="app/services/user.py",
        new_path="app/services/user.py",
        change_type="MODIFIED",
        added_lines=[3, 4],
        deleted_lines=[3],
    )
    analyzer = ASTChangeAnalyzer()
    changed_syms = analyzer.analyze_file_diff(fd, old_source=old_code, new_source=new_code)

    assert len(changed_syms) == 1
    assert changed_syms[0].symbol_id == "python:app.services.user.UserService.get_user"
    assert changed_syms[0].change_type == "SIGNATURE_CHANGED"
