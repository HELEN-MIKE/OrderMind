import tempfile
import unittest
from pathlib import Path

from ordermind.auth import (
    AuthStore,
    AuthenticationError,
    PasswordChangeRequired,
)


class AuthStoreTest(unittest.TestCase):
    def test_first_login_requires_password_change_then_new_password_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = AuthStore(Path(tmpdir) / "users.json")
            store.create_user("alice", "Temp123456", must_change_password=True)

            with self.assertRaises(PasswordChangeRequired):
                store.authenticate("alice", "Temp123456")

            store.change_password("alice", "Temp123456", "StrongPass123")

            with self.assertRaises(AuthenticationError):
                store.authenticate("alice", "Temp123456")

            session = store.authenticate("alice", "StrongPass123")

        self.assertEqual(session.username, "alice")
        self.assertFalse(session.must_change_password)

    def test_invalid_password_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = AuthStore(Path(tmpdir) / "users.json")
            store.create_user("bob", "RightPass123", must_change_password=False)

            with self.assertRaises(AuthenticationError):
                store.authenticate("bob", "WrongPass123")


if __name__ == "__main__":
    unittest.main()
