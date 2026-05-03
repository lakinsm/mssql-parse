import re
import sys
import sqlparser.globals
from sqlparser.sqlquery.sqlprepost import SQLPrePost
from sqlparser.sqlquery.sqloffset import SQLOffset
from sqlparser.sqlquery.sqlfetch import SQLFetch
from sqlparser.sqlquery.sqlwhere import SQLWhere
from sqlparser.sqlquery.sqlselect import SQLSelect
from sqlparser.sqlquery.sqlwith import SQLWith
from sqlparser.sqlquery.sqlfromjoin import SQLFromJoin


class SQLNode:
	"""
	One (sub-)query and its components.

	- Main
		- SELECT
			- DISTINCT, TOP
			- AS, =
			- variables plain, "", [] AS plain, "", ''
				- subquery +/- named
				- Other keywords +/- ()
		- FROM
			- tables plain, "", [] AS plain, '', ""
			- JOIN table plain, "", [] AS plain, '', ""; subquery AS plain, "", []
				- OUTER, INNER, LEFT, RIGHT, FULL OUTER
				- ON table.var plain, "", [] = table.var plain, "", []
				- ON subquery AS plain, "", []
		- WHERE
			- table.var plain, "", []
				- Operator =, <>, >, >=, <=, !=, IS NULL, IS NOT NULL, &, |, ^
				- AND, OR, NOT, BETWEEN, IN, LIKE, EXISTS +/- NOT
		- GROUP BY
			- HAVING
		- ORDER BY
			- Variable +/- <order>, ...
			- Order: ASC, DESC
		- OFFSET
			- ROWS
		- FETCH
			- NEXT <int> ROWS ONLY
	- Row operations
		- UNION +/- ALL
		- INTERSECT
		- EXCEPT
	- Table modifications
		- INSERT INTO
		- INTO
		- ___ TABLE
			- CREATE, ALTER, DROP
			- Suffix: IF/IF NOT EXISTS
	"""
	def __init__(self, query_text: str, non_subqueries: dict) -> None:
		self.issql = sqlparser.globals.issql(query_text)
		self.row_ops = [(m.group(1), m.start(), m.end()) for m in sqlparser.globals.TSQL_ROWOPS.finditer(query_text)]
		self.internal_degree = len(self.row_ops) + 1
		self.query_text = []
		self.non_subqueries = non_subqueries
		self.tables = {}
		self.relations = {}
		self.element_types = {
			'PRETEXT': SQLPrePost,
			'WITH': SQLWith,
			'SELECT': SQLSelect,
			'FROM': SQLFromJoin,
			'WHERE': SQLWhere,
			'GROUP BY': SQLPrePost,
			'ORDER BY': SQLPrePost,
			'OFFSET': SQLOffset,
			'FETCH': SQLFetch
        }
		if self.row_ops:
			self.query_text.append(query_text[:self.row_ops[0][1]])
			for i in range(len(self.row_ops)):
				try:
					self.query_text.append(query_text[self.row_ops[i][2]:self.row_ops[i+1][1]])
				except IndexError:
					self.query_text.append(query_text[self.row_ops[i][2]:])
		else:
			self.query_text.append(query_text)
		
		statement_boundaries = []
		for r in range(self.internal_degree):
			statement_boundaries.append({})
			keyword_breaks = [(m.start(), m.group(1).upper()) 
								for m in sqlparser.globals.TSQL_STATEMENTS.finditer(self.query_text[r])]
			for i in range(len(keyword_breaks)):
				start, keyword = keyword_breaks[i]
				if i == 0:
					pretext = self.query_text[r][:start]
					if pretext.strip():
						statement_boundaries[r].setdefault('PRETEXT', []).append((0, start),)
				if (i+1) == len(keyword_breaks):
					statement_boundaries[r].setdefault(keyword, []).append((start, len(self.query_text[r])),)
				else:
					next_start = keyword_breaks[i+1][0]
					statement_boundaries[r].setdefault(keyword, []).append((start, next_start),)
		
		self.clauses = [{
			'PRETEXT': None,
			'WITH': None,
			'SELECT': None,
			'FROM': None,
			'WHERE': None,
			'GROUP BY': None,
			'ORDER BY': None,
			'OFFSET': None,
			'FETCH': None
		} for _ in  range(self.internal_degree)]
		for r in range(self.internal_degree):
			for keyword, breaks in statement_boundaries[r].items():
				for start, stop in breaks:
					self.clauses[r][keyword] = self.element_types[keyword]( 
						keyword,
						start,
						stop,
						self.query_text[r][start:stop],
						self.non_subqueries
					)
		# TODO: resolve unclaimed vars within elements
		# TODO: validate selects & by clauses with tables in from/joins
		# TODO: validate row operations (requires same columns)
		
	