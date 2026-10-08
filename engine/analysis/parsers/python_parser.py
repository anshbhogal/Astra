"""
ASTRA Engine - Phase 6 Python Stack Trace Parser
"""

import re
from typing import Optional, List
from engine.analysis.models import ParsedException, StackFrame
from engine.analysis.parsers.base import BaseStackTraceParser


class PythonStackTraceParser(BaseStackTraceParser):
    """Parses standard Python traceback output into normalized ParsedException."""

    # Matches: File "...", line 123, in func_name
    FRAME_REGEX = re.compile(
        r'File\s+["\'](?P<file>[^"\']+)["\'],\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>\w+))?'
    )

    # Matches exception line: ZeroDivisionError: division by zero
    EXCEPTION_REGEX = re.compile(
        r'^(?P<type>[A-Za-z_][A-Za-z0-9_\.]*(?:Error|Exception|Fault|Warning|Exit|Interrupt|Violation|Mismatch|Reject)?):\s*(?P<msg>.*)$'
    )

    def parse(self, raw_trace: str) -> Optional[ParsedException]:
        if not raw_trace or "Traceback" not in raw_trace and "File " not in raw_trace:
            # Check if it's a single line exception like "KeyError: 'discount'"
            lines = [l.strip() for l in raw_trace.strip().splitlines() if l.strip()]
            if lines and ":" in lines[-1]:
                exc_match = self.EXCEPTION_REGEX.match(lines[-1])
                if exc_match:
                    return ParsedException(
                        exception_type=exc_match.group("type"),
                        message=exc_match.group("msg").strip(),
                        frames=[],
                        language="python",
                        raw_trace_hash=self.compute_hash(raw_trace),
                    )
            return None

        lines = raw_trace.strip().splitlines()
        frames: List[StackFrame] = []
        exception_type = "PythonException"
        exception_message = raw_trace.strip()

        idx = 0
        while idx < len(lines):
            line = lines[idx]
            frame_match = self.FRAME_REGEX.search(line)
            if frame_match:
                file_path = frame_match.group("file")
                line_number = int(frame_match.group("line"))
                function_name = frame_match.group("func") or "<module>"

                # Check next line for code snippet
                code_snippet = None
                if idx + 1 < len(lines) and not self.FRAME_REGEX.search(lines[idx + 1]) and not lines[idx + 1].strip().startswith("Traceback"):
                    snippet_candidate = lines[idx + 1].strip()
                    if snippet_candidate and not self.EXCEPTION_REGEX.match(snippet_candidate):
                        code_snippet = snippet_candidate

                is_in_project = not ("site-packages" in file_path or "dist-packages" in file_path or "lib/python" in file_path)

                frames.append(
                    StackFrame(
                        file_path=file_path,
                        line_number=line_number,
                        function_name=function_name,
                        code_snippet=code_snippet,
                        is_in_project=is_in_project,
                    )
                )
            else:
                exc_match = self.EXCEPTION_REGEX.match(line.strip())
                if exc_match:
                    exception_type = exc_match.group("type")
                    exception_message = exc_match.group("msg").strip()
            idx += 1

        return ParsedException(
            exception_type=exception_type,
            message=exception_message,
            frames=frames,
            language="python",
            raw_trace_hash=self.compute_hash(raw_trace),
        )
