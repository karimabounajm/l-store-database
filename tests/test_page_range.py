import unittest
import random
from lstore import (
    PageRange,
    RID_Generator,
    MAX_BASE_PAGES_IN_PAGE_RANGE,
    PHYSICAL_PAGE_SIZE,
    ATTRIBUTE_SIZE,
    INVALID_RID
)

class TestPageRange(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.num_cols: int = 3
        self.rid_generator: RID_Generator = RID_Generator()
        self.max_base_page_records_per_page_range: int = MAX_BASE_PAGES_IN_PAGE_RANGE * (PHYSICAL_PAGE_SIZE // ATTRIBUTE_SIZE)

    @classmethod
    def tearDownClass(self):
        self.num_cols: int = None
        self.rid_generator: RID_Generator = None
        self.max_base_page_records_per_page_range: int = None

    def test_is_full(self) -> None:
        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)
        for _ in range(self.max_base_page_records_per_page_range):
            self.assertFalse(page_range.is_full())
            page_range.insert_column([9,4,14])
        self.assertTrue(page_range.is_full())

    def test_insert_column(self) -> None:
        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)

        records_to_verify: list[int, list[int]] = []
        for _ in range(self.max_base_page_records_per_page_range):
            random_record = [random.getrandbits(ATTRIBUTE_SIZE) for _ in range (self.num_cols)]
            rid = page_range.insert_column(random_record)
            self.__verify_record_retrieval(page_range, rid, random_record + [0, rid])
            records_to_verify.append((rid, random_record))

        for rid, expected_record in records_to_verify:
            self.__verify_record_retrieval(page_range, rid, expected_record + [0, rid])

    def test_insert_column_when_page_range_full(self) -> None:
        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)

        for _ in range(self.max_base_page_records_per_page_range):
            random_record = [random.getrandbits(ATTRIBUTE_SIZE) for _ in range (self.num_cols)]
            rid = page_range.insert_column(random_record)
            self.assertNotEqual(
                first=rid,
                second=INVALID_RID,
                msg=f"Expected valid RID but received invalid RID. Received rid of {rid}"
            )

        rid = page_range.insert_column(random_record)
        self.assertEqual(
            first=rid,
            second=INVALID_RID,
            msg=f"Expected invalid RID but received valid RID. Expected: {INVALID_RID} Received: {rid}"
        )

    def test_get_latest_column_value_after_insert(self) -> None:
        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)
        base_rid = page_range.insert_column([1,2,3])
        self.__verify_record_retrieval(page_range, base_rid, [1,2,3,0b000,base_rid])

    def test_get_latest_column_value_after_update(self) -> None:
        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)
        base_rid = page_range.insert_column([1,2,3])
        page_range.update_record(base_rid, [None, 5, None])
        self.__verify_record_retrieval(page_range, base_rid, [1,5,3,0b010,base_rid])

    def test_update_record_for_small_number_of_updates(self) -> None:
        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)
        base_rid = page_range.insert_column([1,2,3])
        self.__verify_record_retrieval(page_range, base_rid, [1,2,3,0b000,base_rid])
        tail_rid1 = page_range.update_record(base_rid, [None, 5, None])
        self.__verify_record_retrieval(page_range, base_rid, [1,5,3,0b010,base_rid])
        tail_rid2 = page_range.update_record(base_rid, [None, 7, 2])
        self.__verify_record_retrieval(page_range, base_rid, [1,7,2,0b011,tail_rid1])
        tail_rid3 = page_range.update_record(base_rid, [9, None, None])
        self.__verify_record_retrieval(page_range, base_rid, [9,7,2,0b100,tail_rid2])
        self.__verify_tail_chain(
            page_range,
            base_rid,
            [
                (base_rid, [1,2,3,0b000,tail_rid3]),
                (tail_rid3, [9,7,2,0b100,tail_rid2]),
                (tail_rid2, [1,7,2,0b011,tail_rid1]),
                (tail_rid1, [1,5,3,0b010,base_rid]),
            ])

    def test_update_record_for_large_number_of_updates(self) -> None:
        multiplier: int = 2

        page_range: PageRange = PageRange(self.num_cols, self.rid_generator)
        base_rid = page_range.insert_column([1,2,3])

        previous_tail_rid = base_rid
        for _ in range (self.max_base_page_records_per_page_range * multiplier):
            tail_rid = page_range.update_record(base_rid, [4, 5, 6])
            self.__verify_record_retrieval(page_range, base_rid, [4,5,6,0b111,previous_tail_rid])
            previous_tail_rid = tail_rid

        expected_tail_chain = [(base_rid,[1,2,3,0b000,previous_tail_rid])]
        for rid in range(previous_tail_rid, base_rid, -1):
            expected_tail_chain.append((rid, ([4,5,6,0b111,rid-1])))

        self.__verify_tail_chain(
            page_range,
            base_rid,
            expected_tail_chain
            )
        self.assertEqual(
            first=len(page_range.base_pages),
            second=1,
            msg=f"Page range has unexpected number of base pages. Expected 1 base page. \
                Found {len(page_range.base_pages)} base page(s)"
        )
        self.assertEqual(
            first=len(page_range.tail_pages),
            second=MAX_BASE_PAGES_IN_PAGE_RANGE * multiplier,
            msg=f"Page range has unexpected number of tail pages. \
                Expected {MAX_BASE_PAGES_IN_PAGE_RANGE * multiplier} tail page. \
                Found {len(page_range.tail_pages)} tail page(s)"
        )

        page_range.update_record(base_rid, [4, 5, 6])
        self.assertEqual(
            first=len(page_range.tail_pages),
            second=MAX_BASE_PAGES_IN_PAGE_RANGE * multiplier + 1,
            msg=f"Page range has unexpected number of tail pages. \
                Expected {MAX_BASE_PAGES_IN_PAGE_RANGE * multiplier + 1} tail page. \
                Found {len(page_range.tail_pages)} tail page(s)"
        )

    def __verify_tail_chain(self, page_range: PageRange, base_rid: int, expected_tail_chain) -> None:
        actual_tail_chain = page_range._get_tail_chain(base_rid)
        self.assertEqual(
            first=len(actual_tail_chain),
            second=len(expected_tail_chain),
            msg=f"Tail chain lengths differ. Expected: {len(expected_tail_chain)} Received: {actual_tail_chain}"
        )
        for (actual_rid, actual_record), (expected_rid, expected_record) in zip(actual_tail_chain, expected_tail_chain):
            self.assertEqual(
                first=actual_rid,
                second=expected_rid,
                msg=f"Record RIDs differ. Expected: {expected_rid} Received: {actual_rid}"
            )
            self.assertListEqual(
                list1=actual_record,
                list2=expected_record,
                msg=f"Record columns differ. Expected: {expected_record} Received: {actual_record}"
            )

    def __verify_record_retrieval(self, page_range: PageRange, rid: int, expected_record: list[int]) -> None:
        for ind in range(self.num_cols):
            actual_col_val: int = page_range.get_latest_column_value(rid, ind)
            expected_col_val: int = expected_record[ind]
            self.assertEqual(
                first=actual_col_val,
                second=expected_col_val,
                msg=f"Expected {expected_col_val} Received: {actual_col_val}"
            )

if __name__ == '__main__':
    unittest.main()