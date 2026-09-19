"""Safety regressions for the Category A ZCC draft writer."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from zcc_ir_import import NoRedirect, apply_plan, build_plan, digest, proposed_sku


class ImportTests(unittest.TestCase):
    def row(self, **changes):
        return dict({'source_url': 'https://zcc.ir/product/a/', 'brand_normalized': 'ZCC.CT',
                     'part_number': 'DCMT-X', 'name_fa': 'test', 'category_path': ['turning']}, **changes)

    def plan(self, rows, current=None, selectable=True):
        return build_plan(rows, {'turning': {'mapping_status': 'SAFE_RULE', 'karzar_category_id': '33', 'karzar_category_path': 'Inserts › Turning'}},
                          [{'id': 168, 'breadcrumb': ['Inserts', 'Turning'], 'is_selectable': selectable}], [{'id': 8, 'name': 'ZCC.CT'}], current or [])

    def test_collision_keeps_all_rows_on_hold(self):
        entries = self.plan([self.row(), self.row(source_url='https://zcc.ir/product/b/')])
        self.assertEqual([e['state'] for e in entries], ['HOLD', 'HOLD'])

    def test_unknown_brand_and_long_sku_not_fabricated(self):
        self.assertIsNone(proposed_sku(self.row(brand_normalized=None)))
        self.assertIsNone(proposed_sku(self.row(part_number='X'*60)))

    def test_parent_or_unmapped_category_blocks(self):
        self.assertEqual(self.plan([self.row()], selectable=False)[0]['state'], 'HOLD')
        self.assertEqual(self.plan([self.row(category_path=['other'])])[0]['state'], 'HOLD')

    def test_inactive_existing_is_never_recreated(self):
        current = [{'id': 7, 'sku': 'ZCC-DCMT-X', 'brand': 'ZCC.CT', 'name': 'test', 'is_active': False}]
        self.assertEqual(self.plan([self.row()], current)[0]['state'], 'EXISTING')

    def test_source_prices_never_become_sale_data(self):
        payload = self.plan([self.row(price_normalized=500, availability_normalized='available')])[0]['payload']
        self.assertIsNone(payload['base_price'])
        self.assertFalse(payload['is_active'])
        self.assertFalse(payload['is_available'])
        self.assertEqual(payload['category_id'], 168)

    def test_plan_hash_blocks_before_login_or_write(self):
        with patch('zcc_ir_import.http') as http:
            with self.assertRaises(RuntimeError):
                apply_plan({}, None, Path('/unused'), Path('/unused'), 'wrong', 0)
            http.assert_not_called()

    def test_uncertain_write_stops_and_keeps_intent(self):
        entries = self.plan([self.row(), self.row(part_number='SECOND', source_url='https://zcc.ir/product/b/')])
        plan = {'entries': entries}
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ', {'KARZAR_LOCAL_ADMIN_TOKEN': 'test'}):
            backup = Path(d) / 'backup'
            backup.write_bytes(b'local backup')
            journal = Path(d) / 'audit'
            with patch('zcc_ir_import.http', side_effect=RuntimeError('uncertain')) as http:
                with self.assertRaises(RuntimeError):
                    apply_plan(plan, SimpleNamespace(), journal, backup, digest(plan), 0)
                self.assertEqual(http.call_count, 1)
            self.assertIn('create_intent', journal.read_text())
            self.assertNotIn('"event": "created"', journal.read_text())

    def test_redirect_refused(self):
        with self.assertRaises(RuntimeError):
            NoRedirect().redirect_request(None)


if __name__ == '__main__':
    unittest.main()
