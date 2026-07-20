import os
import json
import pyzipper
import unittest
from app import app, db
from utils.export_import import import_courriers_from_package

class TestImportLogic(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.zip_path = "test_encrypted.zip"
        self.password = "securepassword"

        # Create a dummy encrypted ZIP
        with pyzipper.AESZipFile(self.zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(self.password.encode('utf-8'))
            data = {"version": "1.0.0", "courriers": [], "attachments": []}
            zf.writestr('data.json', json.dumps(data))

    def tearDown(self):
        if os.path.exists(self.zip_path):
            os.remove(self.zip_path)
        self.app_context.pop()

    def test_import_wrong_password(self):
        result = import_courriers_from_package(self.zip_path, password="wrongpassword")
        self.assertFalse(result["success"])
        self.assertIn("Erreur : La clé de déchiffrement est incorrecte ou l'archive est corrompue.", result["details"])

    def test_import_correct_password(self):
        result = import_courriers_from_package(self.zip_path, password=self.password)
        # With empty courriers list, it should succeed with 0 imported
        self.assertTrue(result["success"])
        self.assertEqual(result["imported"], 0)

if __name__ == '__main__':
    unittest.main()
