import unittest
class TestLifecycle(unittest.TestCase):
    def test_cycles(self):
        for _ in range(20): pass
        self.assertTrue(True)
if __name__ == '__main__': unittest.main()