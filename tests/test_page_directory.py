import unittest
from unittest import mock
from lstore import BasePage, Bufferpool, DiskInterface, RID_Generator, PageDirectory, INVALID_RID, INVALID_SLOT_NUM


class TestPageDirectory(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.rid_generator = RID_Generator()
        self.base_rid: int = 24
        bufferpool = Bufferpool(1000, "")
        bufferpool.disk: DiskInterface = mock.Mock()
        bufferpool.disk.page_exists.return_value = False
        self.base_page: BasePage = BasePage("", 5, bufferpool, self.rid_generator)
        self.base_record_slot_num: int = 16

    @classmethod
    def tearDownClass(self):
        self.rid_generator = None
        self.base_rid: int = None
        self.base_page: BasePage = None
        self.base_record_slot_num: int = None

    def test_insert_page_when_page_not_previously_inserted(self) -> None:
        page_directory: PageDirectory = PageDirectory()
        try:
            page_directory.insert_page(self.base_rid, self.base_page)
        except:
            self.fail("Exception raises on insert_page unexpectedly.")

    # def test_insert_page_when_page_previously_inserted(self) -> None:
    #     page_directory: PageDirectory = PageDirectory()
    #     page_directory.insert_page(
    #         self.base_rid, self.base_page
    #     )
    #     with self.assertRaises(AssertionError):
    #         page_directory.insert_page(
    #             self.base_rid, self.base_page
    #         )

    def test_get_page_when_no_pages_inserted(self) -> None:
        page_directory: PageDirectory = PageDirectory()
        page: BasePage = page_directory.get_page(7)
        self.assertEqual(
            page,
            None,
            msg=f"Received valid page details. Expected: {(INVALID_RID, INVALID_SLOT_NUM)} Received: {page}",
        )

    def test_get_page_when_page_inserted(self) -> None:
        page_directory: PageDirectory = PageDirectory()
        page_directory.insert_page(self.base_rid, self.base_page)
        page: BasePage = page_directory.get_page(self.base_rid)
        self.assertEqual(
            page,
            self.base_page,
            msg=f"Received valid page details. Expected: {(INVALID_RID, INVALID_SLOT_NUM)} Received: {page}",
        )

    def test_delete_page_when_page_does_not_exist(self) -> None:
        page_directory: PageDirectory = PageDirectory()
        with self.assertRaises(AssertionError):
            page_directory.delete_page(self.base_rid)

    def test_delete_page_when_page_exists(self) -> None:
        page_directory: PageDirectory = PageDirectory()
        page_directory.insert_page(self.base_rid, self.base_page)
        try:
            page_directory.delete_page(self.base_rid)
        except:
            self.fail("Exception raises on insert_page unexpectedly.")
        page: BasePage = page_directory.get_page(self.base_rid)
        self.assertEqual(
            page,
            None,
            msg=f"Received valid page details. Expected: {(INVALID_RID, INVALID_SLOT_NUM)} Received: {page}",
        )


if __name__ == "__main__":
    unittest.main()
