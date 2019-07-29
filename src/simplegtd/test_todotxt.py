#!/usr/bin/python3

import unittest
from simplegtd.todotxt import TodoTxt

class TodoTxtTest(unittest.TestCase):

    def test_load_from_lines(self):
        t = TodoTxt()
        t._load_from_lines(['a\n', 'b\n', 'c'])
        assert t[0][0] == "a"
        assert t[1][0] == "b"
        assert t[2][0] == "c"
        assert t.last_line_cr is False

    def test_reload_from_lines(self):
        t = TodoTxt()
        t._load_from_lines(['a\n', 'b\n', 'c'])
        t._load_from_lines(['b\n', 'c'])
        assert t[0][0] == "b"
        assert t[1][0] == "c"
        assert len(t) == 2
        assert t.last_line_cr is False

    def test_replace_from_lines(self):
        t = TodoTxt()
        t._load_from_lines(['a\n', 'b\n', 'c'])
        t._load_from_lines(['z\n', 'y\n', 'b\n', 'c'])
        assert t[0][0] == "z", t[0][0]
        assert t[1][0] == "y"
        assert t[2][0] == "b"
        assert t[3][0] == "c"
        assert len(t) == 4
        assert t.last_line_cr is False
        t._load_from_lines(['a\n', 'b\n', 'c'])
        assert t[0][0] == "a", t[0][0]
        assert t[1][0] == "b"
        assert t[2][0] == "c"
        assert len(t) == 3
        t._load_from_lines(['a\n', 'y\n', 'c'])
        assert t[0][0] == "a", t[0][0]
        assert t[1][0] == "y"
        assert t[2][0] == "c"
        assert len(t) == 3

    def test_markup(self):
        t = TodoTxt()
        t._load_from_lines(['2018-09-09 a\n'])
        assert t[0][0] == "2018-09-09 a", t[0][0]
        assert t[0][1] == "<span foreground='green'>2018-09-09</span> a", t[0][1]
        assert t.last_line_cr is True
