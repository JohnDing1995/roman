import os
import unittest
from json import loads

from apluslms_roman.utils.path_mapping import json_re, load_from_env

test_case_loadable = (
    'true',
    'false',
    'null',
    '123',
    '-123',
    '3.14',
    '-3.14',
    '{"foo": "bar"}',
    '[1, 2, 3]',
    '"foo bar"'
)

test_case_not_loadable = (
    "/foobar.py",
    "text",
    "yes",
    "0123123",
)


class TestJsonLoadable(unittest.TestCase):

    def test_loadable_not_raise(self):
        for case in test_case_loadable:
            with self.subTest(non_json=case):
                loads(case)

    def test_not_loadable_raise(self):
        for case in test_case_not_loadable:
            with self.subTest(non_json=case):
                with self.assertRaises(ValueError, msg="Testing:{}".format(case)):
                    loads(case)


class TestJsonRegex(unittest.TestCase):

    def test_loadable_match(self):
        for case in test_case_loadable:
            with self.subTest(non_json=case):
                self.assertTrue(json_re.match(case)is not None, msg="Testing:{}".format(case))

    def test_not_loadable_not_match(self):
        for case in test_case_not_loadable:
            with self.subTest(non_json=case):
                self.assertFalse(json_re.match(case) is not None, msg="Testing:{}".format(case))


class TestLoadFromEnv(unittest.TestCase):

    def test_with_decode_json(self):
        os.environ['DOCKER.FOO.BAR'] = '123'
        self.assertEqual({'foo': {'bar': '123'}}, load_from_env('DOCKER.', False))

    def test_without_decode_json(self):
        os.environ['DOCKER.FOO.BAR'] = '123'
        self.assertEqual({'foo': {'bar': 123}}, load_from_env('DOCKER.', True))

