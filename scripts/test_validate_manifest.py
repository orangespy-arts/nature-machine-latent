import tempfile
import unittest
from pathlib import Path

from validate_manifest import FIELDS, read_csv, validate


def asset(**changes):
    row = dict.fromkeys(FIELDS, '')
    row.update(asset_id='A', relative_path='a.wav', duration_seconds='1',
               sample_rate_hz='96000', channels='2', sha256='a' * 64,
               split='unassigned', license='unknown')
    row.update(changes)
    return row


class ManifestTests(unittest.TestCase):
    def test_pending_inventory_is_valid(self):
        report = validate([asset()])
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['pending_metadata']['license'], 1)

    def test_leakage_by_group_and_hash(self):
        rows = [asset(recording_group='session', source='recorded', license='owned', split='train'),
                asset(asset_id='B', relative_path='b.wav', recording_group='session',
                      source='recorded', license='owned', split='test')]
        errors = validate(rows)['errors']
        self.assertEqual(sum('cross-split leakage' in error for error in errors), 2)

    def test_invalid_values_and_assignment(self):
        errors = validate([asset(duration_seconds='nan', channels='1.5', split='train')])['errors']
        for field in ('duration_seconds', 'channels', 'recording_group', 'source', 'license'):
            self.assertTrue(any(field in error for error in errors))

    def test_unsafe_paths(self):
        for path in ('../a.wav', 'C:\\a.wav', '/a.wav', 'C:a.wav', ''):
            with self.subTest(path=path):
                self.assertTrue(any('unsafe' in e for e in validate([asset(relative_path=path)])['errors']))

    def test_duplicates_and_queue_mismatch(self):
        queue = [dict(asset_id='A', relative_path='wrong.wav', duration_seconds='1', review='pending')]
        errors = validate([asset(), asset()], queue)['errors']
        self.assertTrue(any('duplicate asset_id' in e for e in errors))
        self.assertTrue(any('duplicate relative_path' in e for e in errors))
        self.assertTrue(any('differs' in e for e in errors))

    def test_file_existence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(validate([asset()], root=root)['errors'])
            (root / 'a.wav').touch()
            self.assertEqual(validate([asset()], root=root)['errors'], [])

    def test_malformed_csv_and_empty_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.csv'
            path.write_text('asset_id,relative_path\nA\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_csv(path, ['asset_id', 'relative_path'])
        self.assertTrue(validate([])['errors'])


if __name__ == '__main__':
    unittest.main()
