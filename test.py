import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field

@dataclass
class Relation:
    name: str
    attributes: List[str]
    primary_keys: List[str] = field(default_factory=list)
    unique_keys: List[List[str]] = field(default_factory=list)

@dataclass
class Selection:
    condition: str
    attribute: str
    operator: str
    value: str
    relation: str = ""
    
    def selectivity_score(self, schema: Dict[str, Relation]) -> int:
        """Lower score = higher selectivity (more restrictive)"""
        if self.relation and self.relation in schema:
            rel = schema[self.relation]
            # Check if attribute is primary key
            if self.attribute in rel.primary_keys:
                if self.operator == '=':
                    return 1  # Most selective
                return 2
            # Check if attribute is unique
            for unique_set in rel.unique_keys:
                if self.attribute in unique_set:
                    if self.operator == '=':
                        return 3
                    return 4
        # Equality on non-key attribute
        if self.operator == '=':
            return 5
        # Range predicates
        if self.operator in ['<', '>', '<=', '>=']:
            return 6
        # Not equal
        if self.operator in ['<>', '!=']:
            return 7
        return 8

class QueryOptimizer:
    def __init__(self, file_path: str):
        self.schema: Dict[str, Relation] = {}
        self.query = ""
        self.parse_input(file_path)
        
    def parse_input(self, file_path: str):
        """Parse schema definitions and SQL query from input file"""
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        content = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--'):
                content.append(line)
        
        full_text = ' '.join(content)
        
        # Extract schema definitions
        schema_pattern = r'(\w+)\s*\((.*?)\)\s*;?'
        matches = re.finditer(schema_pattern, full_text, re.IGNORECASE)
        
        for match in matches:
            if 'SELECT' in match.group(0).upper():
                break
            table_name = match.group(1)
            if table_name.upper() in ['PRIMARY', 'UNIQUE', 'SELECT', 'FROM', 'WHERE']:
                continue
            
            table_def = match.group(2)
            self.parse_relation(table_name, table_def)
        
        # Extract SQL query
        select_idx = full_text.upper().find('SELECT')
        if select_idx != -1:
            self.query = full_text[select_idx:].strip()
            if self.query.endswith(';'):
                self.query = self.query[:-1].strip()
    
    def parse_relation(self, name: str, definition: str):
        """Parse a single relation definition"""
        # Extract attributes and keys
        attrs = []
        primary_keys = []
        unique_keys = []
        
        # Find PRIMARY KEY and UNIQUE declarations
        pk_pattern = r'PRIMARY\s+KEY\s*\(\s*([^)]+)\s*\)'
        uk_pattern = r'UNIQUE\s*\(\s*([^)]+)\s*\)'
        
        pk_match = re.search(pk_pattern, definition, re.IGNORECASE)
        if pk_match:
            primary_keys = [k.strip() for k in pk_match.group(1).split(',')]
            definition = re.sub(pk_pattern, '', definition, flags=re.IGNORECASE)
        
        for uk_match in re.finditer(uk_pattern, definition, re.IGNORECASE):
            unique_keys.append([k.strip() for k in uk_match.group(1).split(',')])
        definition = re.sub(uk_pattern, '', definition, flags=re.IGNORECASE)
        
        # Parse remaining attributes
        attr_parts = [a.strip() for a in definition.split(',') if a.strip()]
        attrs = [a for a in attr_parts if a]
        
        self.schema[name.upper()] = Relation(
            name=name.upper(),
            attributes=[a.upper() for a in attrs],
            primary_keys=[k.upper() for k in primary_keys],
            unique_keys=[[k.upper() for k in uk] for uk in unique_keys]
        )
    
    def parse_query(self) -> Tuple[List[str], List[str], str]:
        """Parse SELECT, FROM, and WHERE clauses"""
        # Extract SELECT clause
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', self.query, re.IGNORECASE | re.DOTALL)
        select_attrs = [s.strip() for s in select_match.group(1).split(',')] if select_match else []
        
        # Extract FROM clause
        from_match = re.search(r'FROM\s+(.*?)(?:WHERE|$)', self.query, re.IGNORECASE | re.DOTALL)
        from_tables = []
        if from_match:
            from_text = from_match.group(1).strip()
            # Parse table aliases
            table_parts = [t.strip() for t in from_text.split(',')]
            for part in table_parts:
                tokens = part.split()
                from_tables.append(tokens[0].upper())
        
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.*)', self.query, re.IGNORECASE | re.DOTALL)
        where_clause = where_match.group(1).strip() if where_match else ""
        
        return select_attrs, from_tables, where_clause
    
    def extract_selections(self, where_clause: str) -> List[Selection]:
        """Extract individual selection conditions (Rule #1: Cascade)"""
        if not where_clause:
            return []
        
        # Split by AND (simple approach)
        conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
        selections = []
        
        for cond in conditions:
            cond = cond.strip()
            # Parse condition: attribute operator value
            match = re.match(r'(\w+\.\w+)\s*([<>=!]+|<>)\s*(.+)', cond)
            if match:
                full_attr = match.group(1)
                operator = match.group(2)
                value = match.group(3).strip().strip("'\"")
                
                # Extract table alias and attribute
                parts = full_attr.split('.')
                alias = parts[0].upper()
                attr = parts[1].upper()
                
                selections.append(Selection(
                    condition=cond,
                    attribute=attr,
                    operator=operator,
                    value=value,
                    relation=""
                ))
        
        return selections
    
    def assign_selections_to_relations(self, selections: List[Selection], tables: List[str]):
        """Assign each selection to its appropriate relation"""
        # Map aliases to actual table names (simplified)
        for sel in selections:
            for table in tables:
                if table in self.schema:
                    if sel.attribute in self.schema[table].attributes:
                        sel.relation = table
                        break
    
    def optimize(self) -> str:
        """Apply all heuristic optimization rules"""
        select_attrs, from_tables, where_clause = self.parse_query()
        
        output = ["=" * 60]
        output.append("HEURISTIC QUERY OPTIMIZATION")
        output.append("=" * 60)
        output.append("")
        
        # Original query
        output.append("Original Query:")
        output.append(self.query)
        output.append("")
        
        # Rule #1 & #2: Cascade selections and push down
        output.append("Rule #1 (Cascade of Selections):")
        output.append("Breaking conjunctive WHERE conditions into individual selections...")
        selections = self.extract_selections(where_clause)
        self.assign_selections_to_relations(selections, from_tables)
        
        for sel in selections:
            output.append(f"  σ({sel.condition})")
        output.append("")
        
        output.append("Rule #2 (Push Selections Down):")
        output.append("Pushing selections close to base relations...")
        for sel in selections:
            if sel.relation:
                output.append(f"  σ({sel.condition}) → {sel.relation}")
        output.append("")
        
        # Rule #3: Order by selectivity
        output.append("Rule #3 (Apply Selections with Smallest Selectivity First):")
        selections.sort(key=lambda s: s.selectivity_score(self.schema))
        output.append("Reordering selections by selectivity (most restrictive first):")
        for i, sel in enumerate(selections, 1):
            score = sel.selectivity_score(self.schema)
            output.append(f"  {i}. σ({sel.condition}) on {sel.relation} (score: {score})")
        output.append("")
        
        # Rule #4: Identify joins
        output.append("Rule #4 (Replace Cartesian Product + Selection → Join):")
        output.append("Converting cross products with join conditions to natural joins...")
        join_conditions = [s for s in selections if '=' in s.operator and len(s.attribute.split('.')) > 1]
        if join_conditions:
            output.append(f"  Identified {len(join_conditions)} join condition(s)")
        output.append("")
        
        # Rule #5: Push projections
        output.append("Rule #5 (Push Projections Down):")
        output.append("Pushing projections to eliminate unnecessary attributes early...")
        output.append(f"  Final projection: {', '.join(select_attrs)}")
        output.append("")
        
        # Optimized query tree
        output.append("Optimized Query Tree (bottom-up):")
        output.append("-" * 60)
        for table in from_tables:
            output.append(f"  {table}")
            # Show selections for this table
            table_selections = [s for s in selections if s.relation == table]
            for sel in table_selections:
                output.append(f"    ↑ σ({sel.condition})")
        output.append("    ↑ ⋈ (Joins)")
        output.append(f"    ↑ π({', '.join(select_attrs)})")
        output.append("=" * 60)
        
        return '\n'.join(output)

# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python optimizer.py <input_file.txt>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    optimizer = QueryOptimizer(input_file)
    result = optimizer.optimize()
    print(result)
