#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_crawlit
----------------------------------

Tests for `crawlit` module.
"""

import unittest

import reppy
from crawlit import get_version, default_user_agent
from crawlit.crawlit import fetch_robots_rules, is_same_domain


class TestCrawlit(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_version(self):
        self.assertIsInstance(get_version(), unicode)

    def test_default_user_agent(self):
        self.assertIsInstance(default_user_agent(name="Boom Boom Robo"), unicode)

    def test_fetch_robots_rules(self):
        self.assertIsInstance(fetch_robots_rules("http://kracekumar.com"), reppy.parser.Rules)

    def test_check_same_domain(self):
        self.assertTrue(is_same_domain("http://wordpress.com", "http://kracekumar.wordpress.com"))
        self.assertFalse(is_same_domain("http://kracekumar.com", "http://tumblr.com"))

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
