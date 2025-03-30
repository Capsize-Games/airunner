#!/usr/bin/env python

import unittest

def main():
    # Discover and run tests in the specified directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(start_dir="src/airunner/tests", pattern="*.py")
    test_runner = unittest.TextTestRunner()
    test_runner.run(test_suite)

if __name__ == "__main__":
    main()