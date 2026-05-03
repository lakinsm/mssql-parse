import re
import test_cases
from sqlparser.sqlquery.dfs import DFS
from sqlparser.sqlquery.sqltree import SQLTree


def main():
	opens = [match.start() for match in re.finditer(re.escape('('), test_cases.example1_nested)]
	closes = [match.start() for match in re.finditer(re.escape(')'), test_cases.example1_nested)]
	dfs = DFS(opens, closes)
	
	sqltree = SQLTree(test_cases.example2_nested)
	assert(dfs.traversal == sqltree.dfs.traversal)
	assert(dfs.tree == sqltree.dfs.tree)
	assert(dfs.levels == sqltree.dfs.levels)
	assert(dfs.intervals == sqltree.dfs.intervals)
	
	sqltree = SQLTree(test_cases.example3_comments)
	# Notes 2026-05-03:
	# - Missing FROM in clause 1 of node 0 (check index in internal node split SQLNode)
	# - WHERE is default None in table-var (for var) relationship if not a table/var value
	# 		see WHERE keywords in nodes 16, 19, 26
	sqltree.print()

if __name__ == '__main__':
	main()
	