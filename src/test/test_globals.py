import pytest
import sqlparser.globals
import re


class TestGlobals:
	def test_TSQL_SYMBOLIC(self):
		test1 = "ExtraneousText1234569e9!@#$%&^()<9><@123>OtherText,.;';?> <@2>!@`~#$;lkw\"jef<@asdf>"
		soln1 = [
			(m.start('symb'), m.end('symb'), m.group('symb')) 
			for m in sqlparser.globals.TSQL_SYMBOLIC.finditer(test1)
		]
		assert(len(soln1) == 2)
		assert(soln1[0] == (37, 40, '123'))
		assert(soln1[1] == (60, 61, '2'))
	

	def test_TSQL_SYMBOLIC_OUTER(self):
		x = 1
	

	def test_IS_SQL_QUERY(self):
		test1 = "(SELECT) captures this"
		soln1 = sqlparser.globals.IS_SQL_QUERY.match(test1)
		assert(soln1 is not None)

		test2 = "( SELECT) captures this"
		soln2 = sqlparser.globals.IS_SQL_QUERY.match(test2)
		assert(soln2 is not None)

		test3 = "(select ) captures this"
		soln3 = sqlparser.globals.IS_SQL_QUERY.match(test3)
		assert(soln3 is not None)

		test4 = "( *select ) does not capture this"
		soln4 = sqlparser.globals.IS_SQL_QUERY.match(test4)
		assert(soln4 is None)

		test5 = "SELECT) does not capture this"
		soln5 = sqlparser.globals.IS_SQL_QUERY.match(test5)
		assert(soln5 is None)

		test6 = "(select does not capture this"
		soln6 = sqlparser.globals.IS_SQL_QUERY.match(test6)
		assert(soln6 is None)

		test7 = "select does not capture this"
		soln7 = sqlparser.globals.IS_SQL_QUERY.match(test7)
		assert(soln7 is None)

		test8 = "( selected ) does not capture this"
		soln8 = sqlparser.globals.IS_SQL_QUERY.match(test8)
		assert(soln8 is None)
	

	def test_TSQL_STATEMENTS(self):
		test1 = "(from captures this one"
		soln1 = [
			(m.start("keyword"), m.end("keyword"), m.group("keyword")) 
			for m in sqlparser.globals.TSQL_STATEMENTS.finditer(test1)
		]
		assert(len(soln1) == 1)
		assert(soln1[0] == (1, 5, 'from'))

		test2 = "*FROM does not capture this one"
		soln2 = [
			(m.start("keyword"), m.end("keyword"), m.group("keyword")) 
			for m in sqlparser.globals.TSQL_STATEMENTS.finditer(test2)
		]
		assert(len(soln2) == 0)

		test3 = "( FROM) captures this one"
		soln3 = [
			(m.start("keyword"), m.end("keyword"), m.group("keyword")) 
			for m in sqlparser.globals.TSQL_STATEMENTS.finditer(test3)
		]
		assert(len(soln3) == 1)
		assert(soln3[0] == (2, 6, 'FROM'))

		test4 = "FROMWHERE does not capture this one"
		soln4 = [
			(m.start("keyword"), m.end("keyword"), m.group("keyword")) 
			for m in sqlparser.globals.TSQL_STATEMENTS.finditer(test4)
		]
		assert(len(soln4) == 0)

		test5 = "FROM captures both keywords WHERE"
		soln5 = [
			(m.start("keyword"), m.end("keyword"), m.group("keyword")) 
			for m in sqlparser.globals.TSQL_STATEMENTS.finditer(test5)
		]
		assert(len(soln5) == 2)
		assert(soln5[0] == (0, 4, 'FROM'))
		assert(soln5[1] == (28, 33, 'WHERE'))

		test6 = "\nWHERE\nFROM\ncaptures all of these GROUP BY"
		soln6 = [
			(m.start("keyword"), m.end("keyword"), m.group("keyword")) 
			for m in sqlparser.globals.TSQL_STATEMENTS.finditer(test6)
		]
		assert(len(soln6) == 3)
		assert(soln6[0] == (1, 6, 'WHERE'))
		assert(soln6[1] == (7, 11, 'FROM'))
		assert(soln6[2] == (34, 42, 'GROUP BY'))


	def test_TSQL_ROWOPS(self):
		x = 1


	def test_TSQL_VARTABLE_NAMED(self):
		x = 1


	def test_TSQL_VARTABLE_UNNAMED(self):
		x = 1
	

	def test_TSQL_VAR_NAMED(self):
		x = 1


	def test_TSQL_VAR_UNNAMED(self):
		x = 1


	def test_TSQL_SUBQUERY_ALIAS_PREFIX(self):
		x = 1


	def test_TSQL_SUBQUERY_ALIAS_SUFFIX(self):
		x = 1


	def test_TSQL_CTES(self):
		x = 1


	def test_TSQL_JOIN_JOINTYPES(self):
		x = 1


	def test_TSQL_JOIN_MAJOROPS(self):
		x = 1


	def test_TSQL_JOIN_ALLOPS(self):
		x = 1


	def test_TSQL_JOIN_BASETABLE(self):
		x = 1


	def test_TSQL_RHSLHS_VARTABLE_NAMED(self):
		x = 1


	def test_TSQL_RHSLHS_VARTABLE_UNNAMED(self):
		x = 1


	def test_TSQL_BETWEEN_AND(self):
		x = 1


	def test_isnamed(self):
		x = 1
	

	def test_issubquery(self):
		x = 1
	

	def test_issql(self):
		x = 1
	

	def test_extract_between(self):
		x = 1
	

	def test_extract_tablevar(self):
		x = 1
	

	def test_with_outer_symbolics(self):
		x = 1

