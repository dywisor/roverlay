#!/usr/bin/python

import unittest

import tests.depres


if __name__ == '__main__':
   tests = tests.depres.suite()
   unittest.TextTestRunner ( verbosity=2 ).run ( tests )
