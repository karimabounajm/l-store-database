from .config import (
    INVALID_RID,
    NUM_RECORDS_IN_PAGE_RANGE
)
from .index import Index
from .rid import RID_Generator
from .page_range import PageRange
from .page_directory import PageDirectory

class Record:

    def __init__(self, rid, key, columns):
        self.rid = rid
        self.key = key
        self.columns = columns

class Table:

    """
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def __init__(self, name: str, num_columns: int, primary_key_col: int):
        self.name: str = name
        self.primary_key_col: int = primary_key_col
        self.num_columns: int = num_columns
        self.index: Index = Index(self)
        self.page_directory: PageDirectory = PageDirectory()
        self.rid_generator: RID_Generator = RID_Generator()
        self.page_ranges: list = [PageRange(self.num_columns, self.page_directory, self.rid_generator)]

    def delete_record(self, primary_key: int) -> None:
        rid: int = self.index.get_rid(primary_key)
        self.index.delete_key(primary_key)
        self.page_directory.delete_page(rid)

    # should we check / assert that the primary key does not already exist in the index?
    def insert_record(self, columns: list) -> bool:
        last_page_range: PageRange = self.page_ranges[-1]
        if last_page_range.is_full():
            new_page_range: PageRange = PageRange(self.num_columns, self.page_directory, self.rid_generator)
            rid_from_insertion: int = new_page_range.insert_record(columns)
            self.page_ranges.append(new_page_range)
        else:
            rid_from_insertion: int = last_page_range.insert_record(columns)
        if rid_from_insertion != INVALID_RID:
            self.index.add_key_rid(columns[self.primary_key_col], rid_from_insertion)
            return True
        return False

    def update_record(self, primary_key: int, columns: list) -> bool:
        rid: int = self.index.get_rid(primary_key)
        page_range_with_record: PageRange = self.__find_page_range_with_rid(rid)
        self.index.delete_key(primary_key)
        self.index.add_key_rid(columns[self.primary_key_col], rid)
        return page_range_with_record.update_record(rid, columns) != INVALID_RID

    def get_latest_column_values(self, primary_key: int, projected_columns_index: list):
        assert len(projected_columns_index) == self.num_columns
        rid: int = self.index.get_rid(primary_key)
        page_range: PageRange = self.__find_page_range_with_rid(rid)
        col_vals: list = []
        for col_ind in range(self.num_columns):
            if projected_columns_index[col_ind] == 1:
                col_val: int = page_range.get_latest_column_value(rid, col_ind)
                col_vals.append(col_val)
        return col_vals

    def __find_page_range_with_rid(self, rid: int):
        page_range_index: int = rid // NUM_RECORDS_IN_PAGE_RANGE
        assert 0 <= page_range_index < len(self.page_ranges)
        return self.page_ranges[page_range_index]

    def __merge(self):
        print("merge is happening")
        pass
 