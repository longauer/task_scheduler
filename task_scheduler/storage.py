"""! @file storage.py
@brief JSON data storage handling module
@author Samuel Longauer

@defgroup storage Storage Module
@brief Provides JSON serialization/deserialization utilities
"""

import json

class Storage:
    """! @brief Static class for JSON data storage operations
    
    @ingroup storage
    
    Provides static methods for saving and loading data using JSON format.
    Handles file operations and JSON serialization/deserialization.
    """
    
    @staticmethod
    def save(file_path, data):
        """! @brief Save data to JSON file
        
        @param file_path Path to target JSON file
        @param data Serializable data to save
        @exception TypeError If data contains non-serializable objects
        @exception IOError If file write operation fails
        """
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

    @staticmethod
    def load(file_path):
        """! @brief Load data from JSON file
        
        @param file_path Path to source JSON file
        @return Deserialized Python data structure
        @exception FileNotFoundError If specified file doesn't exist
        @exception json.JSONDecodeError If file contains invalid JSON
        @exception IOError If file read operation fails
        """
        with open(file_path, "r") as file:
            return json.load(file)
