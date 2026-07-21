import unittest
from app import app

class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_root_redirect_unauthenticated(self):
        """Test that unauthenticated users are redirected to login"""
        response = self.app.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        # Check if redirect location contains 'login'
        # The location might be a full URL (http://localhost/login) or relative (/login)
        self.assertIn('/login', response.location)

    def test_landing_page_gone(self):
        """Test that attempting to access a hypothetical landing page returns 404"""
        # Assuming 'landing' was the endpoint name or /landing path
        response = self.app.get('/landing', follow_redirects=True)
        self.assertEqual(response.status_code, 404)
