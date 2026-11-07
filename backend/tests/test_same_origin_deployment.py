"""Safety contracts for the coordinated same-origin Render transition."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class SameOriginDeploymentTests(unittest.TestCase):
    def test_blueprint_preserves_resources_and_wires_the_canonical_origin(self):
        current = yaml.safe_load((ROOT / 'render.yaml').read_text(encoding='utf-8'))
        # Explicit resource identities also work in shallow CI checkouts.
        self.assertEqual(len(current['databases']), 1)
        self.assertEqual(current['databases'][0]['name'], 'barbearia-homolog-db')
        self.assertEqual(current['databases'][0]['databaseName'], 'barbearia_homolog')
        self.assertEqual({(s['name'], s['runtime']) for s in current['services']},
                         {('barbearia-homolog-api', 'python'), ('barbearia-homolog-frontend', 'static')})
        api = next(s for s in current['services'] if s['runtime'] == 'python')
        env = {v['key']: v for v in api['envVars']}
        self.assertEqual(api['rootDir'], '.')
        self.assertIn('backend/requirements.txt', api['buildCommand'])
        self.assertIn('cd backend &&', api['startCommand'])
        self.assertEqual(env['SERVE_FRONTEND']['value'], 'true')
        self.assertEqual(str(env['PYTHON_VERSION']['value']), (ROOT / 'backend/.python-version').read_text().strip())
        for name in ('CORS_ALLOWED_ORIGINS', 'FRONTEND_ORIGIN'):
            self.assertEqual(env[name]['fromService'], {
                'name': api['name'], 'type': 'web', 'envVarKey': 'RENDER_EXTERNAL_URL'})

    def test_legacy_service_is_retained_as_a_redirect_entry(self):
        config = yaml.safe_load((ROOT / 'render.yaml').read_text(encoding='utf-8'))
        legacy = next(s for s in config['services'] if s['runtime'] == 'static')
        env = {v['key']: v for v in legacy['envVars']}
        self.assertEqual(env['PUBLIC_SAME_ORIGIN_REDIRECT']['value'], 'true')
        self.assertEqual(env['PUBLIC_API_URL']['fromService']['name'], 'barbearia-homolog-api')
