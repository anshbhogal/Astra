import pytest
from engine.regression.git_diff_parser import GitDiffParser


def test_git_diff_parser_rename_and_lines():
    diff_text = """diff --git a/backend/app/services/old_user.py b/backend/app/services/user_service.py
similarity index 90%
rename from backend/app/services/old_user.py
rename to backend/app/services/user_service.py
@@ -10,4 +10,6 @@ class UserService:
-    def old_method(self):
-        pass
+    def get_user(self, user_id: int):
+        return {"id": user_id}
+    def update_user(self, user_id: int):
+        pass
"""

    parser = GitDiffParser()
    file_diffs = parser.parse_diff(diff_text)

    assert len(file_diffs) == 1
    fd = file_diffs[0]
    assert fd.old_path == "backend/app/services/old_user.py"
    assert fd.new_path == "backend/app/services/user_service.py"
    assert fd.change_type == "RENAMED"
    assert fd.rename_similarity == 0.90
    assert len(fd.added_lines) > 0
    assert len(fd.deleted_lines) > 0
