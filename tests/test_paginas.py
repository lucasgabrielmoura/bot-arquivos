"""Testes para o módulo bot/ops/paginas.py."""

import pytest

from bot.ops import OpError
from bot.ops.paginas import parse_pages, parse_ranges


def test_parse_ranges_valid():
    assert parse_ranges("1-3, 5, 8-", 10) == [[0, 1, 2], [4], [7, 8, 9]]
    assert parse_ranges("-3", 5) == [[0, 1, 2]]
    assert parse_ranges("4-", 5) == [[3, 4]]
    assert parse_ranges("2", 5) == [[1]]
    assert parse_ranges(" 1 - 2 , 4 ", 5) == [[0, 1], [3]]
    assert parse_ranges("-", 3) == [[0, 1, 2]]


def test_parse_ranges_invalid():
    with pytest.raises(OpError):
        parse_ranges("", 5)
    with pytest.raises(OpError):
        parse_ranges("   ", 5)
    with pytest.raises(OpError):
        parse_ranges("1,,3", 5)
    with pytest.raises(OpError):
        parse_ranges("0", 5)
    with pytest.raises(OpError):
        parse_ranges("6", 5)
    with pytest.raises(OpError):
        parse_ranges("3-1", 5)
    with pytest.raises(OpError):
        parse_ranges("1-6", 5)
    with pytest.raises(OpError):
        parse_ranges("abc", 5)
    with pytest.raises(OpError):
        parse_ranges("1-2-3", 5)
    with pytest.raises(OpError):
        parse_ranges("1-2", 0)


def test_parse_pages_valid():
    assert parse_pages("3, 1, 2", 3) == [2, 0, 1]
    assert parse_pages("1, 1, 2", 3) == [0, 0, 1]
    assert parse_pages("1-2, 2", 3) == [0, 1, 1]
    assert parse_pages("1-3", 3) == [0, 1, 2]


def test_parse_pages_invalid():
    with pytest.raises(OpError):
        parse_pages("4", 3)
    with pytest.raises(OpError):
        parse_pages("invalid", 3)
