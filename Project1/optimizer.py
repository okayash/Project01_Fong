'''
Name: Ashley Fong
CS: 5700 Database Systems
Project: Heuristic Query Optimizer
San Yeung

'''

# Contains unnesting rules with semi/anti-join and also converts optimized query tree to SQL.

'''
Python Standard Libraries:
'''
import re
import os
import sys

'''
Constant symbols/phrases representing SQL operations that will appear in final trees.
'''
PROJECT = "π"
SELECT = "σ"
HAVING = "HAVING"
JOIN = "⋈"
SEMI_JOIN = "SEMI_JOIN"
ANTI_JOIN = "ANTI_JOIN"
OUTER_JOIN = "OUTER_JOIN"
CARTESIAN = "CARTESIAN"
RELATION = "Relation: "
GROUP = "GROUP_BY"
SORT = "ORDER_BY"

class QueryNode:
    '''
    class QueryNode
    Purpose: This class creates a node, representing an SQL/relational algebra 
    operation, that will be in the final canonical and optimized query trees.
    '''
    def __init__(
        self,
        node_type, # operation type
        data="", 
        left=None, # node to the left aka left child node pointer
        right=None, # node to the right aka right child node pointer
        attributes=None, # attributes like SSN, etc
        join_condition="", # join condition if node is a join node
        selectivity=1.0 # selectivity 
    ):
        # store parameters
        self.node_type = node_type
        self.data = data # things that are also stored in the SQL commnad 
        self.left = left
        self.right = right
        self.attributes = attributes # query attributes
        self.join_condition = join_condition
        self.selectivity = selectivity

    def __str__(self, level=0):
        '''
        Purpose: Readable representation of a query tree that will be outputted.
        '''
        
        indent = "  " * level # more indents = deeper in tree
        result = f"{indent}{self.node_type}" # print indent, then the operation type.
        
        if self.data:
            result += f"_{self.data}" # add SQL additional data
        if self.join_condition:
            result += f" [{self.join_condition}]" # add join condition if it's a join.
        
        result += "\n" # add new line
        
        if self.left:
            result += self.left.__str__(level + 1) # print the lower query tree of the left child
        if self.right:
            result += self.right.__str__(level + 1) # print the lower query tree of the right
            
        return result

class SQLParser:
    '''

    class SQLParser
    Purpose: Parse SQL Queries that are inputted into each part of the syntax.

    '''
    
    def __init__(self, query, schema):
        '''

        store each SQL clause/syntax portion.

        '''
        self.query = self._normalize_query(query)
        self.schema = schema
        self.select_clause = ""
        self.from_clause = ""
        self.where_clause = ""
        self.group_by_clause = ""
        self.having_clause = ""
        self.order_by_clause = ""
        self.table_aliases = {}
        
    def _normalize_query(self, query):
        # Ignore comments in the query that start with --.
        query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)

        # Remove any new lines.
        query = re.sub(r'\s+', ' ', query)
        return query.strip() # remove excess spaces
    
    def parse(self):
        '''
        def parse
        Purpose: Using RE libarary, we extract each part of the SQL query into its individual parts.
        '''
        query = self.query
        
        # Search for SELECT ... FROM by using REGEX with any cases and any # of lines, if matching, remove white space 
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if select_match:
            self.select_clause = select_match.group(1).strip()
        
        # Search FROM ... to WHERE / other potential next clauses with any cases and any # of lines
        from_match = re.search(r'FROM\s+(.*?)(?:WHERE|GROUP BY|HAVING|ORDER BY|$)', 
                              query, re.IGNORECASE | re.DOTALL)
        if from_match:
            self.from_clause = from_match.group(1).strip() # if we find from, store it and remove white space
            self._parse_table_aliases() # obtain any necessary table alias.

        
        # Search WHERE through keyword to potential next clauses with any cases and any # of lines
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|HAVING|ORDER BY|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if where_match:
            self.where_clause = where_match.group(1).strip()
        
        # Search GROUP BY through keyword to potential next clauses with any cases and any # of lines
        group_match = re.search(r'GROUP BY\s+(.*?)(?:HAVING|ORDER BY|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if group_match:
            self.group_by_clause = group_match.group(1).strip()
        
        # Search HAVING through keyword to potential next clauses with any cases and any # of lines
        having_match = re.search(r'HAVING\s+(.*?)(?:ORDER BY|$)', 
                                query, re.IGNORECASE | re.DOTALL)
        if having_match:
            self.having_clause = having_match.group(1).strip()
        
        # Search ORDER BY through keyword to potential next clauses/end of SQL query with any cases and any # of lines
        order_match = re.search(r'ORDER BY\s+(.*?)(?:;|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if order_match:
            self.order_by_clause = order_match.group(1).strip()
        
        return {
            # return all parts of SQL query in a dictionary
            'select': self.select_clause,
            'from': self.from_clause,
            'where': self.where_clause,
            'group_by': self.group_by_clause,
            'having': self.having_clause,
            'order_by': self.order_by_clause,
            'aliases': self.table_aliases
        }
    
    def _parse_table_aliases(self):
        '''
        We need to obtain any aliases of the tables in FROM
        '''
        # If seperated by commas
        if ',' in self.from_clause:
            # obtain parts seperated by commas
            items = [x.strip() for x in self.from_clause.split(',')]
            for item in items:
                # skip if items are JOIN
                if re.search(r'\s+JOIN\s+', item, re.IGNORECASE):
                    continue
                parts = item.split() # split item by space
                if len(parts) >= 2:
                    # if table has alias --> Relation goes with alias R
                    self.table_aliases[parts[1]] = parts[0]
                else:
                    # if no alias, Relation is just Relation
                    self.table_aliases[parts[0]] = parts[0]
        
        # JOIN 
        parts = re.split(r'\s+(?:INNER\s+|LEFT\s+OUTER\s+|RIGHT\s+OUTER\s+|FULL\s+OUTER\s+)?JOIN\s+', 
                        self.from_clause, flags=re.IGNORECASE) # remove from and join
        
        for part in parts:
            # strip ON
            part = re.split(r'\s+ON\s+', part, flags=re.IGNORECASE)[0]
            if ',' not in part: # skip any comma seperated parts
                # match table alias
                match = re.search(r'(\w+)\s+(\w+)$', part.strip())
                if match:
                    table, alias = match.groups()
                    self.table_aliases[alias] = table
                else:
                    # match table name
                    match = re.search(r'(\w+)$', part.strip())
                    if match:
                        table = match.group(1)
                        self.table_aliases[table] = table

class QueryTreeBuilder:
    '''
    class QueryTreeBuilder
    Purpose: functions to build query trees from SQL queries.
    '''
    
    def __init__(self, parsed_query, schema):
        self.parsed = parsed_query
        self.schema = schema
        self.aliases = parsed_query['aliases']
        
    def build_canonical_tree(self):
        '''
        Purpose: To build the canonical tree from the inital SQL query with no optimizations.
        '''

        # we build starting from FROM clause to put relation tables at the bottom of the tree
        root = self._build_from_tree()
        
        # WHERE goes on top of FROM in tree
        if self.parsed['where']: # does SQL have where
            select_node = QueryNode(SELECT, self.parsed['where']) # create a node for this where 
            select_node.left = root # attaches tree to root
            root = select_node # root is now where node
        
        # GROUP BY is next on tree
        if self.parsed['group_by']: # SQL has group by?
            group_node = QueryNode(GROUP, self.parsed['group_by']) # create group by node
            group_node.left = root # attach tree to root
            root = group_node # root is now group by node

            # HAVING is above     
            if self.parsed['having']: # SQL has having?
                having_node = QueryNode(HAVING, f"{self.parsed['having']}") # create having node
                having_node.left = root # attach tree to root
                root = having_node # root is now having node
        
        # Add projection
        if self.parsed['select'] != '*': # if SQL select is not *
            proj_node = QueryNode(PROJECT, self.parsed['select']) # create projection node
            proj_node.left = root # attach tree to root
            root = proj_node # root is now projection node
        
        # ORDER_BY on top of tree
        if self.parsed['order_by']: # check if SQL order by exists
            sort_node = QueryNode(SORT, self.parsed['order_by']) # create sort node
            sort_node.left = root # attach tree to root
            root = sort_node # root is now sort node
        
        return root
    
    def _build_from_tree(self):
        '''
        Build a tree starting from the FROM clause
        '''

        from_clause = self.parsed['from'] # get FROM ...
        joins = self._parse_joins(from_clause) # parse any joins in FROM
        
        # we have no joins and are dealing with a single table:
        if not joins:
            raw = from_clause.split()[0] # get table name
            table_name = self.aliases.get(raw, raw) # obtain alias if necessary
            return QueryNode(RELATION, table_name) # create relation node
        
        # we have JOINS to process:

        root = None

        # each 'join' in joins becomes left_table, right_table
        for join in joins:
            if root is None:
                root = QueryNode(RELATION, join['left_table'])
            
            # node for RHS table
            right_node = QueryNode(RELATION, join['right_table'])
            
            
            join_type = join['type'] # check join type
            if 'OUTER' in join_type: # for outer joins
                join_node = QueryNode(OUTER_JOIN, join_type, join_condition=join['condition'])
            elif join_type == 'CARTESIAN': # for cartesian products
                join_node = QueryNode(CARTESIAN, "")
            else: # assuming inner join is default ... 
                join_node = QueryNode(JOIN, join_type, join_condition=join['condition'])
            
            join_node.left = root # attach exisiting tree on LHS
            join_node.right = right_node # attach right node
            root = join_node # JOIN is now on the root
        
        return root
    
    def _parse_joins(self, from_clause):
        '''

        parse JOIN in FROM into dictionary format

        '''
        joins = []
        
        # checking for JOIN ... 
        if re.search(r'\s+JOIN\s+', from_clause, re.IGNORECASE): # searching for JOIN keyword
            # check for LHS (potential alias LHS) JOIN of types (inner/outer LEFT/RIGHT/FULL) RHS (potential alias of RHS)... 
            join_pattern = r'(\w+)\s+(\w+)\s+((?:INNER\s+|LEFT\s+OUTER\s+|RIGHT\s+OUTER\s+|FULL\s+OUTER\s+)?JOIN)\s+(\w+)\s+(\w+)\s+ON\s+([^,]+?)(?=(?:INNER|LEFT|RIGHT|FULL|$))'
            matches = list(re.finditer(join_pattern, from_clause, re.IGNORECASE)) 

            # for each match found, we store the join information in a dictionary
            for i, match in enumerate(matches):
                if i == 0:
                    left_table = match.group(1)   # if i is the first run, table is from SQL, else use right table of prev join.
                    left_alias = match.group(2)   
                else:
                    left_table = joins[-1]['right_table']  # previous join's right side ("B")
                    left_alias = joins[-1]['right_alias']  # previous join's right alias ("b"

                joins.append({ # we add the left table + alias + type of join + right table + alias + join condition to a dictionary
                    'left_table': left_table, 
                    'left_alias': left_alias,
                    'type': match.group(3).strip().upper(),
                    'right_table': match.group(4),
                    'right_alias': match.group(5),
                    'condition': match.group(6).strip()
                })
        
        # check for comma separated tables (CARTESIAN PRODUCT)

        if ',' in from_clause and not joins: # we split FROM by comma if no joins found
            tables = [t.strip() for t in from_clause.split(',')] 

            for i in range(len(tables) - 1):

                # left table ... 
                parts_left = tables[i].split() # split left table and alias
                l_table = parts_left[0] # obtain table name

                if (len(parts_left) > 1): # obtain alias if exists
                    l_alias = parts_left[1] # alias
                else:
                    l_alias = l_table # alias is table name if no alias
                
                # right table ...
                parts_right = tables[i + 1].split() # split right table and alias
                r_table = parts_right[0] # obtain table name
                if (len(parts_right) > 1): # obtain alias if exists
                    r_alias = parts_right[1] # alias
                else:
                    r_alias = r_table
                
                joins.append({ # ADD ALL OF THIS TO A DICTIONARY
                    'left_table': l_table if i == 0 else joins[-1]['right_table'], # for the first join, the left table is the first table appearing \
                    # for tables after, the left table is the right table of the previous join.
                    'left_alias': l_alias if i == 0 else joins[-1]['right_alias'],
                    'type': 'CARTESIAN',
                    'right_table': r_table, 
                    'right_alias': r_alias,
                    'condition': ''
                })
        
        return joins

class QueryOptimizer:

    '''

    class QueryOptimizer
    Purpose: Store the functions that will apply the five heuristic optimization rules and the unnesting rules.

    '''
    
    def __init__(self, schema, aliases):
        self.schema = schema
        self.aliases = aliases
        self.optimizations_applied = []
        
    def optimize(self, root):
        '''
       
        Apply Heuristic Optimization Rules
        
        1	Cascade of Selections	Break conjunctive selection conditions into a sequence of single-condition selections.
        2	Push Selections Down	Move selections as close as possible to the base relations to reduce intermediate results.
        3	Apply Selections with Smallest Selectivity First	Reorder leaf nodes and attached selections so that the most restrictive (smallest selectivity) filters are applied earliest.
        4	Replace Cartesian Product + Selection → Join	Combine cross-products followed by join conditions into a single ⋈ operator.
        5	Push Projections Down	Apply projections early to eliminate unnecessary attributes before joins.

        call each function to check/apply each rule
      
        '''
        self.optimizations_applied = [] # remember which rules were applied ....
        
        # after each rule is applied, we print out the current status of the query tree.

        # Break conjunctive selection conditions into a sequence of single-condition selections.
        # Move selections as close as possible to the base relations to reduce intermediate results.

        root = self._break_and_push_selections(root)
        print("Rule 1 & 2")
        print(root)

        # Reorder leaf nodes and attached selections so that the most restrictive (smallest selectivity) filters are applied earliest.
        root = self._order_by_selectivity(root)
        print("Rule 3")
        print(root)

        # Combine cross-products followed by join conditions into a single ⋈ operator.
        root = self._cartesian_to_join(root)
        print("Rule 4")
        print(root)
        
        # Apply projections early to eliminate unnecessary attributes before joins.
        root = self._push_projections(root)
        print("Rule 5")
        print(root)
        
        # Extra credit: unnest IN / NOT IN subqueries into semi/anti-joins
        root = self._unnest_subqueries(root)
        print(f'Unnest Rules')
        print(root)
        
        return root
    
    def _break_and_push_selections(self, node):
        '''

        Function that will break multiple selection conditions into seperate single selection conditions, and will also push selections

        '''

        if node is None: # if the node is empty, do nothing.
            return None
        
        if node.node_type == SELECT: # check the SELECT of the SQL for a SELECT node
            conditions = self._split_conditions(node.data) 

            if len(conditions) > 1: # if there are multiple conditions, we will apply rule 1 below
                self.optimizations_applied.append(
                    "Rule #1: Cascade of Selections"
                )
            
            current = node.left

            for condition in reversed(conditions): # we reverse the conditions so the first condition is at the top of the tree.
                select_node = QueryNode(SELECT, condition) # we create a new select node for condition in for loop
                select_node.selectivity = self._estimate_selectivity(condition) # estimate selectivity 
                select_node.left = current # attach sub-tree under our SELECT
                current = select_node # this select node becomes our current.
            
            result = self._push_selection_down(current) # push selections to bottom of tree if we can
            
            if len(conditions) > 0: # if there are conditions in the SELECT, we try to apply rule 2 and mark as applied.
                self.optimizations_applied.append(
                    "Rule #2: Push Selections Down"
                )
            
            return result
        
        node.left = self._break_and_push_selections(node.left) # process children subtrees with recursion 
        node.right = self._break_and_push_selections(node.right)
        
        return node
    
    def _split_conditions(self, condition):
        '''

        Split a conjunctive condition into individual conditions if it is not inside parentheses.
        - we only split when our nested_parenthesis value is 0, so we are at the top level

        '''
        parts = [] # initalize list of conditions
        current = ""
        nested_parenthesis = 0 # keep track of how many parenthesis we encounter
        i = 0
        n = len(condition)
        
        while i < n: # go through the string
            char = condition[i]
            if char == '(': # we are within another layer of nested parenthesis
                nested_parenthesis += 1
            elif char == ')':
                nested_parenthesis -= 1
            
            is_and = False # check if we have an AND at the top level

            if nested_parenthesis == 0 and i + 3 <= n: # if we are at top level and have enough chars for AND

                characters = condition[i:i+3].upper() # check next three characters 
                if characters == 'AND': 
                    before_AND = (i == 0) or condition[i-1].isspace() or condition[i-1] in ')' # check before AND
                    after_AND = (i + 3 == n) or condition[i+3].isspace() or condition[i+3] in '(' # check after AND
                    if before_AND and after_AND: 
                        is_and = True # we have a valid AND

            if is_and:
                # save condition
                if current.strip():
                    parts.append(current.strip())
                current = ""
                i += 3 # ignore the AND
                while i < n and condition[i].isspace(): # ignore whitespace
                    i += 1
                continue
            
            current += char 
            i += 1
            
        if current.strip(): # add last condition
            parts.append(current.strip())

        return parts if parts else [condition] # return conditions
    
    def _alias_to_table_names(self, tables):
        '''
        Obtain alias from table names
        '''
        resolved = set()
        for t in tables: # for each table, we get its alias if it exists
            resolved.add(self.aliases.get(t, t))
        return resolved

    def _push_selection_down(self, node):
        '''

        Rule 2: Push a selection node down the tree
        - push deeper selections in a chain first
        - we stop pushing if child is groupby/having/outer join
        - check to ensure if we are pushing potential JOINs by checking child nodes and stop if we are

        '''
        if node is None or node.node_type != SELECT: # we only need a SELECT node ...
            return node
        
        child = node.left # get child node

        # if child is a SELECT, we push the child first
        if child and child.node_type == SELECT:
            node.left = self._push_selection_down(child)
            return node
        
        # stop pushing child if is a group by/having/outer join... 
        if child and child.node_type in [GROUP, HAVING, OUTER_JOIN]:
            return node
        
        # for join/cartesian product child nodes
        if child and child.node_type in [JOIN, CARTESIAN]:
            referenced_aliases = self._get_referenced_tables(node.data) # obtain necessary alias of table in conditions
            referenced_tables = self._alias_to_table_names(referenced_aliases) # obtain these tables
            
            left_tables = self._get_node_tables(child.left) # find tables in left subtree
            right_tables = self._get_node_tables(child.right) # tables in right subtree
            
            # check if this is a join 
            is_join_condition = (
                referenced_tables.issubset(left_tables.union(right_tables)) and
                not referenced_tables.issubset(left_tables) and
                not referenced_tables.issubset(right_tables)
            )
            
            # if child is cartesian and condition is a join condition, we stop pushing because we need to convert cartisan to join later
            if is_join_condition and child.node_type == CARTESIAN:
                return node
            
            if referenced_tables.issubset(left_tables): # if only left tables are needed, we push it down to left child
                node.left = child.left # focus on left child
                child.left = self._push_selection_down(node) # push selection down
                return child
            
            if referenced_tables.issubset(right_tables): # if only right tables are needed
                node.left = child.right
                child.right = self._push_selection_down(node)
                return child
            
        return node

    def _has_top_level_or(self, expr):
        '''
        '''
        nested_parenthesis = 0
        i = 0
        n = len(expr)
        while i < n:
            ch = expr[i]
            if ch == '(':
                nested_parenthesis += 1
            elif ch == ')':
                nested_parenthesis -= 1

            if nested_parenthesis == 0 and i + 2 <= n:
                characters = expr[i:i+2].upper()
                if characters == 'OR':
                    before_ok = (i == 0) or expr[i-1].isspace() or expr[i-1] in ')'
                    after_ok = (i + 2 == n) or expr[i+2].isspace() or expr[i+2] in '('
                    if before_ok and after_ok:
                        return True
            i += 1
        return False

    def _selectivity_key(self, node):
        '''
        '''
        return node.selectivity
    
    def _order_by_selectivity(self, node):
        '''
        Rule 3: Order selections by selectivity
        '''
        if node is None:
            return None
        
        if node.node_type == SELECT:
            selections = []
            current = node
            while current and current.node_type == SELECT:
                selections.append(current)
                current = current.left
                
            if len(selections) > 1:
                # Skip Rule 3 if any selection has a top-level OR (input2 case)
                if any(self._has_top_level_or(sel.data) for sel in selections):
                    selections[-1].left = self._order_by_selectivity(current)
                    return node

                selections.sort(key=self._selectivity_key)
                self.optimizations_applied.append("Rule #3: Apply Selections with Smallest Selectivity First")
                
                root = selections[0]
                for i in range(len(selections) - 1):
                    selections[i].left = selections[i+1]
                selections[-1].left = current
                
                selections[-1].left = self._order_by_selectivity(current)
                return root
        
        node.left = self._order_by_selectivity(node.left)
        node.right = self._order_by_selectivity(node.right)
        return node
    
    def _cartesian_to_join(self, node):
        """Rule 4: Convert Cartesian product + selection to join"""
        if node is None:
            return None
        
        # Check if this is a SELECT with a join condition
        if node.node_type == SELECT and self._is_join_condition(node.data):
            # Find a cartesian product in the subtree that this join condition applies to
            cartesian_node, parent = self._find_applicable_cartesian(node.left, node.data)
            
            if cartesian_node is not None:
                join_node = QueryNode(JOIN, "INNER JOIN", join_condition=node.data)
                join_node.left = cartesian_node.left
                join_node.right = cartesian_node.right
                
                # Replace the cartesian in the tree
                if parent is None:
                    # The cartesian was directly under this select
                    result = join_node
                else:
                    # Replace in parent
                    if parent.left == cartesian_node:
                        parent.left = join_node
                    else:
                        parent.right = join_node
                    result = node.left
                
                self.optimizations_applied.append(
                    "Rule #4: Replace Cartesian Product + Selection → Join"
                )
                
                # Continue optimizing the result
                return self._cartesian_to_join(result)
        
        node.left = self._cartesian_to_join(node.left)
        node.right = self._cartesian_to_join(node.right)
        
        return node
    
    def _find_applicable_cartesian(self, node, condition, parent=None):
        """Find a cartesian product that the given join condition applies to"""
        if node is None:
            return None, None
        
        if node.node_type == CARTESIAN:
            # Check if this join condition applies to this cartesian
            refs = self._get_referenced_tables(condition)
            resolved_refs = self._alias_to_table_names(refs)
            left_tables = self._get_node_tables(node.left)
            right_tables = self._get_node_tables(node.right)
            
            # Join condition should reference both sides
            if (not resolved_refs.issubset(left_tables) and 
                not resolved_refs.issubset(right_tables) and
                resolved_refs.issubset(left_tables.union(right_tables))):
                return node, parent
        
        # Search left subtree
        result, p = self._find_applicable_cartesian(node.left, condition, node)
        if result:
            return result, p
        
        # Search right subtree
        return self._find_applicable_cartesian(node.right, condition, node)
    
    def _push_projections(self, node):
        """Rule 5: Push projections down to reduce intermediate result sizes"""
        if node is None:
            return None
        
        # First recursively process children
        node.left = self._push_projections(node.left)
        node.right = self._push_projections(node.right)
        
        # Only process if this is a projection node
        if node.node_type != PROJECT:
            return node
        
        # Mark that we're applying Rule 5
        if "Rule #5: Push Projections Down" not in self.optimizations_applied:
            self.optimizations_applied.append("Rule #5: Push Projections Down")
        
        # Parse the attributes being projected
        projected_attrs = self._parse_projection_attributes(node.data)
        
        # Collect additional attributes needed for operations above this point
        needed_attrs = self._collect_needed_attributes(node.left, projected_attrs)
        
        # Push projections down to each relation
        node.left = self._insert_projections(node.left, needed_attrs)
        
        return node
    
    def _parse_projection_attributes(self, proj_clause):
        '''
        '''
        if proj_clause == '*':
            return set()  # Keep all attributes
        
        attrs = set()
        # Split by comma, but be careful of function calls like COUNT(*)
        parts = [p.strip() for p in proj_clause.split(',')]
        
        for part in parts:
            # Handle aggregation functions: COUNT(E.Salary), SUM(...)
            func_match = re.match(r'(COUNT|SUM|AVG|MIN|MAX)\s*\((.*?)\)', part, re.IGNORECASE)
            if func_match:
                inner = func_match.group(2).strip()
                if inner != '*':
                    # Extract table.attr from inside function
                    attr_match = re.match(r'([A-Za-z_]\w*)\.([A-Za-z_]\w*)', inner)
                    if attr_match:
                        attrs.add((attr_match.group(1), attr_match.group(2)))
            else:
                # Regular attribute: E.Lname or just Lname
                attr_match = re.match(r'([A-Za-z_]\w*)\.([A-Za-z_]\w*)', part)
                if attr_match:
                    attrs.add((attr_match.group(1), attr_match.group(2)))
        
        return attrs
    
    def _collect_needed_attributes(self, node, base_attrs):
        """
        Traverse tree to collect all attributes needed:
        - Attributes in the projection
        - Attributes in join conditions
        - Attributes in selection predicates
        - Attributes in GROUP BY, HAVING, ORDER BY
        """
        needed = set(base_attrs)
        
        def traverse(n):
            if n is None:
                return
            
            # Collect from selections
            if n.node_type == SELECT or n.node_type == HAVING:
                refs = self._get_referenced_attributes(n.data)
                needed.update(refs)
            
            # Collect from joins
            elif n.node_type in [JOIN, SEMI_JOIN, ANTI_JOIN, OUTER_JOIN]:
                if n.join_condition:
                    refs = self._get_referenced_attributes(n.join_condition)
                    needed.update(refs)
            
            # Collect from GROUP BY
            elif n.node_type == GROUP:
                refs = self._get_referenced_attributes(n.data)
                needed.update(refs)
            
            # Collect from ORDER BY
            elif n.node_type == SORT:
                refs = self._get_referenced_attributes(n.data)
                needed.update(refs)
            
            traverse(n.left)
            traverse(n.right)
        
        traverse(node)
        return needed
    
    def _get_referenced_attributes(self, expression):
        """
        Extract all table.attribute references from an expression
        Returns set of (alias, attribute) tuples
        """
        attrs = set()
        # Match patterns like E.Lname, W.Pno, etc.
        matches = re.findall(r'([A-Za-z_]\w*)\.([A-Za-z_]\w*)', expression)
        for alias, attr in matches:
            attrs.add((alias, attr))
        return attrs
    
    def _insert_projections(self, node, needed_attrs):
        '''
        '''
        if node is None:
            return None
        
        # If this is a relation, add a projection above it
        if node.node_type == RELATION:
            # Find which attributes from this relation are needed
            relation_attrs = []
            for alias, attr in needed_attrs:
                # Check if this alias refers to this relation
                resolved_table = self.aliases.get(alias, alias)
                if resolved_table == node.data:
                    relation_attrs.append(f"{alias}.{attr}")
            
            # Only add projection if we're actually filtering attributes
            all_attrs = self._get_all_relation_attributes(node.data)
            if relation_attrs and all_attrs and len(relation_attrs) < len(all_attrs):
                proj_node = QueryNode(PROJECT, ", ".join(relation_attrs))
                proj_node.left = node
                return proj_node
            
            return node
        
        # For other nodes, recurse
        node.left = self._insert_projections(node.left, needed_attrs)
        node.right = self._insert_projections(node.right, needed_attrs)
        
        return node
    
    def _get_all_relation_attributes(self, table_name):
        """Get all attributes of a relation from schema"""
        if table_name in self.schema:
            return self.schema[table_name]['attributes']
        return []

    # ---------- Extra Credit: Unnest IN / NOT IN into semi/anti-joins ----------

    def _unnest_in_subquery(self, node, anti=False):
        """
        Convert a condition of the form:
            outer_col IN (SELECT inner_col FROM T [alias] [WHERE inner_pred])
        or
            outer_col NOT IN (SELECT inner_col FROM T [alias] [WHERE inner_pred])
        into a SEMI_JOIN (⋉) or ANTI_JOIN (▷) node.

        Assumes node.data is exactly that IN / NOT IN expression
        (true after Rule 1 splits on AND).
        """
        pattern = r"""
            ^\s*
            ([A-Za-z_]\w*\.[A-Za-z_]\w*)      # outer_col, e.g. E.Ssn
            \s+
            (?:NOT\s+IN|IN)                   # IN / NOT IN
            \s*\(
                \s*SELECT\s+
                ([A-Za-z_]\w*\.[A-Za-z_]\w*)  # inner_col, e.g. W.Essn
                \s+FROM\s+
                ([A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)?)  # table or "table alias"
                (?:\s+WHERE\s+(.*))?          # optional inner WHERE predicate
            \)\s*
            $
        """
        m = re.match(pattern, node.data, re.IGNORECASE | re.VERBOSE)
        if not m:
            return None  # pattern not supported
        
        outer_col = m.group(1)
        inner_col = m.group(2)
        from_part = m.group(3)
        inner_where = m.group(4)  # may be None

        # Parse table and alias from FROM part (e.g., "Works_On W" or "Works_On")
        parts = from_part.split()
        table_name = parts[0]

        # Build right subtree: relation (and maybe a selection on top)
        right_rel = QueryNode(RELATION, table_name)
        if inner_where and inner_where.strip():
            right_subtree = QueryNode(SELECT, inner_where.strip(), left=right_rel)
        else:
            right_subtree = right_rel

        # Left subtree is whatever was under the original σ node
        left_subtree = node.left

        # Build semi/anti-join node
        join_type = ANTI_JOIN if anti else SEMI_JOIN
        join_cond = outer_col + " = " + inner_col
        join_node = QueryNode(join_type, "", left=left_subtree, right=right_subtree,
                              join_condition=join_cond)

        return join_node

    def _unnest_subqueries(self, node):
        """
        Extra credit: unnest nested subquery patterns into semi/anti-joins.

        Supported:
          - col IN (SELECT col FROM T [WHERE ...])     -> SEMI_JOIN (⋉)
          - col NOT IN (SELECT col FROM T [WHERE ...]) -> ANTI_JOIN (▷)

        EXISTS/NOT EXISTS are only detected/logged.
        """
        if node is None:
            return None

        if node.node_type == SELECT:
            text = node.data

            # NOT IN -> anti-join
            if re.search(r'\bNOT\s+IN\s*\(\s*SELECT', text, re.IGNORECASE):
                new_node = self._unnest_in_subquery(node, anti=True)
                if new_node is not None:
                    self.optimizations_applied.append(
                        "Extra Credit: Converted NOT IN subquery to anti-join (▷)"
                    )
                    new_node.left = self._unnest_subqueries(new_node.left)
                    new_node.right = self._unnest_subqueries(new_node.right)
                    return new_node

            # IN -> semi-join
            if re.search(r'\bIN\s*\(\s*SELECT', text, re.IGNORECASE):
                new_node = self._unnest_in_subquery(node, anti=False)
                if new_node is not None:
                    self.optimizations_applied.append(
                        "Extra Credit: Converted IN subquery to semi-join (⋉)"
                    )
                    new_node.left = self._unnest_subqueries(new_node.left)
                    new_node.right = self._unnest_subqueries(new_node.right)
                    return new_node

            # Just log EXISTS / NOT EXISTS if you want
            if re.search(r'\bEXISTS\s*\(\s*SELECT', text, re.IGNORECASE):
                self.optimizations_applied.append(
                    "Extra Credit: (detected) EXISTS subquery (no structural transform)"
                )
            if re.search(r'\bNOT\s+EXISTS\s*\(\s*SELECT', text, re.IGNORECASE):
                self.optimizations_applied.append(
                    "Extra Credit: (detected) NOT EXISTS subquery (no structural transform)"
                )

        node.left = self._unnest_subqueries(node.left)
        node.right = self._unnest_subqueries(node.right)
        return node
    
    # ---------- Common helper methods ----------

    def _estimate_selectivity(self, condition):
        """Estimate selectivity"""
        if '=' in condition:
            if any(k in condition.upper() for k in ['SSN', 'NUMBER', 'PNO', 'ESSN', 'DNUM']):
                return 0.05
            return 0.2
        if any(op in condition for op in ['>', '<', '>=', '<=', '!=']): 
            return 0.33
        return 0.5

    def _get_referenced_tables(self, condition):
        """Get aliases referenced in a condition"""
        matches = re.findall(r'([A-Za-z_]\w*)\.\w+', condition)
        return set(matches)
    
    def _get_node_tables(self, node):
        """Get all table names in a subtree (resolved names)"""
        if node is None:
            return set()
        tables = set()
        if node.node_type == RELATION:
            tables.add(node.data)
        tables.update(self._get_node_tables(node.left))
        tables.update(self._get_node_tables(node.right))
        return tables
    
    def _is_join_condition(self, condition):
        """Check if condition is a join condition"""
        if '=' not in condition:
            return False
        refs = self._get_referenced_tables(condition)
        return len(refs) >= 2

# --- SQL reconstruction helpers ---

def collect_where_conditions(node, conditions):
    """Traverse tree and collect all WHERE-selection conditions (σ nodes)."""
    if node is None:
        return
    if node.node_type == SELECT:
        conditions.append(node.data)
        collect_where_conditions(node.left, conditions)
    else:
        collect_where_conditions(node.left, conditions)
        collect_where_conditions(node.right, conditions)

def find_top_project(node):
    """Find the topmost PROJECT node, if any."""
    if node is None:
        return None
    if node.node_type == PROJECT:
        return node
    left = find_top_project(node.left)
    if left:
        return left
    return find_top_project(node.right)

def build_sql_from_tree(root, parsed):
    """
    Convert the optimized query tree back into a runnable SQL query.

    NOTE: Semi/anti-join nodes (⋉/▷) are represented only in the tree; this
    function currently only regenerates WHERE from remaining σ nodes.
    """
    # SELECT clause
    project_node = find_top_project(root)
    if project_node is not None and project_node.data:
        select_clause = project_node.data
    else:
        select_clause = parsed['select'] if parsed['select'] else '*'
    
    from_clause = parsed['from']
    group_by_clause = parsed['group_by']
    having_clause = parsed['having']
    order_by_clause = parsed['order_by']
    
    where_conditions = []
    collect_where_conditions(root, where_conditions)
    
    sql_lines = []
    sql_lines.append("SELECT " + select_clause)
    sql_lines.append("FROM " + from_clause)
    
    if where_conditions:
        sql_lines.append("WHERE " + " AND ".join(where_conditions))
    
    if group_by_clause:
        sql_lines.append("GROUP BY " + group_by_clause)
    
    if having_clause:
        sql_lines.append("HAVING " + having_clause)
    
    if order_by_clause:
        sql_lines.append("ORDER BY " + order_by_clause)
    
    return "\n".join(sql_lines) + ";"

# --- Schema loading and main driver ---

def load_schema_from_file(content):
    schema = {}
    table_pattern = r'(\w+)\s*\((.*?)\);'
    matches = re.findall(table_pattern, content, re.DOTALL | re.IGNORECASE)
    for table_name, definition in matches:
        schema[table_name] = {'attributes': [], 'primary_key': [], 'unique': []}
        lines = [line.strip() for line in definition.split(',')]
        for line in lines:
            if 'PRIMARY KEY' in line.upper():
                m = re.search(r'PRIMARY KEY\s*\(\s*(\w+)', line, re.IGNORECASE)
                if m:
                    schema[table_name]['primary_key'].append(m.group(1))
            elif 'UNIQUE' in line.upper():
                m = re.search(r'UNIQUE\s*\(\s*(\w+)', line, re.IGNORECASE)
                if m:
                    schema[table_name]['unique'].append(m.group(1))
            else:
                m = re.match(r'(\w+)', line)
                if m:
                    schema[table_name]['attributes'].append(m.group(1))
    return schema

def process_query_file(filename):
    # open file and read contents
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        
    schema = load_schema_from_file(content)
    query_match = re.search(r'-- SQL Query --(.*)', content, re.DOTALL | re.IGNORECASE)
        
            
    query = query_match.group(1).strip()
    parser = SQLParser(query, schema)
    parsed = parser.parse()

    # printing final results ! 
    print(f"\n{'*'*80}")
    print(f"Query Optimization Results for: {filename}")
    print(f"{'*'*80}\n")
        
    print("SQL query:")
    print(query)
    print()
        
    builder = QueryTreeBuilder(parsed, schema)
    canonical_tree = builder.build_canonical_tree()
    print("\ncanonical query tree:")
    print(canonical_tree)
        
    optimizer = QueryOptimizer(schema, parsed['aliases'])
    optimized_tree = optimizer.optimize(canonical_tree)
        
    print("\noptimized query tree:")
    print(optimized_tree)
        
    optimized_sql = build_sql_from_tree(optimized_tree, parsed)
    print("\nsql query with optimizations:")
    print(optimized_sql)
        
    print("\nrules applied:")
    seen_rules = set()
    for x in optimizer.optimizations_applied:
        if x not in seen_rules:
            print(f"✓ {x}")
            seen_rules.add(x)
        
    print("\n" + "*"*80 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            process_query_file(filename)
    else:
        print("Please run with command: python3 Project1/optimizer.py input.txt")
