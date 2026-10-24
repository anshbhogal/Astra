"""Tests for Phase 2 Task P2-2: Polyglot AST Parsers (JavaScript & TypeScript)."""

import pytest
from dataclasses import dataclass
from engine.analyzer.parsers.javascript import JavaScriptParser
from engine.analyzer.parsers.typescript import TypeScriptParser
from engine.analyzer.parsers import ParserRegistry


@dataclass
class DummySourceFile:
    path: str


SAMPLE_JS_CODE = """
// Express application sample
const express = require('express');
const router = express.Router();

function calculateTotal(items, discount = 0) {
    /** Calculates total sum with optional discount. */
    return items.reduce((acc, it) => acc + it.price, 0) - discount;
}

const findAccount = async (accountId) => {
    return await db.accounts.findOne({ id: accountId });
};

router.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    res.status(200).json({ token: 'abc' });
});
"""

SAMPLE_TS_CODE = """
import { Controller, Get, Post, Body, Param } from '@nestjs/common';

export async function processPayment(amount: number, currency: string = 'USD'): Promise<boolean> {
    /** Process transaction via payment gateway. */
    return true;
}

const formatAddress = (street: string, zipCode?: number): string => {
    return `${street}, ${zipCode || ''}`;
};

@Controller('users')
export class UsersController {
    @Get('/:id')
    async getUserById(@Param('id') id: string): Promise<UserDto> {
        return await this.userService.find(id);
    }

    @Post('/create')
    createUser(@Body() dto: CreateUserDto): void {
        this.userService.create(dto);
    }
}
"""


def test_javascript_parser_extracts_functions_and_routes():
    parser = JavaScriptParser()
    functions = parser.parse_file("server.js", SAMPLE_JS_CODE)

    assert len(functions) >= 4, f"Expected at least 4 functions, got {len(functions)}"

    # Check calculateTotal function declaration
    calc_func = next((f for f in functions if f.name == "calculateTotal"), None)
    assert calc_func is not None
    assert calc_func.is_async is False
    assert len(calc_func.parameters) == 2
    assert calc_func.parameters[0]["name"] == "items"
    assert calc_func.parameters[1]["name"] == "discount"

    # Check async arrow function
    account_func = next((f for f in functions if f.name == "findAccount"), None)
    assert account_func is not None
    assert account_func.is_async is True
    assert len(account_func.parameters) == 1
    assert account_func.parameters[0]["name"] == "accountId"

    # Check Express routes
    health_route = next((f for f in functions if "health" in f.name or any("health" in d for d in f.decorators)), None)
    assert health_route is not None
    assert any("router.get" in d or "get" in d.lower() for d in health_route.decorators)

    login_route = next((f for f in functions if "login" in f.name or any("login" in d for d in f.decorators)), None)
    assert login_route is not None
    assert login_route.is_async is True


def test_typescript_parser_extracts_typed_functions_and_decorators():
    parser = TypeScriptParser()
    functions = parser.parse_file("users.controller.ts", SAMPLE_TS_CODE)

    assert len(functions) >= 4, f"Expected at least 4 functions, got {len(functions)}"

    # Check processPayment typed function
    pay_func = next((f for f in functions if f.name == "processPayment"), None)
    assert pay_func is not None
    assert pay_func.is_async is True
    assert pay_func.return_type == "Promise<boolean>"
    assert len(pay_func.parameters) == 2
    assert pay_func.parameters[0]["name"] == "amount"
    assert pay_func.parameters[0]["type"] == "number"

    # Check formatAddress arrow function
    fmt_func = next((f for f in functions if f.name == "formatAddress"), None)
    assert fmt_func is not None
    assert fmt_func.return_type == "string"

    # Check class methods with decorators
    get_user = next((f for f in functions if f.name == "getUserById"), None)
    assert get_user is not None
    assert get_user.is_async is True
    assert any("@Get" in d for d in get_user.decorators)
    assert get_user.return_type == "Promise<UserDto>"


def test_parser_registry_polyglot_dispatch():
    registry = ParserRegistry()

    js_parser = registry.get_parser("JavaScript")
    assert isinstance(js_parser, JavaScriptParser)
    assert len(js_parser.parse_file("index.js", SAMPLE_JS_CODE)) >= 4

    ts_parser = registry.get_parser("TypeScript")
    assert isinstance(ts_parser, TypeScriptParser)
    assert len(ts_parser.parse_file("index.ts", SAMPLE_TS_CODE)) >= 4
