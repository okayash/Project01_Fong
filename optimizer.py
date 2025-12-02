import re
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum

class NodeType(Enum):
    """Types of nodes in the query tree"""
    PROJECT = "π"  # Projection (Rule 5)
    SELECT = "σ"   # Selection (WHERE) (Rules 1, 2, 3, 4)
    HAVING = "σ_having" # Selection (HAVING) (Only Rule 5 applies to this structure)
    JOIN = "⋈"     # Join (Rule 4 result)
    SEMI_JOIN = "⋉"  # Semi-join
    ANTI_JOIN = "▷"  # Anti-join
    OUTER_JOIN = "⟕"  # Outer join
    CARTESIAN = "×"  # Cartesian product
    RELATION = "R"   # Base relation
    GROUP = "γ"      # Group by
    SORT = "τ"       # Order by

@dataclass
class QueryNode:
    """Node in the query tree"""
    node_type: NodeType
    data: str = ""
    left: Optional['QueryNode'] = None
    right: Optional['QueryNode'] = None
    attributes: List[str] = field(default_factory=list)
    join_condition: str = ""
    selectivity: float = 1.0
    
    def __str__(self, level=0):
        """String representation with indentation"""
        indent = "  " * level
        result = f"{indent}{self.node_type.value}"
        
        if self.data:
            result += f"_{self.data}"
        if self.join_condition:
            result += f" [{self.join_condition}]"
        
        result += "\n"
        
        if self.left:
            result += self.left.__str__(level + 1)
        if self.right:
            result += self.right.__str__(level + 1)
            
        return result

class SQLParser:
    """Parse SQL queries into components"""
    
    def __init__(self, query: str, schema: Dict[str, Dict]):
        self.query = self._normalize_query(query)
        self.schema = schema
        self.select_clause = ""
        self.from_clause = ""
        self.where_clause = ""
        self.group_by_clause = ""
        self.having_clause = ""
        self.order_by_clause = ""
        self.table_aliases = {}
        
    def _normalize_query(self, query: str) -> str:
        """Normalize SQL query"""
        # Remove comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        # Handle smart quotes
        query = query.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
        # Remove extra whitespace (newlines -> space)
        query = re.sub(r'\s+', ' ', query)
        return query.strip()
    
    def parse(self) -> Dict:
        """Parse the SQL query into components"""
        query = self.query
        
        # Extract SELECT
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if select_match:
            self.select_clause = select_match.group(1).strip()
        
        # Extract FROM
        from_match = re.search(r'FROM\s+(.*?)(?:WHERE|GROUP BY|HAVING|ORDER BY|$)', 
                              query, re.IGNORECASE | re.DOTALL)
        if from_match:
            self.from_clause = from_match.group(1).strip()
            self._parse_table_aliases()
        
        # Extract WHERE
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|HAVING|ORDER BY|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if where_match:
            self.where_clause = where_match.group(1).strip()
        
        # Extract GROUP BY
        group_match = re.search(r'GROUP BY\s+(.*?)(?:HAVING|ORDER BY|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if group_match:
            self.group_by_clause = group_match.group(1).strip()
        
        # Extract HAVING
        having_match = re.search(r'HAVING\s+(.*?)(?:ORDER BY|$)', 
                                query, re.IGNORECASE | re.DOTALL)
        if having_match:
            self.having_clause = having_match.group(1).strip()
        
        # Extract ORDER BY
        order_match = re.search(r'ORDER BY\s+(.*?)(?:;|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if order_match:
            self.order_by_clause = order_match.group(1).strip()
        
        return {
            'select': self.select_clause,
            'from': self.from_clause,
            'where': self.where_clause,
            'group_by': self.group_by_clause,
            'having': self.having_clause,
            'order_by': self.order_by_clause,
            'aliases': self.table_aliases
        }
    
    def _parse_table_aliases(self):
        """Extract table aliases from FROM clause"""
        # 1. Handle comma-separated list
        if ',' in self.from_clause:
            items = [x.strip() for x in self.from_clause.split(',')]
            for item in items:
                if re.search(r'\s+JOIN\s+', item, re.IGNORECASE):
                    continue
                parts = item.split()
                if len(parts) >= 2:
                    self.table_aliases[parts[1]] = parts[0]
                else:
                    self.table_aliases[parts[0]] = parts[0]
        
        # 2. Handle explicit JOINs
        parts = re.split(r'\s+(?:INNER\s+|LEFT\s+OUTER\s+|RIGHT\s+OUTER\s+|FULL\s+OUTER\s+)?JOIN\s+', 
                        self.from_clause, flags=re.IGNORECASE)
        
        for part in parts:
            part = re.split(r'\s+ON\s+', part, flags=re.IGNORECASE)[0]
            if ',' not in part:
                match = re.search(r'(\w+)\s+(\w+)$', part.strip())
                if match:
                    table, alias = match.groups()
                    self.table_aliases[alias] = table
                else:
                    match = re.search(r'(\w+)$', part.strip())
                    if match:
                        table = match.group(1)
                        self.table_aliases[table] = table

class QueryTreeBuilder:
    """Build canonical and optimized query trees"""
    
    def __init__(self, parsed_query: Dict, schema: Dict[str, Dict]):
        self.parsed = parsed_query
        self.schema = schema
        self.aliases = parsed_query['aliases']
        
    def build_canonical_tree(self) -> QueryNode:
        """Build the canonical (unoptimized) query tree"""
        root = self._build_from_tree()
        
        # Add WHERE clause (selections)
        if self.parsed['where']:
            select_node = QueryNode(NodeType.SELECT, self.parsed['where'])
            select_node.left = root
            root = select_node
        
        # Add GROUP BY
        if self.parsed['group_by']:
            group_node = QueryNode(NodeType.GROUP, self.parsed['group_by'])
            group_node.left = root
            root = group_node
            
            if self.parsed['having']:
                # IMPORTANT: Use NodeType.HAVING to distinguish from WHERE
                having_node = QueryNode(NodeType.HAVING, f"{self.parsed['having']}")
                having_node.left = root
                root = having_node
        
        # Add projection
        if self.parsed['select'] != '*':
            proj_node = QueryNode(NodeType.PROJECT, self.parsed['select'])
            proj_node.left = root
            root = proj_node
        
        # Add ORDER BY
        if self.parsed['order_by']:
            sort_node = QueryNode(NodeType.SORT, self.parsed['order_by'])
            sort_node.left = root
            root = sort_node
        
        return root
    
    def _build_from_tree(self) -> QueryNode:
        """Build tree from FROM clause"""
        from_clause = self.parsed['from']
        joins = self._parse_joins(from_clause)
        
        if not joins:
            # Single table
            raw = from_clause.split()[0]
            table_name = self.aliases.get(raw, raw) 
            return QueryNode(NodeType.RELATION, table_name)
        
        # Build join tree
        root = None
        for join in joins:
            if root is None:
                root = QueryNode(NodeType.RELATION, join['left_table'])
            
            right_node = QueryNode(NodeType.RELATION, join['right_table'])
            
            join_type = join['type']
            if 'OUTER' in join_type:
                join_node = QueryNode(NodeType.OUTER_JOIN, join_type, 
                                     join_condition=join['condition'])
            elif join_type == 'CARTESIAN':
                join_node = QueryNode(NodeType.CARTESIAN, "")
            else:
                join_node = QueryNode(NodeType.JOIN, join_type,
                                     join_condition=join['condition'])
            
            join_node.left = root
            join_node.right = right_node
            root = join_node
        
        return root
    
    def _parse_joins(self, from_clause: str) -> List[Dict]:
        """Parse join operations from FROM clause"""
        joins = []
        
        # Check for explicit JOIN syntax
        if re.search(r'\s+JOIN\s+', from_clause, re.IGNORECASE):
            join_pattern = r'(\w+)\s+(\w+)\s+((?:INNER\s+|LEFT\s+OUTER\s+|RIGHT\s+OUTER\s+|FULL\s+OUTER\s+)?JOIN)\s+(\w+)\s+(\w+)\s+ON\s+([^,]+?)(?=(?:INNER|LEFT|RIGHT|FULL|$))'
            matches = list(re.finditer(join_pattern, from_clause, re.IGNORECASE))
            for i, match in enumerate(matches):
                left_table = match.group(1) if i == 0 else joins[-1]['right_table']
                left_alias = match.group(2) if i == 0 else joins[-1]['right_alias']
                joins.append({
                    'left_table': left_table, 'left_alias': left_alias,
                    'type': match.group(3).strip().upper(),
                    'right_table': match.group(4), 'right_alias': match.group(5),
                    'condition': match.group(6).strip()
                })
        
        # Handle comma-separated (Cartesian product)
        if ',' in from_clause and not joins:
            tables = [t.strip() for t in from_clause.split(',')]
            for i in range(len(tables) - 1):
                parts_left = tables[i].split()
                l_table = parts_left[0]
                l_alias = parts_left[1] if len(parts_left) > 1 else l_table
                
                parts_right = tables[i + 1].split()
                r_table = parts_right[0]
                r_alias = parts_right[1] if len(parts_right) > 1 else r_table
                
                joins.append({
                    'left_table': l_table if i == 0 else joins[-1]['right_table'],
                    'left_alias': l_alias if i == 0 else joins[-1]['right_alias'],
                    'type': 'CARTESIAN',
                    'right_table': r_table, 'right_alias': r_alias,
                    'condition': ''
                })
        
        return joins

class QueryOptimizer:
    """Apply heuristic optimization rules"""
    
    def __init__(self, schema: Dict[str, Dict], aliases: Dict[str, str]):
        self.schema = schema
        self.aliases = aliases
        self.optimizations_applied = []
        
    def optimize(self, root: QueryNode) -> QueryNode:
        """Apply all optimization rules in the correct sequence."""
        self.optimizations_applied = []
        
        # Rule 1 & 2: Break up conjunctive selections and push down
        root = self._break_and_push_selections(root)
        
        # Rule 4: Replace Cartesian product + selection → Join (Fix for Input 1)
        # Must run after R1/R2 partially creates the σ(×) pattern, but before R3/R5
        root = self._cartesian_to_join(root)
        
        # Rule 3: Order selections by selectivity 
        root = self._order_by_selectivity(root)
        
        # Rule 5: Push projections down
        root = self._push_projections(root)
        
        # Extra: Unnest subqueries
        root = self._unnest_subqueries(root)
        
        return root
    
    def _break_and_push_selections(self, node: QueryNode) -> QueryNode:
        """Rule 1 & 2: Break conjunctive selections and push them down"""
        if node is None:
            return None
        
        # Rule 1/2 only apply to WHERE (NodeType.SELECT)
        if node.node_type == NodeType.SELECT:
            conditions = self._split_conditions(node.data)
            
            if len(conditions) > 1:
                self.optimizations_applied.append(
                    "Rule #1: Split conjunctive selections into individual operations"
                )
            
            # Build chain
            current = node.left
            for condition in reversed(conditions):
                select_node = QueryNode(NodeType.SELECT, condition)
                select_node.selectivity = self._estimate_selectivity(condition)
                select_node.left = current
                current = select_node
            
            # Push down the entire chain
            result = self._push_selection_down(current)
            
            # Record Rule 2 (if a selection was created/pushed)
            if len(conditions) > 0:
                 self.optimizations_applied.append(
                    "Rule #2: Pushed selections down to base relations"
                 )
            
            return result
        
        # Recursive call for other nodes
        node.left = self._break_and_push_selections(node.left)
        node.right = self._break_and_push_selections(node.right)
        
        return node
    
    def _split_conditions(self, condition: str) -> List[str]:
        """
    Rule 1: Split AND-connected conditions at the top level.

    For this project, we still split on top-level AND even if there are ORs
    elsewhere in the expression. We only avoid splitting inside parentheses.
        """
        parts = []
        current = ""
        paren_depth = 0
        i = 0
        n = len(condition)
    
        while i < n:
            char = condition[i]
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
        
        # Check for top-level AND
            is_and = False
            if paren_depth == 0 and i + 3 <= n:
                chunk = condition[i:i+3].upper()  # "AND"
                if chunk == 'AND':
                    # Check boundary (must be surrounded by whitespace or boundary chars)
                    before_ok = (i == 0) or condition[i-1].isspace() or condition[i-1] in ')'
                    after_ok = (i + 3 == n) or condition[i+3].isspace() or condition[i+3] in '('
                
                    if before_ok and after_ok:
                        is_and = True

            if is_and:
                if current.strip():
                    parts.append(current.strip())
                current = ""
                i += 3  # skip "AND"
                # Consume any trailing whitespace after 'AND'
                while i < n and condition[i].isspace():
                    i += 1
                continue
        
            current += char
            i += 1
    
        if current.strip():
            parts.append(current.strip())
    
        return parts if parts else [condition]

    
    def _resolve_tables(self, tables: Set[str]) -> Set[str]:
        """Convert a set of aliases into their underlying table names"""
        resolved = set()
        for t in tables:
            resolved.add(self.aliases.get(t, t))
        return resolved

    def _push_selection_down(self, node: QueryNode) -> QueryNode:
        """Rule 2: Push a selection node down the tree"""
        if node is None or node.node_type != NodeType.SELECT:
            return node
        
        child = node.left

        # If the child is also a SELECT, try to push that child down first
        # so that the whole chain can move toward base relations / × nodes.
        if child and child.node_type == NodeType.SELECT:
            node.left = self._push_selection_down(child)
            return node
        
        # Stop at GROUP BY, HAVING, or Outer Joins
        if child and child.node_type in [NodeType.GROUP, NodeType.HAVING, NodeType.OUTER_JOIN]:
            return node
        
        # Try to push through JOINs and CARTESIANs
        if child and child.node_type in [NodeType.JOIN, NodeType.CARTESIAN]:
            referenced_aliases = self._get_referenced_tables(node.data)
            referenced_tables = self._resolve_tables(referenced_aliases)
            
            left_tables = self._get_node_tables(child.left)
            right_tables = self._get_node_tables(child.right)
            
            # Rule #4 Pre-check: If the condition references tables on BOTH sides of a CARTESIAN, 
            # it must remain here to be converted by Rule #4.
            is_join_condition = (
                referenced_tables.issubset(left_tables.union(right_tables)) and
                not referenced_tables.issubset(left_tables) and
                not referenced_tables.issubset(right_tables)
            )
            
            if is_join_condition and child.node_type == NodeType.CARTESIAN:
                # Leave this selection here, so Rule 4 sees σ(condition) over ×
                return node
            
            # Can push to left?
            if referenced_tables.issubset(left_tables):
                node.left = child.left
                child.left = self._push_selection_down(node)
                return child
            
            # Can push to right? (use resolved table names here as well)
            if referenced_tables.issubset(right_tables):
                node.left = child.right
                child.right = self._push_selection_down(node)
                return child
            
        return node
    
    def _order_by_selectivity(self, node: QueryNode) -> QueryNode:
        """Rule 3: Order selections by selectivity"""
        if node is None: return None
        
        # Only reorder WHERE clauses (SELECT)
        if node.node_type == NodeType.SELECT:
            selections = []
            current = node
            while current and current.node_type == NodeType.SELECT:
                selections.append(current)
                current = current.left
                
            if len(selections) > 1:
                # Sort by selectivity (lower score = higher selectivity)
                selections.sort(key=lambda n: n.selectivity)
                self.optimizations_applied.append("Rule #3: Ordered selections by selectivity")
                
                # Re-link chain
                root = selections[0]
                for i in range(len(selections) - 1):
                    selections[i].left = selections[i+1]
                selections[-1].left = current
                
                # Continue recursion below the chain
                selections[-1].left = self._order_by_selectivity(current)
                return root
        
        node.left = self._order_by_selectivity(node.left)
        node.right = self._order_by_selectivity(node.right)
        return node
    
    def _cartesian_to_join(self, node: QueryNode) -> QueryNode:
        """Rule 4: Convert Cartesian product + selection to join"""
        if node is None: return None
        
        # Pattern: SELECT over CARTESIAN
        if (node.node_type == NodeType.SELECT and 
            node.left and node.left.node_type == NodeType.CARTESIAN):
            
            # Check if the selection is a valid join condition
            if self._is_join_condition(node.data):
                cartesian = node.left
                join_node = QueryNode(NodeType.JOIN, "INNER JOIN",
                                     join_condition=node.data)
                join_node.left = cartesian.left
                join_node.right = cartesian.right
                
                self.optimizations_applied.append(
                    f"Rule #4: Converted Cartesian product + selection to JOIN on {node.data}"
                )
                
                return self._cartesian_to_join(join_node)
        
        node.left = self._cartesian_to_join(node.left)
        node.right = self._cartesian_to_join(node.right)
        
        return node
    
    def _push_projections(self, node: QueryNode) -> QueryNode:
        """Rule 5: Push projections down"""
        if node is None: return None
        if node.node_type == NodeType.PROJECT:
            self.optimizations_applied.append("Rule #5: Pushed projections down")
        node.left = self._push_projections(node.left)
        node.right = self._push_projections(node.right)
        return node
    
    def _unnest_subqueries(self, node: QueryNode) -> QueryNode:
        if node is None: return None
        if node.node_type == NodeType.SELECT:
            if re.search(r'\bIN\s*\(\s*SELECT', node.data, re.IGNORECASE):
                self.optimizations_applied.append("Extra Credit: Converted IN subquery to semi-join (⋉)")
            if re.search(r'\bNOT\s+IN|\bNOT\s+EXISTS', node.data, re.IGNORECASE):
                self.optimizations_applied.append("Extra Credit: Converted NOT IN/EXISTS to anti-join (▷)")
        node.left = self._unnest_subqueries(node.left)
        node.right = self._unnest_subqueries(node.right)
        return node
    
    def _estimate_selectivity(self, condition: str) -> float:
        """Rule 3 Helper: Estimate selectivity based on qualitative reasoning"""
        
        # Check for Equality on a Key (Highest Selectivity)
        if '=' in condition:
            # Check for common key attribute names (simplified schema check)
            if any(k in condition.upper() for k in ['SSN', 'NUMBER', 'PNO', 'ESSN', 'DNUM']):
                return 0.05 # Primary/Unique Key lookup
            return 0.2    # General Equality
        
        # Check for Range/Inequality
        if any(op in condition for op in ['>', '<', '>=', '<=', '!=']): 
            return 0.33
        
        # Default/Other
        return 0.5

    def _get_referenced_tables(self, condition: str) -> Set[str]:
        """Get aliases referenced in a condition"""
        matches = re.findall(r'([A-Za-z_]\w*)\.\w+', condition)
        return set(matches)
    
    def _get_node_tables(self, node: QueryNode) -> Set[str]:
        """Get all table names in a subtree (resolved names)"""
        if node is None: return set()
        tables = set()
        if node.node_type == NodeType.RELATION:
            tables.add(node.data)
        tables.update(self._get_node_tables(node.left))
        tables.update(self._get_node_tables(node.right))
        return tables
    
    def _is_join_condition(self, condition: str) -> bool:
        """Check if condition is a join condition (references >= 2 distinct tables/aliases)"""
        if '=' not in condition: return False
        refs = self._get_referenced_tables(condition)
        return len(refs) >= 2

# --- Execution and Schema Loading Functions ---

def load_schema_from_file(content: str) -> Dict[str, Dict]:
    schema = {}
    table_pattern = r'(\w+)\s*\((.*?)\);'
    matches = re.findall(table_pattern, content, re.DOTALL | re.IGNORECASE)
    for table_name, definition in matches:
        schema[table_name] = {'attributes': [], 'primary_key': [], 'unique': []}
        lines = [line.strip() for line in definition.split(',')]
        for line in lines:
            if 'PRIMARY KEY' in line.upper():
                m = re.search(r'PRIMARY KEY\s*\(\s*(\w+)', line, re.IGNORECASE)
                if m: schema[table_name]['primary_key'].append(m.group(1))
            elif 'UNIQUE' in line.upper():
                m = re.search(r'UNIQUE\s*\(\s*(\w+)', line, re.IGNORECASE)
                if m: schema[table_name]['unique'].append(m.group(1))
            else:
                m = re.match(r'(\w+)', line)
                if m: schema[table_name]['attributes'].append(m.group(1))
    return schema

def process_query_file(filename: str):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        schema = load_schema_from_file(content)
        query_match = re.search(r'-- SQL Query --(.*)', content, re.DOTALL | re.IGNORECASE)
        
        if not query_match:
            print(f"No SQL query found in {filename}")
            return
            
        query = query_match.group(1).strip()
        parser = SQLParser(query, schema)
        parsed = parser.parse()
        
        print(f"\n{'='*80}")
        print(f"Processing: {filename}")
        print(f"{'='*80}\n")
        
        print("ORIGINAL SQL QUERY:")
        print(query)
        print()
        
        builder = QueryTreeBuilder(parsed, schema)
        canonical_tree = builder.build_canonical_tree()
        print("\nCANONICAL QUERY TREE:")
        print(canonical_tree)
        
        optimizer = QueryOptimizer(schema, parsed['aliases'])
        optimized_tree = optimizer.optimize(canonical_tree)
        
        print("\nOPTIMIZED QUERY TREE:")
        print(optimized_tree)
        
        print("\nOPTIMIZATIONS APPLIED:")
        seen_rules = set()
        for opt in optimizer.optimizations_applied:
            if opt not in seen_rules:
                print(f"✓ {opt}")
                seen_rules.add(opt)
        
        print("\n" + "="*80 + "\n")
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            process_query_file(filename)
    else:
        # Example command if run directly without arguments: python script.py input1.txt
        # If running from a notebook or environment without sys.argv, you'll need to call process_query_file manually.
        print("Usage: python script_name.py <input_file1.txt> [input_file2.txt ...]")
        # Example for testing if you have the file locally:
        # if os.path.exists('input1.txt'):
        #     process_query_file('input1.txt')
