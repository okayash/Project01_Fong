# Project01_Fong

Overview
In this project, you will develop a program that processes a single-block SQL query by applying heuristic optimizations. Your task is to optimize the initial query with heuristic techniques to improve execution efficiency.

Max Group Size
Students may work individually or in pairs for this project. Both members must actively contribute to all parts of the work. Each team submits a single deliverable with both names listed.
During demos or code reviews, both members should be able to explain any part of the project.

If you are looking for a partner, you may post in the Canvas discussion board created for group formation. Use it to connect with classmates who are also seeking partners before the project deadline.

 

Input Requirements 
SQL Query Input: The primary input for the program will be a single-block SQL query composed of standard SQL syntax and constructs such as:
SELECT (with attribute lists, and aggregation functions such as `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`)
FROM (one or more relations, with or without joins; simple table aliases (e.g., FROM Employee E) should be supported for readability and mapping)
WHERE (with conjunctive/disjunctive predicates) 
GROUP BY (for grouped aggregation) 
HAVING (for post-group filtering) 
ORDER BY (for sorting) 

Unnesting Rules (Extra Credits + 10 points): For extra credit, implement query unnesting transformations that convert nested subqueries into equivalent join-based forms. Your program should support common patterns such as:  
`IN`/`EXISTS` -> semi-join 
`NOT IN`/`NOT EXISTS` -> anti-join
 

Output Requirements 
Canonical Query Tree 
Output the initial canonical query tree generated from the input SQL query. This tree should represent the logical flow and structure of the query before any optimizations are applied. Its outputting format can be, but not limited to, graphical or a structured textual representation. 
Optimized Query Tree
After applying heuristic optimizations, output the optimized query tree reflecting the changes and enhancements made to improve the query's performance.
Your program must output the query tree after each major transformation step to illustrate the effect of every optimization rule. This ensures transparency and traceability in your optimizer's reasoning process. 
Refined SQL Query (Extra Credit + 10 points) 
Convert the optimized query tree back into SQL format. This should be a runnable SQL Query that represents the optimized version of the original input.
 

Deliverables
Submit a single ZIP file named: Project01_LastName1_LastName2.zip (or Project01_LastName.zip if working individually) 

The ZIP file must include: 

Source Code: Well-commented source code in the language of your choice.
README File: Include a short README.txt or README.md that contains: 
Compilation & Execution Instructions 
Commands or steps needed to build and run your program. 
Any external libraries, tools, or dependencies required. 
Input Requirements 
Expected input format (e.g., SQL query text file, command-line input).
Any assumptions about schema names, attributes, or query structure. 
Output Description 
What files or console outputs are generated.
How to interpret the output (e.g., structure of the query tree, optimization steps). 
