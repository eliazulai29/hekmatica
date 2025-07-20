
import os
import pytest
from Hekmatica.tools import write_to_file


def test_write_to_file_creates_file(tmp_path):
    file_path = tmp_path / "subdir" / "test.txt"
    data = "Hello, world!"
    write_to_file(str(file_path), data)

    assert file_path.exists(), "File should be created"
    assert file_path.read_text() == data, "Data written to the file should match the input data"


def test_write_to_file_handles_ioerror(tmp_path, mocker):
    file_path = tmp_path / "test.txt"
    data = "Test data"

    # Mock open to raise an IOError
    mock_open = mocker.patch('builtins.open', side_effect=IOError("Permission denied"))
    with pytest.raises(IOError):
        write_to_file(str(file_path), data)

    mock_open.assert_called_once_with(str(file_path), 'w')


@pytest.mark.parametrize("invalid_path", ["/", None, "", 123])
def test_write_to_file_with_invalid_path_raises_exception(invalid_path):
    data = "Some data"

    with pytest.raises(Exception):
        write_to_file(invalid_path, data)
