# Heuristic Query Optimization Project

## Compilation & Execution Instructions 

## Commands or steps needed to build and run your program. 
## Any external libraries, tools, or dependencies required. 

Python Libraries:

re - Regular Expression Operators

os - Operating System Interfaces

sys - System Parameters and Functions

To execute the program, use the following commands:

For console output: python3 Project1/optimizer.py  [filename].txt

To store output into a text file: python3 Project1/optimizer.py [filename].txt > output.txt


# Input Requirements 
## Expected input format (e.g., SQL query text file, command-line input).
Inputs must be an SQL query text file with schema definitions containing attributes, followed by SQL queries.

## Any assumptions about schema names, attributes, or query structure. 
Assumptions: 
Schema Names:
The tables are given with the schema name first, without the need of the CREATE TABLE command in front.

Attributes:
Each attribute is seperated by a comma and new line.

Query Structure
Each query ends with ;

# Output Description 
## What files or console outputs are generated.

## How to interpret the output (e.g., structure of the query tree, optimization steps). 
The output will initally show your input SQL query from the .txt file provided.
Then, a canonical query tree is created 
