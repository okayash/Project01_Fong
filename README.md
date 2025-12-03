# Heuristic Query Optimization Project


# Compilation & Execution Instructions 

## Commands or steps needed to build and run your program. 

1. Download the ZIP file
2. The program can be executed within the directory via the following commands:

For console output: python3 Project1/optimizer.py  [filename].txt

To store output into a text file: python3 Project1/optimizer.py [filename].txt > output.txt

## Any external libraries, tools, or dependencies required. 

Python Version 3.7+.

### The external libaries only include Python standard libraries, including:

re - Regular Expression Operators

os - Operating System Interfaces

sys - System Parameters and Functions




# Input Requirements 
## Expected input format (e.g., SQL query text file, command-line input).
Inputs must be an SQL query text file with schema definitions containing attributes, followed by SQL queries.

## Any assumptions about schema names, attributes, or query structure. 
### Assumptions: 

### Schema Names:
The tables are given with the schema name first, without the need of the CREATE TABLE command in front.

### Attributes:
Each attribute is seperated by a comma and new line.

### Query Structure
Each query ends with ;.
The SQL syntax supported include:
SELECT using lists and aggregation
FROM using simple tables, alias, joins (inner, left-outer, right-outer, full-outer, anti-, semi-)
WHERE
GROUP BY
HAVING
ORDER BY

Unnesting Rules:
IN/EXISTS
NOT IN/NOT EXISTS


# Output Description 
## What files or console outputs are generated.
The console output will then generate a canonical query tree, optimized query tree, an optimized SQL query, and the heuristic query rules applied when developing the optimized query tree.

## How to interpret the output (e.g., structure of the query tree, optimization steps). 
The output will initally show your input SQL query from the .txt file provided.
Then, a canonical query tree is created 
The optimized query tree
an SQL query with refinements
and a description of the rules applied
