"""! @file main.py
@brief Main entry point for the task scheduler application
@author Samuel Longauer

@defgroup main Main Module
@brief Handles application startup and command line interface
"""

import sys
from task_scheduler.cli import parse_args

def main():
    """! @brief Main application entry point
    
    @details Initializes command line argument parsing and starts the application.
    Delegates all functionality to the parse_args() function from the CLI module.
    
    @exception SystemExit Propagates any exit commands from argument parsing
    """
    parse_args()

if __name__ == "__main__":
    """! @brief Main execution block
    @details Entry point when script is run directly. Simply calls main() function.
    """
    main()
