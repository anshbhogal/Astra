"""
ASTRA Engine - Phase 6 Node.js / V8 Stack Trace Parser
"""

import re
from typing import Optional, List
from engine.analysis.models import ParsedException, StackFrame
from engine.analysis.parsers.base import BaseStackTraceParser


class NodejsStackTraceParser(BaseStackTraceParser):
    """Parses Node.js / V8 stack trace output into normalized ParsedException."""

    # Matches: TypeError: Cannot read property 'x' of undefined
    EXCEPTION_HEADER_REGEX = re.compile(
        r'^(?P<type>[A-Za-z_][A-Za-z0-9_\.]*Error):\s*(?P<msg>.*)$'
    )

    # Matches frame formats:
    #   at calculateDiscount (/app/services/orders.js:91:15)
    #   at /app/routes/orders.js:42:10
    #   at async Promise.all (index 0)
    FRAME_REGEX = re.compile(
        r'^\s*at\s+(?:(?P<func>[^\(]+)\s+\()?(?P<file>[^:\s\)]+):(?P<line>\d+):(?P<col>\d+)\)?'
    )

    def parse(self, raw_trace: str) -> Optional[ParsedException]:
        if not raw_trace or ("Error" not in raw_trace and "at " not in raw_trace):
            return None

        lines = [l.strip() for l in raw_trace.strip().splitlines() if l.strip()]
        if not lines:
            return None

        exception_type = "Error"
        exception_message = raw_trace.strip()

        header_match = self.EXCEPTION_HEADER_REGEX.match(lines[0])
        if header_match:
            exception_type = header_match.group("type")
            exception_message = header_match.group("msg").strip()

        frames: List[StackFrame] = []
        for line in lines:
            frame_match = self.FRAME_REGEX.match(line)
            if frame_match:
                file_path = frame_match.group("file")
                line_number = int(frame_match.group("line"))
                func_name = (frame_match.group("func") or "<anonymous>").strip()

                is_in_project = not ("node_modules" in file_path or "internal/" in file_path)

                frames.append(
                    StackFrame(
                        file_path=file_path,
                        line_number=line_number,
                        function_name=func_name,
                        is_in_project=is_in_project,
                    )
                )

        if not frames and not header_match:
            return None

        return ParsedException(
            exception_type=exception_type,
            message=exception_message,
            frames=frames,
            language="nodejs",
            raw_trace_hash=self.compute_hash(raw_trace),
        )
