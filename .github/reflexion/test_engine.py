import unittest
from engine import retrieve, validate

def lesson(id="a", **kw):
    return dict(dict(id=id, tags=["docker"], trigger="build failure",
        evidence="a"*40, action="inspect build logs", status="approved",
        supersedes=None), **kw)

class EngineTests(unittest.TestCase):
    def test_relevance(self):
        a = lesson()
        self.assertEqual(retrieve([a], "docker"), [a])
        self.assertEqual(retrieve([a], "unrelated"), [])
    def test_budget(self):
        self.assertEqual(retrieve([lesson()], "docker", budget=2), [])
        self.assertEqual(retrieve([lesson()], "docker", limit=0), [])
    def test_invalid_budget(self):
        for budget in (-1, 0, 1):
            with self.assertRaises(ValueError):
                retrieve([], "docker", budget=budget)
        with self.assertRaises(ValueError):
            retrieve([], "docker", limit=-1)
    def test_credential_screen(self):
        for action in ("token=" + "x"*24, "-----BEGIN PRIVATE KEY-----", "ghp_" + "x"*30):
            with self.assertRaisesRegex(ValueError, "Potential credential"):
                validate([lesson(action=action)])
    def test_candidate(self):
        self.assertEqual(retrieve([lesson(status="candidate")], "docker"), [])
    def test_supersession(self):
        a = lesson()
        b = lesson("b", action="inspect failed build step", supersedes="a")
        self.assertEqual(retrieve([a,b], "docker"), [b])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate([lesson(), lesson("b", action="Inspect build logs!")])
    def test_malformed(self):
        with self.assertRaises(ValueError):
            validate([{}])
    def test_order(self):
        a = lesson()
        b = lesson("b", action="verify build output")
        self.assertEqual(retrieve([b,a], "docker"), [a,b])

if __name__ == "__main__":
    unittest.main()
