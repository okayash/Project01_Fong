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
    is_join_condition: bool = False
    
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

@dataclass
class Join:
    left_table: str
    right_table: str
    join_type: str  # INNER, LEFT, RIGHT, FULL
    condition: str
    left_alias: str = ""
    right_alias: str = ""

class QueryOptimizer:
    def __init__(self, file_path: str):
        self.schema: Dict[str, Relation] = {}
        self.query = ""
        self.joins: List[Join] = []
        self.table_aliases: Dict[str, str] = {}  # alias -> table_name
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
    
    def parse_query(self) -> Tuple[List[str], List[str], str, str, str]:
        """Parse SELECT, FROM, WHERE, GROUP BY, and HAVING clauses"""
        # Extract SELECT clause
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', self.query, re.IGNORECASE | re.DOTALL)
        select_attrs = [s.strip() for s in select_match.group(1).split(',')] if select_match else []
        
        # Extract FROM clause - handle both implicit and explicit joins
        from_match = re.search(r'FROM\s+(.*?)(?:WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|$)', self.query, re.IGNORECASE | re.DOTALL)
        from_tables = []
        
        if from_match:
            from_text = from_match.group(1).strip()
            
            # Check for explicit JOIN syntax
            join_pattern = r'(INNER\s+JOIN|LEFT\s+(?:OUTER\s+)?JOIN|RIGHT\s+(?:OUTER\s+)?JOIN|FULL\s+(?:OUTER\s+)?JOIN)'
            
            if re.search(join_pattern, from_text, re.IGNORECASE):
                # Parse explicit joins
                self.parse_explicit_joins(from_text)
                # Extract all tables from joins
                for join in self.joins:
                    if join.left_table not in from_tables:
                        from_tables.append(join.left_table)
                    if join.right_table not in from_tables:
                        from_tables.append(join.right_table)
            else:
                # Parse comma-separated table list (implicit cross product)
                table_parts = [t.strip() for t in from_text.split(',')]
                for part in table_parts:
                    tokens = part.split()
                    table_name = tokens[0].upper()
                    from_tables.append(table_name)
                    # Store alias if provided
                    if len(tokens) > 1:
                        alias = tokens[1].upper()
                        self.table_aliases[alias] = table_name
                    else:
                        self.table_aliases[table_name] = table_name
        
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP\s+BY|HAVING|ORDER\s+BY|$)', self.query, re.IGNORECASE | re.DOTALL)
        where_clause = where_match.group(1).strip() if where_match else ""
        
        # Extract GROUP BY clause
        group_by_match = re.search(r'GROUP\s+BY\s+(.*?)(?:HAVING|ORDER\s+BY|$)', self.query, re.IGNORECASE | re.DOTALL)
        group_by_clause = group_by_match.group(1).strip() if group_by_match else ""
        
        # Extract HAVING clause
        having_match = re.search(r'HAVING\s+(.*?)(?:ORDER\s+BY|$)', self.query, re.IGNORECASE | re.DOTALL)
        having_clause = having_match.group(1).strip() if having_match else ""
        
        return select_attrs, from_tables, where_clause, group_by_clause, having_clause
    
    def parse_explicit_joins(self, from_text: str):
        """Parse explicit JOIN syntax"""
        # Pattern to match table with optional alias
        table_pattern = r'(\w+)(?:\s+(\w+))?'
        
        # Split by different join types while preserving the join keyword
        parts = re.split(r'(INNER\s+JOIN|LEFT\s+(?:OUTER\s+)?JOIN|RIGHT\s+(?:OUTER\s+)?JOIN|FULL\s+(?:OUTER\s+)?JOIN)', 
                        from_text, flags=re.IGNORECASE)
        
        # First table (before any JOIN)
        first_table_match = re.match(table_pattern, parts[0].strip())
        if first_table_match:
            left_table = first_table_match.group(1).upper()
            left_alias = first_table_match.group(2).upper() if first_table_match.group(2) else left_table
            self.table_aliases[left_alias] = left_table
        else:
            left_table = left_alias = ""
        
        # Process each JOIN
        i = 1
        while i < len(parts) - 1:
            join_type = parts[i].strip().upper()
            join_type = join_type.replace('OUTER', '').replace('JOIN', '').strip()
            if not join_type:
                join_type = 'INNER'
            
            # Extract right table and ON condition
            rest = parts[i + 1].strip()
            on_match = re.search(r'(.*?)\s+ON\s+(.*)', rest, re.IGNORECASE | re.DOTALL)
            
            if on_match:
                right_table_text = on_match.group(1).strip()
                on_condition = on_match.group(2).strip()
                
                # Remove next JOIN keyword from condition if present
                for j in range(i + 2, len(parts)):
                    if re.match(r'(INNER|LEFT|RIGHT|FULL)', parts[j], re.IGNORECASE):
                        # Split condition before next join
                        next_join_pos = on_condition.upper().find(parts[j].split()[0].upper())
                        if next_join_pos > 0:
                            on_condition = on_condition[:next_join_pos].strip()
                        break
                
                # Parse right table
                right_table_match = re.match(table_pattern, right_table_text)
                if right_table_match:
                    right_table = right_table_match.group(1).upper()
                    right_alias = right_table_match.group(2).upper() if right_table_match.group(2) else right_table
                    self.table_aliases[right_alias] = right_table
                    
                    self.joins.append(Join(
                        left_table=left_table,
                        right_table=right_table,
                        join_type=join_type,
                        condition=on_condition,
                        left_alias=left_alias,
                        right_alias=right_alias
                    ))
                    
                    # Next join's left table is current right table
                    left_table = right_table
                    left_alias = right_alias
            
            i += 2
    
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
                
                # Check if this is a join condition (both sides are attributes)
                is_join = '.' in value or value.replace('_', '').isalpha()
                
                selections.append(Selection(
                    condition=cond,
                    attribute=attr,
                    operator=operator,
                    value=value,
                    relation="",
                    is_join_condition=is_join
                ))
        
        return selections
    
    def assign_selections_to_relations(self, selections: List[Selection], tables: List[str]):
        """Assign each selection to its appropriate relation"""
        for sel in selections:
            # First try to resolve using table aliases
            for alias, table_name in self.table_aliases.items():
                # Extract alias from condition
                cond_parts = sel.condition.split('.')
                if len(cond_parts) > 0:
                    cond_alias = cond_parts[0].strip().upper()
                    if cond_alias == alias and table_name in self.schema:
                        if sel.attribute in self.schema[table_name].attributes:
                            sel.relation = table_name
                            break
            
            # Fallback: try direct table match
            if not sel.relation:
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
        
        # Show query structure
        output.append("Query Structure:")
        output.append(f"  Tables: {', '.join(from_tables)}")
        if self.joins:
            output.append(f"  Explicit Joins: {len(self.joins)}")
            for join in self.joins:
                output.append(f"    {join.left_table} {join.join_type} JOIN {join.right_table} ON {join.condition}")
        output.append("")
        
        # Rule #1 & #2: Cascade selections and push down
        output.append("Rule #1 (Cascade of Selections):")
        output.append("Breaking conjunctive WHERE conditions into individual selections...")
        selections = self.extract_selections(where_clause)
        
        # Also extract conditions from explicit JOIN ON clauses
        join_selections = []
        if self.joins:
            for join in self.joins:
                join_sels = self.extract_selections(join.condition)
                for js in join_sels:
                    js.is_join_condition = True
                join_selections.extend(join_sels)
        
        all_selections = selections + join_selections
        self.assign_selections_to_relations(all_selections, from_tables)
        
        # Separate filter conditions from join conditions
        filter_conditions = [s for s in all_selections if not s.is_join_condition]
        join_conditions = [s for s in all_selections if s.is_join_condition]
        
        if filter_conditions:
            output.append("  Filter Conditions:")
            for sel in filter_conditions:
                output.append(f"    σ({sel.condition})")
        
        if join_conditions:
            output.append("  Join Conditions:")
            for sel in join_conditions:
                output.append(f"    {sel.condition}")
        output.append("")
        
        output.append("Rule #2 (Push Selections Down):")
        output.append("Pushing selections close to base relations...")
        for sel in filter_conditions:
            if sel.relation:
                output.append(f"  σ({sel.condition}) → {sel.relation}")
        output.append("")
        
        # Rule #3: Order by selectivity
        output.append("Rule #3 (Apply Selections with Smallest Selectivity First):")
        filter_conditions.sort(key=lambda s: s.selectivity_score(self.schema))
        output.append("Reordering selections by selectivity (most restrictive first):")
        for i, sel in enumerate(filter_conditions, 1):
            score = sel.selectivity_score(self.schema)
            selectivity_desc = self.get_selectivity_description(sel, score)
            output.append(f"  {i}. σ({sel.condition}) on {sel.relation} (score: {score}) - {selectivity_desc}")
        output.append("")
        
        # Rule #4: Identify joins
        output.append("Rule #4 (Replace Cartesian Product + Selection → Join):")
        if self.joins:
            output.append(f"Query uses explicit JOIN syntax ({len(self.joins)} join(s)):")
            for join in self.joins:
                join_symbol = self.get_join_symbol(join.join_type)
                output.append(f"  {join.left_table} {join_symbol} {join.right_table} ON ({join.condition})")
        else:
            output.append("Converting cross products with join conditions to natural joins...")
            if join_conditions:
                output.append(f"  Identified {len(join_conditions)} join condition(s):")
                for jc in join_conditions:
                    output.append(f"    {jc.condition}")
            else:
                output.append("  No join conditions found (cross product)")
        output.append("")
        
        # Rule #5: Push projections
        output.append("Rule #5 (Push Projections Down):")
        output.append("Pushing projections to eliminate unnecessary attributes early...")
        output.append(f"  Final projection: {', '.join(select_attrs)}")
        
        # Determine which attributes are needed from each table
        needed_attrs = self.determine_needed_attributes(select_attrs, all_selections, from_tables)
        if needed_attrs:
            output.append("  Attributes needed per relation:")
            for table, attrs in needed_attrs.items():
                output.append(f"    {table}: {{{', '.join(attrs)}}}")
        output.append("")
        
        # Optimized query tree
        output.append("Optimized Query Tree (bottom-up):")
        output.append("-" * 60)
        
        if self.joins:
            # Build tree for explicit joins
            output.append(f"  {self.joins[0].left_table}")
            table_selections = [s for s in filter_conditions if s.relation == self.joins[0].left_table]
            for sel in table_selections:
                output.append(f"    ↑ σ({sel.condition})")
            if self.joins[0].left_table in needed_attrs:
                output.append(f"    ↑ π({', '.join(needed_attrs[self.joins[0].left_table])})")
            
            for join in self.joins:
                join_symbol = self.get_join_symbol(join.join_type)
                output.append(f"  {join_symbol} {join.right_table} ON ({join.condition})")
                table_selections = [s for s in filter_conditions if s.relation == join.right_table]
                for sel in table_selections:
                    output.append(f"    ↑ σ({sel.condition})")
                if join.right_table in needed_attrs:
                    output.append(f"    ↑ π({', '.join(needed_attrs[join.right_table])})")
        else:
            # Build tree for implicit joins
            for table in from_tables:
                output.append(f"  {table}")
                table_selections = [s for s in filter_conditions if s.relation == table]
                for sel in table_selections:
                    output.append(f"    ↑ σ({sel.condition})")
                if table in needed_attrs:
                    output.append(f"    ↑ π({', '.join(needed_attrs[table])})")
            
            if join_conditions:
                output.append("    ↑ ⋈ (Joins)")
                for jc in join_conditions:
                    output.append(f"       Condition: {jc.condition}")
            else:
                output.append("    ↑ × (Cross Product)")
        
        output.append(f"    ↑ π({', '.join(select_attrs)}) [Final Projection]")
        output.append("=" * 60)
        
        return '\n'.join(output)
    
    def get_join_symbol(self, join_type: str) -> str:
        """Return appropriate join symbol"""
        join_type = join_type.upper()
        if 'LEFT' in join_type:
            return '⟕'
        elif 'RIGHT' in join_type:
            return '⟖'
        elif 'FULL' in join_type:
            return '⟗'
        else:
            return '⋈'
    
    def get_selectivity_description(self, sel: Selection, score: int) -> str:
        """Return human-readable selectivity description"""
        if score == 1:
            return "Primary key equality (most selective)"
        elif score == 2:
            return "Primary key range"
        elif score == 3:
            return "Unique key equality"
        elif score == 4:
            return "Unique key range"
        elif score == 5:
            return "Equality on regular attribute"
        elif score == 6:
            return "Range predicate"
        elif score == 7:
            return "Not-equal predicate"
        else:
            return "Low selectivity"
    
    def determine_needed_attributes(self, select_attrs: List[str], 
                                   selections: List[Selection], 
                                   tables: List[str]) -> Dict[str, Set[str]]:
        """Determine which attributes are needed from each table"""
        needed = {}
        
        for table in tables:
            attrs = set()
            
            # Add attributes from SELECT clause
            for sel_attr in select_attrs:
                if '.' in sel_attr:
                    parts = sel_attr.split('.')
                    alias = parts[0].upper()
                    attr = parts[1].upper()
                    if alias in self.table_aliases and self.table_aliases[alias] == table:
                        attrs.add(attr)
                else:
                    # Check if attribute belongs to this table
                    attr = sel_attr.strip().upper()
                    if table in self.schema and attr in self.schema[table].attributes:
                        attrs.add(attr)
            
            # Add attributes from conditions
            for sel in selections:
                if sel.relation == table:
                    attrs.add(sel.attribute)
            
            # Add attributes from join conditions
            for join in self.joins:
                if join.left_table == table or join.right_table == table:
                    # Parse join condition
                    cond_parts = join.condition.split('=')
                    for part in cond_parts:
                        if '.' in part:
                            alias, attr = part.strip().split('.')
                            alias = alias.upper()
                            attr = attr.upper()
                            if alias in self.table_aliases and self.table_aliases[alias] == table:
                                attrs.add(attr)
            
            if attrs:
                needed[table] = attrs
        
        return needed

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
