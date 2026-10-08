"""
Unit tests for Phase 6 Stack Trace & Log Parsers
"""

import pytest
from engine.analysis.parsers.python_parser import PythonStackTraceParser
from engine.analysis.parsers.nodejs_parser import NodejsStackTraceParser
from engine.analysis.parsers.java_parser import JavaStackTraceParser
from engine.analysis.parsers.sql_parser import SqlErrorParser


def test_python_traceback_parser():
    raw_trace = """Traceback (most recent call last):
  File "/app/services/orders.py", line 143, in calculate_total
    discount = payload['discount']
KeyError: 'discount'"""
    
    parser = PythonStackTraceParser()
    parsed = parser.parse(raw_trace)
    
    assert parsed is not None
    assert parsed.exception_type == "KeyError"
    assert parsed.message == "'discount'"
    assert len(parsed.frames) == 1
    assert parsed.frames[0].file_path == "/app/services/orders.py"
    assert parsed.frames[0].line_number == 143
    assert parsed.frames[0].function_name == "calculate_total"
    assert parsed.frames[0].code_snippet == "discount = payload['discount']"


def test_nodejs_stack_parser():
    raw_trace = """TypeError: Cannot read property 'discount' of undefined
    at calculateDiscount (/app/services/orders.js:91:15)
    at /app/routes/orders.js:42:10"""

    parser = NodejsStackTraceParser()
    parsed = parser.parse(raw_trace)

    assert parsed is not None
    assert parsed.exception_type == "TypeError"
    assert "Cannot read property" in parsed.message
    assert len(parsed.frames) == 2
    assert parsed.frames[0].file_path == "/app/services/orders.js"
    assert parsed.frames[0].line_number == 91
    assert parsed.frames[0].function_name == "calculateDiscount"


def test_java_stack_parser():
    raw_trace = """java.lang.NullPointerException: Cannot invoke "String.length()" because "str" is null
    at com.example.service.OrderService.calculateTotal(OrderService.java:91)
    at com.example.controller.OrderController.createOrder(OrderController.java:42)"""

    parser = JavaStackTraceParser()
    parsed = parser.parse(raw_trace)

    assert parsed is not None
    assert parsed.exception_type == "java.lang.NullPointerException"
    assert len(parsed.frames) == 2
    assert parsed.frames[0].line_number == 91
    assert parsed.frames[0].file_path == "OrderService.java"


def test_sql_parser_sqlstate():
    raw_trace = 'ERROR: duplicate key value violates unique constraint "users_email_key" (SQLSTATE 23505)'

    parser = SqlErrorParser()
    parsed = parser.parse(raw_trace)

    assert parsed is not None
    assert parsed.sql_state == "23505"
    assert parsed.exception_type == "UniqueConstraintViolation"
