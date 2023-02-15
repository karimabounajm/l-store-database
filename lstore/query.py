from lstore.table import Table, Record
from lstore.index import Index


class Query:
    """
    # Creates a Query object that can perform different queries on the specified table 
    Queries that fail must return False
    Queries that succeed should return the result or True
    Any query that crashes (due to exceptions) should return False
    """
    def __init__(self, table):
        self.table = table
        pass

    
    """
    # internal Method
    # Read a record with specified RID
    # Returns True upon succesful deletion
    # Return False if record doesn't exist or is locked due to 2PL
    """
    def delete(self, primary_key):
        try:
            self.table.delete_record(primary_key)
        except AssertionError:
            return False
        return True
    
    
    """
    # Insert a record with specified columns
    # Return True upon succesful insertion
    # Returns False if insert fails for whatever reason
    """
    def insert(self, *columns):
        columnList=list(columns)
        try:
            result = self.table.insert_record(columnList)
        except AssertionError:
            return False
        return result

    
    """
    # Read matching record with specified search key
    # :param search_key: the value you want to search based on
    # :param search_key_index: the column index you want to search based on
    # :param projected_columns_index: what columns to return. array of 1 or 0 values.
    # Returns a list of Record objects upon success
    # Returns False if record locked by TPL
    # Assume that select will never be called on a key that doesn't exist
    """
    def select(self, search_key, search_key_index, projected_columns_index):
        return self.select_version(search_key, search_key_index, projected_columns_index, 0)

    
    """
    # Read matching record with specified search key
    # :param search_key: the value you want to search based on
    # :param search_key_index: the column index you want to search based on
    # :param projected_columns_index: what columns to return. array of 1 or 0 values.
    # :param relative_version: the relative version of the record you need to retreive.
    # Returns a list of Record objects upon success
    # Returns False if record locked by TPL
    # Assume that select will never be called on a key that doesn't exist
    """
    def select_version(self, search_key, search_key_index, projected_columns_index, relative_version):
        columnsList: list = []
        ridList: list = []
        recordList: list = []
        if(search_key_index!=self.table.primary_key_col):
            #Convert secondary key to list of primary keys
            ridList.append(search_key)
        else:
            ridList.append(self.table.index.get_rid(search_key))
        for rid in ridList:
            for _ in range(0, abs(relative_version)):
                rid=self.table.get_indirection_value(rid)
            columnsList.append(self.table.get_latest_column_values(rid, projected_columns_index))
        for columns in columnsList:
            record = Record(rid, search_key, columns)
            recordList.append(record)
        return recordList
    
    """
    # Update a record with specified key and columns
    # Returns True if update is succesful
    # Returns False if no records exist with given key or if the target record cannot be accessed due to 2PL locking
    """
    def update(self, primary_key, *columns):
        columnList=list(columns)
        #record1 = self.select_version(primary_key, 0, [1, 1, 1, 1, 1], 0)[0]
        try:
            result = self.table.update_record(primary_key,columnList)
        except AssertionError:
            return False
        #assert(result)
        #record2 = self.select_version(primary_key, 0, [1, 1, 1, 1, 1], -2)[0]
        #rid = self.table.index.get_rid(primary_key)
        #print(rid, " | " ,self.table.get_indirection_value(rid))
        #print(record1.columns)
        #print(record2.columns)
        #print(self.table.page_ranges[0].base_pages[0].get_column_of_record(-1,0) )
        #assert(record1.columns == record2.columns)
        return result

    
    """
    :param start_range: int         # Start of the key range to aggregate 
    :param end_range: int           # End of the key range to aggregate 
    :param aggregate_columns: int  # Index of desired column to aggregate
    # this function is only called on the primary key.
    # Returns the summation of the given range upon success
    # Returns False if no record exists in the given range
    """
    def sum(self, start_range, end_range, aggregate_column_index):
        return self.sum_version(start_range, end_range, aggregate_column_index, 0)

    
    """
    :param start_range: int         # Start of the key range to aggregate 
    :param end_range: int           # End of the key range to aggregate 
    :param aggregate_columns: int  # Index of desired column to aggregate
    :param relative_version: the relative version of the record you need to retreive.
    # this function is only called on the primary key.
    # Returns the summation of the given range upon success
    # Returns False if no record exists in the given range
    """
    def sum_version(self, start_range, end_range, aggregate_column_index, relative_version):
        aggregateSum: int = 0
        anyRecords: bool = False
        column_index_list: list =[]
        for index in range(0, self.table.num_columns):
            if index == aggregate_column_index:
                column_index_list.append(1)
            else:
                column_index_list.append(0)
        print
        for key in range(start_range, end_range+1):
            try:
                record = self.select_version(key, self.table.primary_key_col, column_index_list, relative_version)
                aggregateSum+=record[0].columns[0]
                anyRecords=True
            except:
                continue
        if anyRecords==False:
            return False
        return aggregateSum
    """
    incremenets one column of the record
    this implementation should work if your select and update queries already work
    :param key: the primary of key of the record to increment
    :param column: the column to increment
    # Returns True is increment is successful
    # Returns False if no record matches key or if target record is locked by 2PL.
    """
    def increment(self, key, column):
        r = self.select(key, self.table.primary_key_col, [1] * self.table.num_columns)[0]
        if r is not False:
            updated_columns = [None] * self.table.num_columns
            updated_columns[column] = r.columns[column] + 1
            u = self.update(key, *updated_columns)
            return u
        return False
