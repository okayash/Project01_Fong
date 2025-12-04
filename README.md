# Heuristic Query Optimization Project


# Compilation & Execution Instructions 

## Commands or steps needed to build and run your program. 

1. Download the ZIP file
2. python3 -m venv venv
source venv/bin/activate
3. The program can be executed within the directory via the following commands:

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
Inputs must be an SQL query text file containing only alphanumeric characters with schema definitions containing attributes, followed by SQL queries.
1. Schema definitions are in the form: 
TableName(attr1, attr2, ..., 
PRIMARY KEY(...), 
UNIQUE(...));

2. -- SQL Query -- will be written above the SQL queries

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

IN

NOT IN


# Output Description 
## What files or console outputs are generated.
The console output will then generate a canonical query tree, optimized query tree, an optimized SQL query, and the heuristic query rules applied when developing the optimized query tree.

## How to interpret the output (e.g., structure of the query tree, optimization steps). 
The output will initally show your input SQL query from the .txt file provided.
Then, a canonical query tree is created with:
- tables are at the bottom as relations
- join, group by, having, select, will be above
- project is at the top
Each rule applied is then output, along with the change in the query tree if applicable:
1	Cascade of Selections	
2	Push Selections Down	
3	Apply Selections with Smallest Selectivity First	
4	Replace Cartesian Product + Selection → Join	
5	Push Projections Down	
The optimized query tree is output, which is the final query tree after all rules have been checked and applied.

an SQL query with refinements will also be output, which is the optimized query tree converted to SQL. 

Finally, a description of the rules applied will be output.

issues: the trees kinda are different from the expected outputs, even if the correct rules are being applied, idk
- exists/not exists isn't really working yet.

some difficulies:
- ensuring that not all selections are pushed down, since some need to be converted to joins with cartsian products.
- 
