import importlib
import os
import tempfile
import unittest


class AppSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        os.environ['APP_DB_PATH'] = self.temp_db.name

        import app as app_module
        import backend.auth_service as auth_service_module

        self.auth_service = importlib.reload(auth_service_module)
        self.app_module = importlib.reload(app_module)
        self.app = self.app_module.app
        self.app.config.update(TESTING=True, SECRET_KEY='test-secret-key')
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except PermissionError:
                pass

    def test_login_rejects_invalid_role_and_blank_username(self):
        response = self.client.post(
            '/login',
            data={'role': 'admin', 'username': '   '},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid role', response.get_data(as_text=True))

    def test_generate_rejects_unknown_severity(self):
        with self.client.session_transaction() as session:
            session['user_role'] = 'hero'
            session['username'] = 'Alex'

        response = self.client.post(
            '/api/generate',
            json={'text': 'I am feeling stressed', 'severity': 'unexpected'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Unsupported severity', response.get_data(as_text=True))

    def test_root_creates_anonymous_session(self):
        response = self.client.get('/', follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertTrue(session.get('is_anonymous'))
            self.assertEqual(session.get('auth_provider'), 'anonymous')

    def test_backup_account_upgrades_anonymous_session(self):
        with self.client.session_transaction() as session:
            session['user_role'] = 'hero'
            session['username'] = 'Guest User'
            session['is_anonymous'] = True
            session['auth_provider'] = 'anonymous'

        response = self.client.post(
            '/api/backup-account',
            data={'email': 'alex@example.com', 'password': 'secret123'},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertFalse(session.get('is_anonymous'))
            self.assertEqual(session.get('auth_provider'), 'email')
            self.assertEqual(session.get('backup_email'), 'alex@example.com')


if __name__ == '__main__':
    unittest.main()
