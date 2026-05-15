import re

TSQL_SYMBOLIC = re.compile(r'<@(?P<symb>[0-9]+)>', flags=re.MULTILINE)
TSQL_SYMBOLIC_OUTER = re.compile(r'(?P<outer_symb><@[0-9]+>)(?P<nested_symb>[\.\^]?(<@[0-9]+>[\.\^-]?)*)', flags=re.IGNORECASE | re.MULTILINE)
IS_SQL_QUERY = re.compile(r'((\(.*?[\s]+|\()(?P<select>SELECT)([\s]+.*?\)|\)))', flags=re.IGNORECASE | re.MULTILINE)
TSQL_STATEMENTS = re.compile(r'(^|[\(\s]+)(?P<keyword>(WITH|SELECT|FROM|WHERE|GROUP BY|ORDER BY|OFFSET|FETCH))($|[\)\s]+)', flags=re.IGNORECASE | re.MULTILINE)
TSQL_ROWOPS = re.compile(r'\s*(INTERSECT|EXCEPT|UNION ALL|UNION)\s*', flags=re.IGNORECASE | re.MULTILINE)
TSQL_VARTABLE_NAMED = re.compile(r'(?=([\"\[]?(?P<table>[<>@A-Za-z0-9_]+)[\"\]]?\.[\"\[]?(?P<varname>[<>@A-Za-z0-9_]+|[\*])[\"\]]?(\s+AS\s+|\s)[\"\']?(?P<alias>[<>@A-Za-z0-9_]+)[\"\']?\s*(,|$)))', flags=re.IGNORECASE | re.MULTILINE)
TSQL_VARTABLE_UNNAMED = re.compile(r'(?=([\"\[]?(?P<table>[<>@A-Za-z0-9_]+)[\"\]]?\.[\"\[]?(?P<varname>[<>@A-Za-z0-9_]+|[\*])[\"\]]?\s*(,|$)))', flags=re.IGNORECASE | re.MULTILINE)
TSQL_VAR_NAMED = re.compile(r'(?=([^\.][\"\[]?(?P<varname>[<>@A-Za-z0-9_]+|[\*])[\"\]]?(\s+AS\s+|\s)[\"\']?(?P<alias>[<>@A-Za-z0-9_]+)[\"\']?\s*(,|$)))', flags=re.IGNORECASE | re.MULTILINE)
TSQL_VAR_UNNAMED = re.compile(r'(?=([^\.][\"\[]?(?P<varname>[<>@A-Za-z0-9_]+|[\*])[\"\]]?\s*(,|$)))', flags=re.IGNORECASE | re.MULTILINE)
TSQL_SUBQUERY_ALIAS_PREFIX = re.compile(r'[\"\[]?(?P<alias>[A-Za-z0-9_]+)[\"\]]?\s+AS\s+\(', flags=re.IGNORECASE | re.MULTILINE)
TSQL_SUBQUERY_ALIAS_SUFFIX = re.compile(r'\)(\s+AS\s+|\s+)[\"\']?(?P<alias>[A-Za-z0-9_]+)[\"\']?\s*(,|$)', flags=re.IGNORECASE | re.MULTILINE)
TSQL_CTES = re.compile(r'\s*(?P<alias>[A-Za-z0-9_]+)\s+AS\s+(?P<table>[<>@A-Za-z0-9_]+)(\s|,|\.|$)', flags=re.IGNORECASE | re.MULTILINE)
TSQL_JOIN_JOINTYPES = re.compile(r'\s*(?P<jointype>(FULL OUTER JOIN|LEFT OUTER JOIN|RIGHT OUTER JOIN|FULL JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|CROSS JOIN|SELF JOIN|JOIN))\s+', flags=re.IGNORECASE | re.MULTILINE)
TSQL_JOIN_MAJOROPS = re.compile(r'(?P<majop>(ON|AND|OR))', flags=re.IGNORECASE | re.MULTILINE)
TSQL_JOIN_ALLOPS = re.compile(r'(?P<op>\s+(<>|!=|>=|<=|!<|!>|\+=|\-=|\*=|/=|%=|&=|\|=|\^=|\|\||IS NOT NULL|IS NULL|NOT IN|AND|OR|NOT|IN|BETWEEN|LIKE|EXISTS|ALL|ANY|SOME|[\+\-\*/%<>=~&\|\^])\s+)', flags=re.IGNORECASE | re.MULTILINE)
TSQL_JOIN_BASETABLE = re.compile(r'(?P<jointype>(FULL OUTER JOIN|LEFT OUTER JOIN|RIGHT OUTER JOIN|FULL JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|CROSS JOIN|SELF JOIN|JOIN|FROM))\s+(?P<basetable>[A-Za-z0-9_]+)(\s*|$)', flags=re.IGNORECASE | re.MULTILINE)
TSQL_RHSLHS_VARTABLE_NAMED = re.compile(r'[\"\[]?(?P<table>[<>@A-Za-z0-9_]+)[\"\]]?\.[\"\[]?(?P<varname>[<>@A-Za-z0-9_]+)[\"\]]?', flags=re.IGNORECASE | re.MULTILINE)
TSQL_RHSLHS_VARTABLE_UNNAMED = re.compile(r'[\"\[]?(?P<varname>[<>@A-Za-z0-9_]+)[\"\]]?', flags=re.IGNORECASE | re.MULTILINE)
TSQL_BETWEEN_AND = re.compile(r'\s+(?P<between>BETWEEN)((?!AND).)+(?P<and>AND)\s+', flags=re.IGNORECASE | re.MULTILINE)
# TSQL_ = re.compile(r'', flags=re.IGNORECASE | re.MULTILINE)

LOGICAL_OPERATORS = {
    'AND',
    'OR',
    'NOT'
}


ARITHMETIC_OPERATORS = {
    '+', '-', '/', '|',
    '%', '&', '^', '*'
}


ODBC_KEYWORDS = {
	'ABSOLUTE',
	'ACTION',
	'ADA',
	'ADD',
	'ALL',
	'ALLOCATE',
	'ALTER',
	'AND',
	'ANY',
	'ARE',
	'AS',
	'ASC',
	'ASSERTION',
	'AT',
	'AUTHORIZATION',
	'AVG',
	'BEGIN',
	'BETWEEN',
	'BIT',
	'BIT_LENGTH',
	'BOTH',
	'BY',
	'CASCADE',
	'CASCADED',
	'CASE',
	'CAST',
	'CATALOG',
	'CHAR',
	'CHAR_LENGTH',
	'CHARACTER',
	'CHARACTER_LENGTH',
	'CHECK',
	'CLOSE',
	'COALESCE',
	'COLLATE',
	'COLLATION',
	'COLUMN',
	'COMMIT',
	'CONNECT',
	'CONNECTION',
	'CONSTRAINT',
	'CONSTRAINTS',
	'CONTINUE',
	'CONVERT',
	'CORRESPONDING',
	'COUNT',
	'CREATE',
	'CROSS',
	'CURRENT',
	'CURRENT_DATE',
	'CURRENT_TIME',
	'CURRENT_TIMESTAMP',
	'CURRENT_USER',
	'CURSOR',
	'DATE',
	'DAY',
	'DEALLOCATE',
	'DEC',
	'DECIMAL',
	'DECLARE',
	'DEFAULT',
	'DEFERRABLE',
	'DEFERRED',
	'DELETE',
	'DESC',
	'DESCRIBE',
	'DESCRIPTOR',
	'DIAGNOSTICS',
	'DISCONNECT',
	'DISTINCT',
	'DOMAIN',
	'DOUBLE',
	'DROP',
	'ELSE',
	'END',
	'END-EXEC',
	'ESCAPE',
	'EXCEPT',
	'EXCEPTION',
	'EXEC',
	'EXECUTE',
	'EXISTS',
	'EXTERNAL',
	'EXTRACT',
	'FALSE',
	'FETCH',
	'FIRST',
	'FLOAT',
	'FOR',
	'FOREIGN',
	'FORTRAN',
	'FOUND',
	'FROM',
	'FULL',
	'GET',
	'GLOBAL',
	'GO',
	'GOTO',
	'GRANT',
	'GROUP',
	'HAVING',
	'HOUR',
	'IDENTITY',
	'IMMEDIATE',
	'IN',
	'INCLUDE',
	'INDEX',
	'INDICATOR',
	'INITIALLY',
	'INNER',
	'INPUT',
	'INSENSITIVE',
	'INSERT',
	'INT',
	'INTEGER',
	'INTERSECT',
	'INTERVAL',
	'INTO',
	'IS',
	'ISOLATION',
	'JOIN',
	'KEY',
	'LANGUAGE',
	'LAST',
	'LEADING',
	'LEFT',
	'LEVEL',
	'LIKE',
	'LOCAL',
	'LOWER',
	'MATCH',
	'MAX',
	'MIN',
	'MINUTE',
	'MODULE',
	'MONTH',
	'NAMES',
	'NATIONAL',
	'NATURAL',
	'NCHAR',
	'NEXT',
	'NO',
	'NONE',
	'NOT',
	'NULL',
	'NULLIF',
	'NUMERIC',
	'OCTET_LENGTH',
	'OF',
	'ON',
	'ONLY',
	'OPEN',
	'OPTION',
	'OR',
	'ORDER',
	'OUTER',
	'OUTPUT',
	'OVERLAPS',
	'PAD',
	'PARTIAL',
	'PASCAL',
	'POSITION',
	'PRECISION',
	'PREPARE',
	'PRESERVE',
	'PRIMARY',
	'PRIOR',
	'PRIVILEGES',
	'PROCEDURE',
	'PUBLIC',
	'READ',
	'REAL',
	'REFERENCES',
	'RELATIVE',
	'RESTRICT',
	'REVOKE',
	'RIGHT',
	'ROLLBACK',
	'ROWS',
	'SCHEMA',
	'SCROLL',
	'SECOND',
	'SECTION',
	'SELECT',
	'SESSION',
	'SESSION_USER',
	'SET',
	'SIZE',
	'SMALLINT',
	'SOME',
	'SPACE',
	'SQL',
	'SQLCA',
	'SQLCODE',
	'SQLERROR',
	'SQLSTATE',
	'SQLWARNING',
	'SUBSTRING',
	'SUM',
	'SYSTEM_USER',
	'TABLE',
	'TEMPORARY',
	'THEN',
	'TIME',
	'TIMESTAMP',
	'TIMEZONE_HOUR',
	'TIMEZONE_MINUTE',
	'TO',
	'TRAILING',
	'TRANSACTION',
	'TRANSLATE',
	'TRANSLATION',
	'TRIM',
	'TRUE',
	'UNION',
	'UNIQUE',
	'UNKNOWN',
	'UPDATE',
	'UPPER',
	'USAGE',
	'USER',
	'USING',
	'VALUE',
	'VALUES',
	'VARCHAR',
	'VARYING',
	'VIEW',
	'WHEN',
	'WHENEVER',
	'WHERE',
	'WITH',
	'WORK',
	'WRITE',
	'YEAR',
	'ZONE',
    ')',
    '(',
    ';',
    ','
}

TYPEMAP = {
	'NVARCHAR': 'TEXT',
	'VARCHAR': 'TEXT',
	'NCHAR': 'TEXT',
	'CHAR': 'TEXT',
	'BINARY': 'TEXT',
	'VARBINARY': 'TEXT',
	'TEXT': 'TEXT',
	'TINYTEXT': 'TEXT',
	'MEDIUMTEXT': 'TEXT',
	'LONGTEXT': 'TEXT',
	'TINYBLOB': 'BLOB',
	'MEDIUMBLOB': 'BLOB',
	'LONGBLOB': 'BLOB',
	'BIT': 'INTEGER',
	'TINYINT': 'INTEGER',
	'BOOL': 'INTEGER',
	'SMALLINT': 'INTEGER',
	'MEDIUMINT': 'INTEGER',
	'INT': 'INTEGER',
	'INTEGER': 'INTEGER',
	'BIGINT': 'INTEGER',
	'SMALLMONEY': 'REAL',
	'MONEY': 'REAL',
	'FLOAT': 'REAL',
	'DOUBLE': 'REAL',
	'DECIMAL': 'REAL',
	'DEC': 'REAL',
	'REAL': 'REAL',
	'DATE': 'TEXT',
	'DATETIME': 'TEXT',
	'DATETIME2': 'TEXT',
	'SMALLDATETIME': 'TEXT',
	'DATETIMEOFFSET': 'TEXT',
	'TIMESTAMP': 'TEXT',
	'TIME': 'TEXT',
	'YEAR': 'TEXT'
}

def isnamed(query_text: str) -> tuple[bool, list]:
	"""
	Is this (sub-)query or SQL element named (adjacent to an AS)?

	Returns: (bool, [str(element_name),]) if prefix/suffix
				(bool, [(str(col_nam), str(alias_name),]) if object
	"""
	# Check prefix/suffix for subqueries/CTEs
	prefix = TSQL_SUBQUERY_ALIAS_PREFIX.search(query_text)
	suffix = TSQL_SUBQUERY_ALIAS_SUFFIX.search(query_text)

	# Check for tables/vars with aliases
	object_matches = []
	consumed = set()
	# 1. table.var AS? alias
	for m in TSQL_VARTABLE_NAMED.finditer(query_text):
		start = m.start()
		stop = start + len(m.groups()[0])
		match_interval = set(range(start, stop))
		if not consumed.intersection(match_interval):
			table, varname, alias = m.group('table', 'varname', 'alias')
			if alias not in ODBC_KEYWORDS:
				object_matches.append(('{}.{}'.format(table, varname), alias),)
		consumed.update(match_interval)

	# 2. var AS? alias
	for m in TSQL_VAR_NAMED.finditer(query_text):
		start = m.start()
		stop = start + len(m.groups()[0])
		match_interval = set(range(start, stop))
		if not consumed.intersection(match_interval):
			varname, alias = m.group('varname', 'alias')
			if alias not in ODBC_KEYWORDS:
				object_matches.append((varname, alias),)
		consumed.update(match_interval)

	query_val = [bool(x) for x in [prefix, suffix]]
	true_count = query_val.count(True)
	assert(true_count <= 1)
	if true_count:
		query_name = [prefix, suffix][query_val.index(True)]
	ret_bool = True if any([prefix, suffix, object_matches]) else False
	if ret_bool:
		if any(query_val):
			ret_val = [query_name.group(1)]
		else:
			ret_val = object_matches
	else:
		ret_val = []
	return ret_bool, ret_val


def issubquery(query_text: str, require_name: bool = False) -> bool:
	"""
	Determine if text is a TSQL subquery.

	Assumptions:
		- This query does not contain nested queries (remove or mask them ahead of time)
		- Subqueries in TSQL must:
			1. Be a subquery (contain a SELECT)
			2. Begin and end with parentheses
		- Subqueries can:
			3. Be named
	"""
	query_flag = IS_SQL_QUERY.search(query_text) is not None
	name = isnamed(query_text)[0] if require_name else True
	return query_flag and name


def issql(query_text: str) -> bool:
	"""
	Does this "node" contain an outer-scope SELECT statement?
	"""
	quote_idxs = [m.start() for m in re.finditer('[\'"]', query_text)]
	assert(len(quote_idxs) % 2 == 0)
	ignore_idxs = set([y for x in [list(range(quote_idxs[i], quote_idxs[i+1])) 
										for i in range(0, len(quote_idxs), 2)] 
							for y in x])
	query_nostring = ''.join(x for i, x in enumerate(query_text) if i not in ignore_idxs)
	return bool(re.search(r'select', query_nostring, flags=re.IGNORECASE))


def extract_between(clause_text: str) -> tuple:
	"""
	Extract clauses of format X BETWEEN Y AND Z.
	"""
	return((m.span('between'), m.span('and')) for m in TSQL_BETWEEN_AND.finditer(clause_text))
	

def extract_tablevar(rhslhs_text: str) -> tuple[str, str]:
	"""
	Return table - var relation if present (no alias searching here),
	otherwise return (None, var).  Symbolics are included as vars.
	"""
	seen = set()
	seen_idxs = set()
	table_vars = tuple()
	for m in TSQL_RHSLHS_VARTABLE_NAMED.finditer(rhslhs_text):
		table, var = m.group('table', 'varname')
		spans = [x for x in [m.start('table'), m.end('table'), m.start('varname'), m.end('varname')] if x is not None]
		match_start, match_end = min(spans), max(spans)
		match_idxs = set(x for x in range(match_start, match_end))
		unique = '-'.join([x if x else '' for x in (table, var)])
		if (unique not in seen) and not (seen_idxs.intersection(match_idxs)):
			table_vars += (table, var),
			seen.add(unique)
			seen_idxs.update(match_idxs)
	for m in TSQL_RHSLHS_VARTABLE_UNNAMED.finditer(rhslhs_text):
		var = m.group('varname')
		match_idxs = set(x for x in range(m.start('varname'), m.end('varname')))
		unique = '-'.join([x if x else '' for x in (None, var)])
		if (unique not in seen) and not (seen_idxs.intersection(match_idxs)):
			table_vars += (None, var),
			seen.add(unique)
			seen_idxs.update(match_idxs)
	if not table_vars:
		table_vars += (None, None),
	return table_vars


def with_outer_symbolics(clause_text: str) -> str:
	"""
	Return the clause_text with only top-level symbolics; remove nested symbolics.
	"""
	matches = TSQL_SYMBOLIC_OUTER.finditer(clause_text)
	exclude_idxs = set(x for y in (range(m.end('outer_symb'), m.end()) for m in matches) for x in y)
	return ''.join(x for i, x in enumerate(clause_text) if i not in exclude_idxs)
