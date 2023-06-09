import unittest
from unittest import mock
from lstore import PageRange, Table, DSAStructure, Bufferpool, DiskInterface, PageRange


class TestTable(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.primary_key_col: int = 0

    @classmethod
    def tearDownClass(self):
        self.primary_key_col: int = None

    def create_bufferpool(self) -> Bufferpool:
        bufferpool = Bufferpool(1000, "")
        bufferpool.disk: DiskInterface = mock.Mock()
        bufferpool.disk.page_exists.return_value = False
        return bufferpool

    def test_insert_record(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
        page_range: mock.MagicMock = mock.Mock()
        page_range.is_full: mock.MagicMock = mock.Mock(return_value=False)
        table.page_ranges: list[PageRange] = [page_range]
        record: list[int] = [1, 2]

        insert_ok: bool = table.insert_record(record)
        self.assertTrue(insert_ok)
        self.assertEqual(len(table.page_ranges), 1)

    def test_insert_record_latest_page_range_full(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
        page_range: mock.MagicMock = mock.Mock()
        page_range.is_full: mock.MagicMock = mock.Mock(return_value=True)
        table.page_ranges: list[PageRange] = [page_range]
        record: list[int] = [1, 2]

        insert_ok: bool = table.insert_record(record)
        self.assertTrue(insert_ok)
        self.assertEqual(len(table.page_ranges), 2)

    def test_insert_record_with_duplicate_key(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
        table.index.key_exists: mock.MagicMock = mock.Mock(return_value=True)
        table.index.add_key_rid: mock.MagicMock = mock.Mock()
        page_range: mock.MagicMock = mock.Mock()
        page_range.is_full: mock.MagicMock = mock.Mock(return_value=False)
        table.page_ranges: list[mock.MagicMock] = [page_range]
        with self.assertRaises(AssertionError):
            table.insert_record([1, 2])
        # ensure atomicity - make sure no changes to table resulted from invalid transaction
        self.assertEqual(len(table.page_ranges), 1)
        self.assertFalse(page_range.insert_record.called)
        self.assertFalse(table.index.add_key_rid.called)

    def test_update_existent_record(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 3, self.primary_key_col, bufferpool)
        record: list[int] = [10, 20, 30]
        new_record: list[int] = [11, 21, 31]

        table.insert_record(record)
        old_rid: int = table.index.get_rid(record[self.primary_key_col])
        update_ok: bool = table.update_record(record[self.primary_key_col], new_record)
        self.assertTrue(update_ok)

        given_rid: int = table.index.get_rid(new_record[self.primary_key_col])
        self.assertEqual(given_rid, old_rid)

        with self.assertRaises(AssertionError):
            table.index.get_rid(record[self.primary_key_col])

    def test_brute_force_search(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 5, self.primary_key_col, bufferpool, secondary_structure=DSAStructure.DICTIONARY_ARRAY)
        RECORD_VALUE = 8
        records: list[list[int]] = [
            [1, 2, 3, 4, 1],
            [4, 1, 2, 2, 32],
            [2, 6, 5, 1, 1],
            [3, 2, RECORD_VALUE, 3, 1],
            [5, 6, RECORD_VALUE, 9, 43],
            [7, 4, RECORD_VALUE, 9, 4],
            [8, 1, RECORD_VALUE, 9, 3],
            [6, 9, RECORD_VALUE, 9, 13],
        ]
        for record in records:
            table.insert_record(record)
        # retrieving the data that is stored in the secondary index
        expected_rids = table.secondary_indices[2].search_record(RECORD_VALUE)
        # setting the secondary index to None, and using brute force search
        table.secondary_indices[2] = None
        brute_search_indices = table.brute_force_search(RECORD_VALUE, 2)
        self.assertEqual(list(expected_rids), brute_search_indices)

    def test_brute_force_search_set(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 5, self.primary_key_col, bufferpool, secondary_structure=DSAStructure.DICTIONARY_SET)
        RECORD_VALUE = 8
        records: list[list[int]] = [
            [1, 2, 3, 4, 1],
            [4, 1, 2, 2, 32],
            [2, 6, 5, 1, 1],
            [3, 2, RECORD_VALUE, 3, 1],
            [5, 6, RECORD_VALUE, 9, 43],
            [7, 4, RECORD_VALUE, 9, 4],
            [8, 1, RECORD_VALUE, 9, 3],
            [6, 9, RECORD_VALUE, 9, 13],
        ]
        for record in records:
            table.insert_record(record)
        # retrieving the data that is stored in the secondary index
        expected_rids = table.secondary_indices[2].search_record(RECORD_VALUE)
        # setting the secondary index to None, and using brute force search
        table.secondary_indices[2] = None
        brute_search_indices = table.brute_force_search(RECORD_VALUE, 2)
        self.assertEqual(list(expected_rids), brute_search_indices)

    def test_update_existent_record_multiprocessing(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 3, self.primary_key_col, bufferpool, mp=True)
        record: list[int] = [10, 20, 30]
        new_record: list[int] = [11, 21, 31]

        table.insert_record(record)
        table.wait_for_async_responses()
        old_rid: int = table.index.get_rid(record[self.primary_key_col])
        update_ok: bool = table.update_record(record[self.primary_key_col], new_record)
        self.assertTrue(update_ok)

        given_rid: int = table.index.get_rid(new_record[self.primary_key_col])
        self.assertEqual(given_rid, old_rid)

        with self.assertRaises(AssertionError):
            table.index.get_rid(record[self.primary_key_col])
        table.stop_all_secondary_indices()

    def test_brute_force_search_multiprocessing(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 5, self.primary_key_col, bufferpool, secondary_structure=DSAStructure.DICTIONARY_ARRAY, mp=True)
        RECORD_VALUE = 8
        records: list[list[int]] = [
            [1, 2, 3, 4, 1],
            [4, 1, 2, 2, 32],
            [2, 6, 5, 1, 1],
            [3, 2, RECORD_VALUE, 3, 1],
            [5, 6, RECORD_VALUE, 9, 43],
            [7, 4, RECORD_VALUE, 9, 4],
            [8, 1, RECORD_VALUE, 9, 3],
            [6, 9, RECORD_VALUE, 9, 13],
        ]
        for record in records:
            table.insert_record(record)
        table.wait_for_async_responses()
        # retrieving the data that is stored in the secondary index
        _, expected_rids = table.search_secondary_multiprocessing(RECORD_VALUE, 2)
        # setting the secondary index to None, and using brute force search
        brute_search_indices = table.brute_force_search(RECORD_VALUE, 2)
        self.assertEqual(list(expected_rids), brute_search_indices)
        table.stop_all_secondary_indices()

    def test_brute_force_search_set_multiprocessing(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 5, self.primary_key_col, bufferpool, secondary_structure=DSAStructure.DICTIONARY_SET, mp=True)
        RECORD_VALUE = 8
        records: list[list[int]] = [
            [1, 2, 3, 4, 1],
            [4, 1, 2, 2, 32],
            [2, 6, 5, 1, 1],
            [3, 2, RECORD_VALUE, 3, 1],
            [5, 6, RECORD_VALUE, 9, 43],
            [7, 4, RECORD_VALUE, 9, 4],
            [8, 1, RECORD_VALUE, 9, 3],
            [6, 9, RECORD_VALUE, 9, 13],
        ]
        for record in records:
            table.insert_record(record)
        table.wait_for_async_responses()
        # retrieving the data that is stored in the secondary index
        _, expected_rids = table.search_secondary_multiprocessing(RECORD_VALUE, 2)
        # setting the secondary index to None, and using brute force search
        brute_search_indices = table.brute_force_search(RECORD_VALUE, 2)
        self.assertEqual(list(expected_rids), brute_search_indices)
        table.stop_all_secondary_indices()

    def test_update_non_existing_record_multiprocessing(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
        with self.assertRaises(AssertionError):
            table.update_record(1, [90, 14])

    # def test_get_latest_column_values_after_insert(self) -> None:
    #     bufferpool = self.create_bufferpool()
    #     table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
    #     prim_key: int = 10
    #     record: list[int] = [prim_key, 20]
    #     table.insert_record(record)
    #     self._test_all_get_column_possibilities(prim_key, table, record)

    # def test_get_latest_column_values_after_update(self) -> None:
    #     bufferpool = self.create_bufferpool()
    #     table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
    #     rid: int = table.insert_record([1, 2])
    #     new_prim_key: int = 90
    #     new_record: list[int] = [new_prim_key, 14]
    #     table.update_record(rid, new_record)
    #     self._test_all_get_column_possibilities(new_prim_key, table, new_record)

    def test_delete_record(self) -> None:
        bufferpool = self.create_bufferpool()
        table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
        prim_key = 1
        table.insert_record([prim_key, 2])
        table.delete_record(prim_key)
        with self.assertRaises(AssertionError):
            table.get_latest_column_values(prim_key, [1, 1])

    # def _test_all_get_column_possibilities(self, prim_key, table: Table, record) -> None:
    #     rid: int = table.index.get_rid(prim_key)
    #     self.assertEqual(table.get_latest_column_values(rid, [0, 0]), [[]])
    #     self.assertEqual(table.get_latest_column_values(rid, [0, 1]), [[record[1]]])
    #     self.assertEqual(table.get_latest_column_values(rid, [1, 0]), [[record[0]]])
    #     self.assertEqual(table.get_latest_column_values(rid, [1, 1]), [record])

    # def test_get_latest_column_values_nonexisting_record(self) -> None:
    #     bufferpool = self.create_bufferpool()
    #     table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
    #     with self.assertRaises(AssertionError):
    #         table.get_latest_column_values(1, [1, 1])

    # def test_get_latest_column_values_invalid_projected_cols(self) -> None:
    #     bufferpool = self.create_bufferpool()
    #     table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
    #     with self.assertRaises(AssertionError):
    #         table.get_latest_column_values(1, [1, 1, 1])

    # def test_get_latest_column_values_invalid_projected_cols_arrayrid(self) -> None:
    #     table: Table = Table("table1", 2, self.primary_key_col)
    #     with self.assertRaises(AssertionError):
    #         table.get_latest_column_values([1], [1, 1, 1])

    # def test_delete_non_existing_record(self) -> None:
    #     bufferpool = self.create_bufferpool()
    #     table: Table = Table("table1", 2, self.primary_key_col, bufferpool)
    #     with self.assertRaises(AssertionError):
    #         table.delete_record(1)

    # def test_merge(self) -> None:
    #     bufferpool = self.create_bufferpool()
    #     table: Table = Table("table1", 3, self.primary_key_col, bufferpool)
    #     record: list[int] = [10, 20, 30]
    #     inc: int = 0
    #     table.insert_record(record)
    #     rid: int = table.index.get_rid(record[self.primary_key_col])
    #     base_page = table.page_directory.get_page(rid)
    #     old_base_page = base_page
    #     while base_page.tps == 0:
    #         new_record: list[int] = [None, 20 + inc, 30 + inc]
    #         table.update_record(record[self.primary_key_col], new_record)
    #         base_page = table.page_directory.get_page(rid)
    #         inc += 1
    #     print(table.get_latest_column_values(rid, [1, 1, 1]))
    #     self.assertNotEqual(base_page, old_base_page)
    #     col_val = base_page.get_column_of_record(1, 0)
    #     self.assertNotEqual(record[1], col_val)
    #     col_val = base_page.get_column_of_record(2, 0)
    #     self.assertNotEqual(record[2], col_val)


if __name__ == "__main__":
    unittest.main()