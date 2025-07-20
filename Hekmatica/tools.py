
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def write_to_file(file_path, data):
    """
    Writes data to the specified file, ensuring the directory exists and errors are logged.

    :param file_path: Path to the file to write data
    :param data: Data to be written to the file
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w') as f:
            f.write(data)
        logging.info(f"Data successfully written to {file_path}")
    except IOError as e:
        logging.error(f"Failed to write to {file_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred while writing to {file_path}: {e}")
        raise
