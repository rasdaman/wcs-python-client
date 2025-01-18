from datetime import datetime
from wcs.model import _list_to_str, _bound_to_str


# ----------------------------------------------------------------------------
# _list_to_str
def test_bound_to_str_with_datetime_date_only():
    bound = datetime(2023, 10, 5)
    result = _bound_to_str(bound)
    assert result == '"2023-10-05"'


def test_bound_to_str_with_full_datetime():
    bound = datetime(2023, 10, 5, 14, 30, 45)
    result = _bound_to_str(bound)
    assert result == '"2023-10-05T14:30:45"'


def test_bound_to_str_with_non_datetime():
    bound = 42
    result = _bound_to_str(bound)
    assert result == '42'


def test_bound_to_str_with_str():
    bound = "example"
    result = _bound_to_str(bound)
    assert result == 'example'


def test_bound_to_str_with_float():
    bound = 3.14
    result = _bound_to_str(bound)
    assert result == '3.14'


def test_bound_to_str_with_none():
    bound = None
    result = _bound_to_str(bound)
    assert result == 'None'


def test_bound_to_str_with_bool():
    bound = True
    result = _bound_to_str(bound)
    assert result == 'True'

    bound = False
    result = _bound_to_str(bound)
    assert result == 'False'


# ----------------------------------------------------------------------------
# _list_to_str

def test_list_to_str_with_mixed_types():
    lst = [1, 'two', 3.0, True]
    sep = ' | '
    result = _list_to_str(lst, sep)
    assert result == '1 | two | 3.0 | True'


def test_list_to_str_with_empty_list():
    lst = []
    sep = ', '
    result = _list_to_str(lst, sep)
    assert result == ''


def test_list_to_str_with_empty_separator():
    lst = ['a', 'b', 'c']
    sep = ''
    result = _list_to_str(lst, sep)
    assert result == 'abc'
