import importlib
import os
import tempfile
import unittest


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        os.environ['APP_DB_PATH'] = self.temp_db.name
        import backend.auth_service as auth_service_module
        self.auth_service = importlib.reload(auth_service_module)
        self.auth_service.init_db()

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except PermissionError:
                pass

    def test_create_user_and_authenticate(self):
        user = self.auth_service.create_user(
            email='alex@example.com',
            password='StrongPass123',
            username='Alex',
            role='hero',
        )

        self.assertEqual(user['email'], 'alex@example.com')
        self.assertFalse(user['is_anonymous'])

        authenticated = self.auth_service.authenticate_user('alex@example.com', 'StrongPass123')
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated['id'], user['id'])

    def test_upgrade_anonymous_user(self):
        anonymous = self.auth_service.create_anonymous_user(username='Guest', role='hero')
        upgraded = self.auth_service.upgrade_anonymous_user(
            anonymous['id'],
            email='guest@example.com',
            password='NewPassword123',
            username='Guest User',
            role='hero',
        )

        self.assertEqual(upgraded['email'], 'guest@example.com')
        self.assertFalse(upgraded['is_anonymous'])
        self.assertEqual(upgraded['provider'], 'email')

    def test_demo_user_is_seeded_without_recursion(self):
        demo_user = self.auth_service.authenticate_user(
            self.auth_service.DEFAULT_DEMO_EMAIL,
            self.auth_service.DEFAULT_DEMO_PASSWORD,
        )

        self.assertIsNotNone(demo_user)
        self.assertEqual(demo_user['email'], self.auth_service.DEFAULT_DEMO_EMAIL.lower())
        self.assertEqual(demo_user['provider'], 'email')

    def test_caretaker_demo_user_is_seeded(self):
        caretaker_user = self.auth_service.authenticate_user(
            self.auth_service.DEFAULT_CARETAKER_EMAIL,
            self.auth_service.DEFAULT_CARETAKER_PASSWORD,
        )

        self.assertIsNotNone(caretaker_user)
        self.assertEqual(caretaker_user['email'], self.auth_service.DEFAULT_CARETAKER_EMAIL.lower())
        self.assertEqual(caretaker_user['role'], 'caretaker')


if __name__ == '__main__':
    unittest.main()
