from .config import (
    MAX_BASE_PAGES_IN_PAGE_RANGE,
    INVALID_RID,
    INVALID_OFFSET,
    INDIRECTION_COLUMN,
    NUMBER_OF_METADATA_COLUMNS
)
from .page import LogicalPage, BasePage, TailPage
from .rid import RID_Generator

class PageRange():

    def __init__(self, num_cols: list[int], page_directory: dict[int,tuple[LogicalPage,int]], rid_generator: RID_Generator):
        self.num_attr_cols: int = num_cols
        self.num_total_cols: int = num_cols + NUMBER_OF_METADATA_COLUMNS
        self.base_pages: list[BasePage] = [BasePage(self.num_total_cols, rid_generator)]
        self.tail_pages: list[TailPage] = [TailPage(self.num_total_cols, rid_generator)]
        self.page_directory: dict[int,tuple[BasePage,int]] | dict[int,tuple[TailPage,int]] = page_directory
        self.rid_generator: RID_Generator = rid_generator

    def is_full(self) -> bool:
        return len(self.base_pages) == MAX_BASE_PAGES_IN_PAGE_RANGE and self.base_pages[-1].is_full()

    def insert_column(self, columns: list[int]) -> int:
        if self.is_full():
            return INVALID_RID

        latest_base_page: BasePage = self.base_pages[-1]
        if latest_base_page.is_full():
            new_base_page: BasePage = BasePage(self.num_total_cols, self.rid_generator)
            self.base_pages.append(new_base_page)
            latest_base_page = new_base_page

        rid, offset = latest_base_page.insert_record(columns + [0, 0]) # schema encoding and indirectory set to 0
        latest_base_page.update_indir_of_record(rid, offset)
        self.page_directory[rid] = latest_base_page, offset
        return rid

    def update_record(self, base_rid: int, columns_to_update: list[int]) -> int:
        assert len(columns_to_update) == self.num_attr_cols

        # Find latest version of record (may be in Base or Tail page)
        latest_page, latest_page_offset, latest_record_rid = self.__get_latest_record_details(base_rid)
        latest_record_columns: list[int] = [latest_page.get_column_of_record(ind, latest_page_offset) for ind in range(self.num_attr_cols)]

        # Find latest tail page to insert next version of record
        latest_tail_page: TailPage = self.tail_pages[-1]
        if latest_tail_page.is_full():
            new_tail_page = TailPage(self.num_total_cols, self.rid_generator)
            self.tail_pages.append(new_tail_page)
            latest_tail_page = new_tail_page

        # Create new record to insert (replace NULL values with previous records values)
        new_tail_record_columns = []
        updated_column_indices = []
        for old_col, new_col in zip(latest_record_columns, columns_to_update):
            if new_col != None:
                updated_column_indices.append(1)
                new_tail_record_columns.append(new_col)
            else:
                updated_column_indices.append(0)
                new_tail_record_columns.append(old_col)

        # Construct schema encoding integer for new record
        schema_encoding_binary_string: str = ''.join(map(str,updated_column_indices))
        schema_encoding_integer: int = int(schema_encoding_binary_string, base=2)

        new_tail_record_columns.append(schema_encoding_integer)
        new_tail_record_columns.append(latest_record_rid)

        # Insert new record and update page directory
        new_tail_page_rid, new_tail_page_offset = latest_tail_page.insert_record(new_tail_record_columns)
        self.page_directory[new_tail_page_rid] = latest_tail_page, new_tail_page_offset

        # Update indirectory of base record to point to latest tail record
        base_page, base_page_offset = self.__get_page_and_offset(base_rid)
        base_page.update_indir_of_record(new_tail_page_rid, base_page_offset)

        return new_tail_page_rid

    # CUMULATIVE
    def get_latest_column_value(self, base_rid: int, column_index: int) -> int:
        page, offset, _ = self.__get_latest_record_details(base_rid)
        column_value = page.get_column_of_record(column_index, offset)
        return column_value

    def _get_tail_chain(self, base_rid: int) -> list[tuple[int,list[int]]]:
        curr_rid: int = base_rid
        tail_chain = []
        while True:
            page, offset = self.__get_page_and_offset(curr_rid)
            record = [page.get_column_of_record(ind, offset) for ind in range(self.num_total_cols)]
            tail_chain.append((curr_rid, record))
            curr_rid = page.get_column_of_record(INDIRECTION_COLUMN, offset)
            if curr_rid == base_rid:
                break
        return tail_chain

    def __get_latest_record_details(self, base_rid: int) -> tuple[BasePage,int,int] | tuple[TailPage,int,int]:
        base_page, base_page_offset = self.__get_page_and_offset(base_rid)
        base_page_indir_rid: int = base_page.get_column_of_record(INDIRECTION_COLUMN, base_page_offset)
        if base_rid == base_page_indir_rid:
            return base_page, base_page_offset, base_rid

        tail_page, tail_page_offset = self.__get_page_and_offset(base_page_indir_rid)
        return tail_page, tail_page_offset, base_page_indir_rid

    def __get_page_and_offset(self, rid: int) -> tuple[BasePage,int] | tuple[TailPage,int]:
        page, offset = self.page_directory.get(rid, (None, INVALID_OFFSET))
        assert page != None and offset != INVALID_OFFSET
        return page, offset