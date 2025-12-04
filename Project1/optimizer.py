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
    Purpose: Parse SQL Queries that are inputted into each part of the syntax using regular expressions and checking matches of an input.

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
        Purpose: Using the regular expressions libarary, we extract each part of the SQL query into its individual parts
        by searching for matches of keywords
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

        Purpose: To build the canonical tree from the inital SQL query with no optimizations by using nodes with children for each clause

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
        - using regular expressions to identify join components

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

        call each function to check/apply each rule and then print the tree after each rule for tracking.
      
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

        checks for non-nested ORs by tracking the parenthesis depth and validating surrounding characters
        - like the AND function ...

        '''
        nested_parenthesis = 0 
        i = 0
        n = len(expr)

        while i < n:
            ch = expr[i]
            if ch == '(': # we are within another layer of nested parenthesis
                nested_parenthesis += 1
            elif ch == ')': # end of parenthesis
                nested_parenthesis -= 1

            if nested_parenthesis == 0 and i + 2 <= n: # we only check for OR if we are outside of parenthesis completely
                characters = expr[i:i+2].upper() # extract two characters 
                if characters == 'OR': # check if they're or
                    before_OR = (i == 0) or expr[i-1].isspace() or expr[i-1] in ')'
                    after_OR = (i + 2 == n) or expr[i+2].isspace() or expr[i+2] in '('
                    if before_OR and after_OR:
                        return True
            i += 1
        return False

    def _selectivity_key(self, node):
        '''

        JUST RETURNS THE SELECIVITY OF THE NODE 

        '''
        return node.selectivity
    
    def _order_by_selectivity(self, node):
        '''

        Rule 3: Order selections by selectivity
        - by identifiying selection chains
        - sort by selectivity value
        - rebuild selection chain in order of selectivity
        - attach subtree back to last selection

        '''

        if node is None: # basic if no node, do nothing
            return None
        
        if node.node_type == SELECT: # if node is select, we collect all the selects in a list
            selections = []
            current = node
            while current and current.node_type == SELECT:
                selections.append(current)
                current = current.left # go down the selects
                
            if len(selections) > 1: # only need to reorder if more than one select
                if any(self._has_top_level_or(sel.data) for sel in selections): # if any selection has a top level OR, we skip reordering
                    selections[-1].left = self._order_by_selectivity(current) # put the tree back
                    return node

                selections.sort(key=self._selectivity_key) # sort selections by selectivity value
                self.optimizations_applied.append("Rule #3: Apply Selections with Smallest Selectivity First") # mark rule as applied
                
                root = selections[0] # new root is smallest selectivity aka most selective
                for i in range(len(selections) - 1): # chain the selections together
                    selections[i].left = selections[i+1]

                selections[-1].left = current # put subtree back
                
                selections[-1].left = self._order_by_selectivity(current) # further apply rule 3

                return root
            

        # if node isn't select, we can apply to children

        node.left = self._order_by_selectivity(node.left) 
        node.right = self._order_by_selectivity(node.right)
        return node
    
    def _cartesian_to_join(self, node):
        '''

        Rule 4: Convert Cartesian product + selection to join
        - look for SELECT nodes with cartisan products
        - when matching cartesian product, we create a JOIN node with the select as condition
        - remove previous select

        '''

        if node is None: # base case again
            return None
        
        if node.node_type == SELECT and self._is_join_condition(node.data): # Check if this is a SELECT with a join condition
            cartesian_node, parent = self._find_applicable_cartesian(node.left, node.data) # look for applicable cartesian product
            
            if cartesian_node is not None: # if we find cartisan product
                join_node = QueryNode(JOIN, "INNER JOIN", join_condition=node.data) # create a JOIN node
                join_node.left = cartesian_node.left
                join_node.right = cartesian_node.right
                
                # Replace the cartesian in the tree

                if parent is None:
                    # The cartesian was directly under this select

                    result = join_node # select is removed, JOIN becomes new subtree
                else:
                    # cartesian has a parent node, so we replace it there
                    if parent.left == cartesian_node: 
                        parent.left = join_node
                    else:
                        parent.right = join_node

                    result = node.left # result is now the subtree under the select
                
                self.optimizations_applied.append(
                    "Rule #4: Replace Cartesian Product + Selection → Join"
                )
                
                # Continue optimizing the result
                return self._cartesian_to_join(result)
            
        # process children nodes
        node.left = self._cartesian_to_join(node.left)
        node.right = self._cartesian_to_join(node.right)
        
        return node
    
    def _find_applicable_cartesian(self, node, condition, parent=None):
        '''
        
        Find the cartesian product node where a given condition can become a join condition

        '''
        if node is None:
            return None, None
        
        if node.node_type == CARTESIAN: # Check if this join condition applies to this cartesian
            refs = self._get_referenced_tables(condition) # obtain alias
            resolved_refs = self._alias_to_table_names(refs) # obtain table names
            left_tables = self._get_node_tables(node.left) # tables in left subtree
            right_tables = self._get_node_tables(node.right) # tables in right subtree
            
            # Join condition should reference both sides check
            if (not resolved_refs.issubset(left_tables) and 
                not resolved_refs.issubset(right_tables) and
                resolved_refs.issubset(left_tables.union(right_tables))):
                return node, parent
            
        
        # check if join refs both sides ........
        
        # Search left subtree
        result, p = self._find_applicable_cartesian(node.left, condition, node)
        if result:
            return result, p
        
        # Search right subtree
        return self._find_applicable_cartesian(node.right, condition, node)
    
    def _push_projections(self, node):
        '''
        Rule 5: Push Projections Down
        '''
        if node is None:
            return None
        
        # First recursively process children
        node.left = self._push_projections(node.left)
        node.right = self._push_projections(node.right)
        
        
        if node.node_type != PROJECT:
            return node # return if not project
        
        # Mark that we're applying Rule 5
        if "Rule #5: Push Projections Down" not in self.optimizations_applied:
            self.optimizations_applied.append("Rule #5: Push Projections Down")
        
        projected_attrs = self._parse_projection_attributes(node.data) # Parse the attributes being projected
        
        # Collect additional attributes needed for operations above this point
        needed_attrs = self._collect_needed_attributes(node.left, projected_attrs)
        
       
        node.left = self._insert_projections(node.left, needed_attrs)  # Push projections down to each relation
        
        return node
    
    def _parse_projection_attributes(self, proj_clause):
        '''

        set of attributes being projected
        - for projection *, we return empty set to indicate all attributes are kept
        - otherwise split on commas
        - check aggregation functions and extract inner attributes

        '''
        if proj_clause == '*':
            return set()  # Keep all attributes
        
        attrs = set()
        
        parts = [p.strip() for p in proj_clause.split(',')] # Split by comma, but be careful of function calls like COUNT(*)
        
        for part in parts:
            
            func_match = re.match(r'(COUNT|SUM|AVG|MIN|MAX)\s*\((.*?)\)', part, re.IGNORECASE) # Handle aggregation functions: COUNT(E.Salary), SUM(...)
            if func_match:
                inner = func_match.group(2).strip()
                if inner != '*':
                    attr_match = re.match(r'([A-Za-z_]\w*)\.([A-Za-z_]\w*)', inner) # Extract table.attr from inside function
                    if attr_match:
                        attrs.add((attr_match.group(1), attr_match.group(2)))
            else:
                attr_match = re.match(r'([A-Za-z_]\w*)\.([A-Za-z_]\w*)', part) # Regular attributes are here
                if attr_match:
                    attrs.add((attr_match.group(1), attr_match.group(2)))
        
        return attrs
    
    def _collect_needed_attributes(self, node, base_attrs):
        '''

        move up the tree to collect all attributes needed for operations above

        '''
        necessary = set(base_attrs)
        
        def traverse(n):
            if n is None:
                return
            
            # selections
            if n.node_type == SELECT or n.node_type == HAVING:
                refs = self._get_referenced_attributes(n.data)
                necessary.update(refs)
            
            # joins
            elif n.node_type in [JOIN, SEMI_JOIN, ANTI_JOIN, OUTER_JOIN]:
                if n.join_condition:
                    refs = self._get_referenced_attributes(n.join_condition)
                    necessary.update(refs)
            
            # GROUP BY 
            elif n.node_type == GROUP:
                refs = self._get_referenced_attributes(n.data)
                necessary.update(refs)
            
            # ORDER BY
            elif n.node_type == SORT:
                refs = self._get_referenced_attributes(n.data)
                necessary.update(refs)
            
            traverse(n.left)
            traverse(n.right)
        
        traverse(node)
        return necessary
    
    def _get_referenced_attributes(self, expression):
        '''

        get all referenced attributes from an expression

        '''

        attrs = set()
        matches = re.findall(r'([A-Za-z_]\w*)\.([A-Za-z_]\w*)', expression) # match patterns regular expressions
        for alias, attr in matches:
            attrs.add((alias, attr))
        return attrs
    
    def _insert_projections(self, node, needed_attrs):
        '''
        Insert projection nodes above relations based on needed attributes
        '''
        if node is None:
            return None
        
        if node.node_type == RELATION: # for relation nodes, insert projection if needed
            relation_attrs = []
            for alias, attr in needed_attrs:
                resolved_table = self.aliases.get(alias, alias) # does alias refer to a table
                if resolved_table == node.data:
                    relation_attrs.append(f"{alias}.{attr}")
            
            # projections only if filters]
            all_attrs = self._get_all_relation_attributes(node.data)
            if relation_attrs and all_attrs and len(relation_attrs) < len(all_attrs):
                proj_node = QueryNode(PROJECT, ", ".join(relation_attrs))
                proj_node.left = node
                return proj_node
            
            return node
        
        # do this to the children nodes
        node.left = self._insert_projections(node.left, needed_attrs)
        node.right = self._insert_projections(node.right, needed_attrs)
        
        return node
    
    def _get_all_relation_attributes(self, table_name):
        """Get all attributes of a relation from schema"""
        if table_name in self.schema:
            return self.schema[table_name]['attributes']
        return []

    def _unnest_in_subquery(self, node, anti=False):
        '''

        basically convert IN/NOT IN subquery to semi/anti-join
        - use regular expressions to identify the pattern
        - extract outer column, inner column, table name, and inner where predicate
        - build semi/anti-join node with appropriate subtrees

        '''
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
        """ # regex pattern 
        m = re.match(pattern, node.data, re.IGNORECASE | re.VERBOSE) # match aforementioned pattern
        if not m:
            return None  # pattern not supported
        
        # components
        outer_col = m.group(1)
        inner_col = m.group(2)
        from_part = m.group(3)
        inner_where = m.group(4)  

        # obtain table name from from_part
        parts = from_part.split()
        table_name = parts[0]

        right_relation = QueryNode(RELATION, table_name) # we create right relation node
        if inner_where and inner_where.strip():
            right_subtree = QueryNode(SELECT, inner_where.strip(), left=right_relation)
        else:
            right_subtree = right_relation

        # Left subtree is whatever was under the og node
        left_subtree = node.left

       # -- build the semi/anti-join nodes here -- 
        join_type = ANTI_JOIN if anti else SEMI_JOIN
        join_cond = outer_col + " = " + inner_col
        join_node = QueryNode(join_type, "", left=left_subtree, right=right_subtree,
                              join_condition=join_cond)

        return join_node

# parts for extra credit
    def _unnest_subqueries(self, node):
        '''
        function that unnests in/not in subqueries into semi/anti-joins
        - if node is select, we check for IN/NOT IN patterns 
        - we use regular expressions to identify these patterns
        - call function with true/false parameter
        '''
        if node is None:
            return None

        if node.node_type == SELECT:
            text = node.data

            # NOT IN -> anti-join
            if re.search(r'\bNOT\s+IN\s*\(\s*SELECT', text, re.IGNORECASE): # look for NOT IN pattern
                new_node = self._unnest_in_subquery(node, anti=True) # call unnest function with anti=True
                if new_node is not None: # if` we succesfully created anti-join
                    self.optimizations_applied.append( # mark apply
                        "not in --> anti-join"
                    )
                    new_node.left = self._unnest_subqueries(new_node.left)
                    new_node.right = self._unnest_subqueries(new_node.right)
                    return new_node

            # IN -> semi-join
            if re.search(r'\bIN\s*\(\s*SELECT', text, re.IGNORECASE): 
                new_node = self._unnest_in_subquery(node, anti=False) # call unnest function with anti=False
                if new_node is not None: # if we successfully created a semi-join
                    self.optimizations_applied.append(
                        "in --> semi-join ⋉" # mark applied
                    )
                    new_node.left = self._unnest_subqueries(new_node.left)
                    new_node.right = self._unnest_subqueries(new_node.right)
                    return new_node


        # we appply to children nodes too
        node.left = self._unnest_subqueries(node.left)
        node.right = self._unnest_subqueries(node.right)
        return node

    def _estimate_selectivity(self, condition):
        '''
        estimate selecitivity function 
        '''
        if '=' in condition:
            if any(k in condition.upper() for k in ['SSN', 'NUMBER', 'PNO', 'ESSN', 'DNUM']): # primary keys that were in the samples
                return 0.05
            return 0.2
        if any(op in condition for op in ['>', '<', '>=', '<=', '!=']): # ranges
            return 0.33
        return 0.5

    def _get_referenced_tables(self, condition):
        '''
        aliases of tables referenced in a condition
        '''
        matches = re.findall(r'([A-Za-z_]\w*)\.\w+', condition) # match patterns regular expressions 
        return set(matches)
    
    def _get_node_tables(self, node):
        '''
        get all tables in subtree rooted at node
        '''
        if node is None:
            return set()
        tables = set()
        if node.node_type == RELATION:
            tables.add(node.data)
        tables.update(self._get_node_tables(node.left))
        tables.update(self._get_node_tables(node.right))
        return tables
    
    def _is_join_condition(self, condition):
        '''

        just check if condition references at least two different tables

        '''
        if '=' not in condition:
            return False
        refs = self._get_referenced_tables(condition)
        return len(refs) >= 2

# stuff to convert to SQL

def collect_where_conditions(node, conditions):
    '''

    obtain all WHERE conditions from SELECT nodes in the tree via 
    - recursive traversal
    - if it sees a select, will append condition to conditions 
    - traverse on left

    '''
    if node is None:
        return
    if node.node_type == SELECT:
        conditions.append(node.data)
        collect_where_conditions(node.left, conditions)
    else:
        collect_where_conditions(node.left, conditions)
        collect_where_conditions(node.right, conditions)

def find_top_project(node):
    ''' 

    just obtain the top project
    - search tree, top-down
    - or keeps searching recursively 

    '''
    if node is None:
        return None
    if node.node_type == PROJECT: # if current node is project, just return it
        return node
    left = find_top_project(node.left) # or keep searching left
    if left: 
        return left
    return find_top_project(node.right)

def build_sql_from_tree(root, parsed):
    '''
    develop sql query from the optimized treee
    - take select from highest project or from inital select
    - where is obtained from various selects + join with AND

    '''
    
    project_node = find_top_project(root) # find top project node
    if project_node is not None and project_node.data: # if project node exists and has data
        select_clause = project_node.data # that's our select clause
    else:
        select_clause = parsed['select'] if parsed['select'] else '*' # or just use the original seelect
    
    from_clause = parsed['from'] # these stay the same
    group_by_clause = parsed['group_by']
    having_clause = parsed['having']
    order_by_clause = parsed['order_by']
    
    where_conditions = [] # initalize where conditions list
    collect_where_conditions(root, where_conditions) # collect all where conditions from tree
    
    sql_lines = [] # initalize sql list

    # append everything in 
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

def load_schema_from_file(content):
    '''

    parse schema from file content
    - use regular expressions to find table definitions
    - for each table, extract attributes, primary keys, unique constraints
    - return schema dictionary

    '''
    schema = {}
    table_pattern = r'(\w+)\s*\((.*?)\);' # regex pattern to match table definitions
    matches = re.findall(table_pattern, content, re.DOTALL | re.IGNORECASE) # find all matches in content
    for table_name, definition in matches:
        schema[table_name] = {'attributes': [], 'primary_key': [], 'unique': []} # initialize schema entry
        lines = [line.strip() for line in definition.split(',')] # split definition into lines
        for line in lines:
            if 'PRIMARY KEY' in line.upper():
                m = re.search(r'PRIMARY KEY\s*\(\s*(\w+)', line, re.IGNORECASE) # extract PK
                if m:
                    schema[table_name]['primary_key'].append(m.group(1)) # add to primary key list
            elif 'UNIQUE' in line.upper():
                m = re.search(r'UNIQUE\s*\(\s*(\w+)', line, re.IGNORECASE) # extract unique constraints
                if m:
                    schema[table_name]['unique'].append(m.group(1)) # add to unique list
            else:
                m = re.match(r'(\w+)', line)
                if m:
                    schema[table_name]['attributes'].append(m.group(1)) 
    return schema

def process_query_file(filename):
    '''

    function that will:
    1. open the file and read contents 
    2. extract schema
    3. build schema dictionary
    4. parse SQL
    5. build canonical query tree
    6. optimize query tree
    7. convert optimized tree back to SQL.

    '''
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
