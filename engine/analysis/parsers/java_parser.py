"""
ASTRA Engine - Phase 6 Java JVM Stack Trace Parser
"""

import re
from typing import Optional, List
from engine.analysis.models import ParsedException, StackFrame
from engine.analysis.parsers.base import BaseStackTraceParser


class JavaStackTraceParser(BaseStackTraceParser):
    """Parses Java JVM stack trace output into normalized ParsedException."""

    # Matches: java.lang.NullPointerException: Cannot invoke ...
    EXCEPTION_HEADER_REGEX = re.compile(
        r'^(?P<type>[a-zA-Z0-9_\.]+(?:Exception|Error|Throwable)):\s*(?P<msg>.*)$'
    )

    # Matches: at com.example.service.OrderService.calculateTotal(OrderService.java:91)
    FRAME_REGEX = re.compile(
        r'^\s*at\s+(?P<classfunc>[a-zA-Z0-9_\.\$<>]+\.[a-zA-Z0-9_\$<>]+)\((?P<file>[^:]+):(?P<line>\d+)\)'
    )

    def parse(self, raw_trace: str) -> Optional[ParsedException]:
        if not raw_trace or ("Exception" not in raw_trace and "Error" not in raw_trace and "at " not in raw_trace):
            return None

        lines = [l.strip() for l in raw_trace.strip().splitlines() if l.strip()]
        if not lines:
            return None

        exception_type = "JavaException"
        exception_message = raw_trace.strip()

        header_match = self.EXCEPTION_HEADER_REGEX.match(lines[0])
        if header_match:
            exception_type = header_match.group("type")
            exception_message = header_match.group("msg").strip()

        frames: List[StackFrame] = []
        for line in lines:
            frame_match = self.FRAME_REGEX.match(line)
            if frame_match:
                class_func = frame_match.group("classfunc")
                file_name = frame_match.group("file")
                line_number = int(frame_match.group("line"))

                is_in_project = not (
                    class_func.startswith("java.")
                    or class_func.startswith("javax.")
                    or class_func.startswith("org.springframework.")
                    or class_func.startswith("jdk.")
                )

                frames.append(
                    StackFrame(
                        file_path=file_name,
                        line_number=line_number,
                        function_name=class_func,
                        is_in_project=is_in_project,
                    )
                )

        if not frames and not header_match:
            return None

        return ParsedException(
            exception_type=exception_type,
            message=exception_message,
            frames=frames,
            language="java",
            raw_trace_hash=self.compute_hash(raw_trace),
        )
