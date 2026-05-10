
example1_nested = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)'

example2_nested = '1(3(5(7)9(12)15(18)21(24(27(30)33)36)39)42)45(48(51)54)57(60)63(66(69)72)")"\')\' SELECT'

example3_comments = """
		/* This is an example query with comments.
		Select the following examples from example
		for example and order by example.
		*/
		BEGIN

		-- Some variable definitions
		DECLARE mychar1 = NVARCHAR(80);
		DECLARE mydate1 = DATE;
		SET mychar1 = 'example4';
		SET mydate1 = '2100-10-15';

		WITH
		cte1 AS
		(
			SELECT *
			FROM othertable1
			JOIN othertable2
				ON othertable1.field1 = othertable2.field2
			WHERE othertable1.field3 = 'filter1'
		),
		cte2 AS
		(
			SELECT
				othertable3.field1 AS "myvar1",
				cte1.field1 AS 'myvar2'
			FROM othertable3
			JOIN cte1
				ON othertable3.field2 = cte1.field1
		),
		cte3 AS
		(
			SELECT
				othertable4.key1,
				SUM(othertable4.count) AS sumcount
			FROM othertable4
			WHERE othertable4.field1 = 'value1'
			GROUP BY
				othertable4.count
		),
		cte4 AS
		(
			SELECT *,
			(SELECT TOP 1 keyvar FROM subtable1 WHERE keyvar = 'keyvalue') "aliassqval"
			FROM blankettable globalias
		),
		cte6 AS
		(
			SELECT
				othertable4.key1,
				othertable4.key2
			FROM othertable4
			WHERE 
				key3 <> 'implied column value'
				AND othertable4.key4 >= 1
		),
		cte5 AS
		(
			SELECT
				unnamedvar1 AS key1,
				unnamedvar2 as key2
			FROM relativetable reltable
			JOIN cte6
				USING (key1, [key2])
			WHERE unnamedvar1 = 'othervalue1'
		),
		cte7 AS
		(
			SELECT
				ROW_NUMBER() OVER (PARTITION mytable1.field2 ORDER BY mytable1.field3 DESC) AS rnum
			FROM mytable1
		),
		cte8 AS
		(
			SELECT
				SUM(aliasmt2.field2),
				COUNT(*)
			FROM mytable2 aliasmt2
			GROUP BY mytable2.field2
		)
		SELECT 
			mytable1.*,
			mytable2.foo1,
			mytable2.bar1 b1,
			mytable3.foo1 AS "t3foo1",
			mytable4.bar2,  -- Example comment
			mytable5.*,
			(
				SELECT TOP 1 mytable7.rank
				FROM mytable7 mt7
				WHERE mt7.othervalue5 <> 'ExcludeVal'
			) mt7ranktopval
		FROM mytable1
		JOIN mytable2
			ON mytable1.key1 = mytable2.key1
			AND mytable1.var1 = 'example'
		-- This table join is necessary
		FULL JOIN mytable3
			ON mytable2.key2 = mytable3.key1
		LEFT JOIN mytable4
			ON mytable3.key3 = mytable4.key1
			AND 
			( 
				mytable2.key1 = mytable4.key2
				OR mytable1.key2 = mytable4.key3
				AND
				(
					mytable1.key2 <> mytable4.key2
				)
			)
			AND mytable1.key1 NOT IN mytable4.key2
		RIGHT JOIN mytable5
			ON mytable1.key1 = mytable5.key1
		
		UNION ALL  -- Introduce internal degree

		SELECT
			mytable3.*,
			mt4.*
		FROM mytable3
		JOIN mytable4 mt4
			ON mytable3.key3 = mt4.key1
		JOIN (  -- Subquery calculates group sum from most recent date
			SELECT groupid1, MAX(field1), SUM(field2) FROM mytable6 WHERE foobar = 'example2' 
			GROUP BY groupid1
		) "groupsum"
			ON mt4.key1 = groupsum.groupid1
		JOIN cte3
			ON mytable3.key1 = cte3.key1
		JOIN cte2
			ON LEFT(mytable4.key1, 3) LIKE '%' + cte2.myvar1 + '%'
		FULL JOIN cte4
			ON ('/mystring/' || mytable4.key1) = cte4.key1
			AND (mytable3.string1 || mytable.key1) = cte4.key1
		LEFT JOIN cte5
			ON mytable4.key2 = cte5.key2
			AND cte5.unnamedvar1 = "filtervalue"
			AND cte5.datevar1 BETWEEN mytable4.date1 AND mytable4.date2
			AND DATEADD(day, 7, cte5.datevar1) BETWEEN mytable4.date1 AND mytable4.date2
			AND cte5.datevar2 = @mydate1
		WHERE 
			mytable3.field5 = "bar4"
			AND mytable4.date1 BETWEEN cte5.datevar2 AND '2100-01-01'
			AND 
			(
				SELECT TOP 1 mt3.field4 
				FROM mytable3 mt3 
				JOIN mytable4 mt4 
					ON mt3.field1 = mt4.field1 
				WHERE mt4.field2 = 'Example'
			) = mytable4.date1
		ORDER BY mytable1.key1 DESC;  -- Order by request of end users
		
		END

		/*
		-- Trailing comment with indentation formatting because?
		" foo ' example ( bar)
		*/
	"""
