# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2015, Cédric Krier
# Copyright (c) 2013-2014, Nicolas Évrard
# Copyright (c) 2011-2015, B2CK
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division

__version__ = '0.5'
__all__ = ['Flavor', 'Table', 'Values', 'Literal', 'Column', 'Join',
    'Asc', 'Desc']

import string
import warnings
from threading import local, currentThread
from collections import defaultdict


def alias(i, letters=string.ascii_lowercase):
    '''
    Generate a unique alias based on integer

    >>> [alias(n) for n in range(6)]
    ['a', 'b', 'c', 'd', 'e', 'f']
    >>> [alias(n) for n in range(26, 30)]
    ['ba', 'bb', 'bc', 'bd']
    >>> [alias(26**n) for n in range(5)]
    ['b', 'ba', 'baa', 'baaa', 'baaaa']
    '''
    s = ''
    length = len(letters)
    while True:
        r = i % length
        s = letters[r] + s
        i //= length
        if i == 0:
            break
    return s


class Flavor(object):
    '''
    Contains the flavor of SQL

    Contains:
        max_limit - limit to use if there is no limit but an offset
        paramstyle - state the type of parameter marker formatting
        ilike - support ilike extension
        function_mapping - dictionary with Function to replace
    '''

    def __init__(self, max_limit=None, paramstyle='format', ilike=False,
            function_mapping=None):
        self.max_limit = max_limit
        self.paramstyle = paramstyle
        self.ilike = ilike
        self.function_mapping = function_mapping or {}

    @property
    def param(self):
        if self.paramstyle == 'format':
            return '%s'
        elif self.paramstyle == 'qmark':
            return '?'

    @staticmethod
    def set(flavor):
        '''Set this thread's flavor to flavor.'''
        currentThread().__sql_flavor__ = flavor

    @staticmethod
    def get():
        '''
        Return this thread's flavor.

        If this thread does not yet have a flavor, returns a new flavor and
        sets this thread's flavor.
        '''
        try:
            return currentThread().__sql_flavor__
        except AttributeError:
            flavor = Flavor()
            currentThread().__sql_flavor__ = flavor
            return flavor


class AliasManager(object):
    '''
    Context Manager for unique alias generation
    '''
    __slots__ = ()

    local = local()
    local.alias = None
    local.nested = 0
    local.exclude = None

    def __init__(self, exclude=None):
        if exclude:
            if self.local.exclude is None:
                self.local.exclude = []
            self.local.exclude.extend(exclude)

    @classmethod
    def __enter__(cls):
        if getattr(cls.local, 'alias', None) is None:
            cls.local.alias = defaultdict(cls.alias_factory)
            cls.local.nested = 0
        if getattr(cls.local, 'exclude', None) is None:
            cls.local.exclude = []
        cls.local.nested += 1

    @classmethod
    def __exit__(cls, type, value, traceback):
        cls.local.nested -= 1
        if not cls.local.nested:
            cls.local.alias = None
            cls.local.exclude = None

    @classmethod
    def get(cls, from_):
        if getattr(cls.local, 'alias', None) is None:
            return ''
        if from_ in cls.local.exclude:
            return ''
        return cls.local.alias[id(from_)]

    @classmethod
    def set(cls, from_, alias):
        assert cls.local.alias.get(from_) is None
        cls.local.alias[id(from_)] = alias

    @classmethod
    def alias_factory(cls):
        i = len(cls.local.alias)
        return alias(i)


class Query(object):
    __slots__ = ()

    @property
    def params(self):
        return ()

    def __iter__(self):
        yield str(self)
        yield self.params

    def __or__(self, other):
        return Union(self, other)

    def __and__(self, other):
        return Intersect(self, other)

    def __sub__(self, other):
        return Except(self, other)


class WithQuery(Query):
    __slots__ = ('_with',)

    def __init__(self, **kwargs):
        self._with = None
        self.with_ = kwargs.pop('with_', None)
        super(Query, self).__init__(**kwargs)

    @property
    def with_(self):
        return self._with

    @with_.setter
    def with_(self, value):
        if value is not None:
            if isinstance(value, With):
                value = [value]
            assert all(isinstance(w, With) for w in value)
        self._with = value

    def _with_str(self):
        if not self.with_:
            return ''
        recursive = (' RECURSIVE' if any(w.recursive for w in self.with_)
            else '')
        with_ = ('WITH%s ' % recursive
            + ', '.join(w.statement() for w in self.with_)
            + ' ')
        return with_

    def _with_params(self):
        if not self.with_:
            return ()
        params = []
        for w in self.with_:
            params.extend(w.statement_params())
        return tuple(params)


class FromItem(object):
    __slots__ = ()

    @property
    def alias(self):
        return AliasManager.get(self)

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError
        return Column(self, name)

    def __add__(self, other):
        assert isinstance(other, FromItem)
        return From((self, other))

    def select(self, *args, **kwargs):
        return From((self,)).select(*args, **kwargs)

    def join(self, right, type_='INNER', condition=None):
        return Join(self, right, type_=type_, condition=condition)


class With(FromItem):
    __slots__ = ('columns', 'query', 'recursive')

    def __init__(self, *columns, **kwargs):
        self.recursive = kwargs.pop('recursive', False)
        self.columns = columns
        self.query = kwargs.pop('query', None)
        super(With, self).__init__(**kwargs)

    def statement(self):
        columns = ('(%s)' % ', '.join('"%s"' % c for c in self.columns)
            if self.columns else '')
        return '%s%s AS (%s)' % (self.alias, columns, self.query)

    def statement_params(self):
        return self.query.params

    def __str__(self):
        return self.alias

    @property
    def params(self):
        return tuple()


class SelectQuery(WithQuery):
    __slots__ = ('_order_by', '_limit', '_offset')

    def __init__(self, *args, **kwargs):
        self._order_by = None
        self._limit = None
        self._offset = None
        self.order_by = kwargs.pop('order_by', None)
        self.limit = kwargs.pop('limit', None)
        self.offset = kwargs.pop('offset', None)
        super(SelectQuery, self).__init__(*args, **kwargs)

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, value):
        if value is not None:
            if isinstance(value, Expression):
                value = [value]
            assert all(isinstance(col, Expression) for col in value)
        self._order_by = value

    @property
    def _order_by_str(self):
        order_by = ''
        if self.order_by:
            order_by = ' ORDER BY ' + ', '.join(map(str, self.order_by))
        return order_by

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, value):
        if value is not None:
            assert isinstance(value, (int, long))
        self._limit = value

    @property
    def _limit_str(self):
        limit = ''
        if self.limit is not None:
            limit = ' LIMIT %s' % self.limit
        elif self.offset:
            max_limit = Flavor.get().max_limit
            if max_limit:
                limit = ' LIMIT %s' % max_limit
        return limit

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        if value is not None:
            assert isinstance(value, (int, long))
        self._offset = value

    @property
    def _offset_str(self):
        offset = ''
        if self.offset:
            offset = ' OFFSET %s' % self.offset
        return offset


class Select(FromItem, SelectQuery):
    __slots__ = ('_columns', '_where', '_group_by', '_having', '_for_',
        'from_')

    def __init__(self, columns, from_=None, where=None, group_by=None,
            having=None, for_=None, **kwargs):
        self._columns = None
        self._where = None
        self._group_by = None
        self._having = None
        self._for_ = None
        super(Select, self).__init__(**kwargs)
        # TODO ALL|DISTINCT
        self.columns = columns
        self.from_ = from_
        self.where = where
        self.group_by = group_by
        self.having = having
        self.for_ = for_

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        assert all(isinstance(col, Expression) for col in value)
        self._columns = tuple(value)

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    @property
    def group_by(self):
        return self._group_by

    @group_by.setter
    def group_by(self, value):
        if value is not None:
            if isinstance(value, Expression):
                value = [value]
            assert all(isinstance(col, Expression) for col in value)
        self._group_by = value

    @property
    def having(self):
        return self._having

    @having.setter
    def having(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._having = value

    @property
    def for_(self):
        return self._for_

    @for_.setter
    def for_(self, value):
        if value is not None:
            if isinstance(value, For):
                value = [value]
            assert all(isinstance(f, For) for f in value)
        self._for_ = value

    @staticmethod
    def _format_column(column):
        if isinstance(column, As):
            return '%s AS %s' % (column.expression, column)
        else:
            return str(column)

    def __str__(self):
        with AliasManager():
            from_ = str(self.from_)
            if self.columns:
                columns = ', '.join(map(self._format_column, self.columns))
            else:
                columns = '*'
            where = ''
            if self.where:
                where = ' WHERE ' + str(self.where)
            group_by = ''
            if self.group_by:
                group_by = ' GROUP BY ' + ', '.join(map(str, self.group_by))
            having = ''
            if self.having:
                having = ' HAVING ' + str(self.having)
            for_ = ''
            if self.for_ is not None:
                for_ = ' ' + ' '.join(map(str, self.for_))
            return (self._with_str()
                + 'SELECT %s FROM %s' % (columns, from_)
                + where + group_by + having + self._order_by_str
                + self._limit_str + self._offset_str + for_)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        for column in self.columns:
            if isinstance(column, As):
                p.extend(column.expression.params)
            p.extend(column.params)
        p.extend(self.from_.params)
        if self.where:
            p.extend(self.where.params)
        if self.group_by:
            for expression in self.group_by:
                p.extend(expression.params)
        if self.having:
            p.extend(self.having.params)
        if self.order_by:
            for expression in self.order_by:
                p.extend(expression.params)
        return tuple(p)


class Insert(WithQuery):
    __slots__ = ('_table', '_columns', '_values', '_returning')

    def __init__(self, table, columns=None, values=None, returning=None,
            **kwargs):
        self._table = None
        self._columns = None
        self._values = None
        self._returning = None
        self.table = table
        self.columns = columns
        self.values = values
        self.returning = returning
        super(Insert, self).__init__(**kwargs)

    @property
    def table(self):
        return self._table

    @table.setter
    def table(self, value):
        assert isinstance(value, Table)
        self._table = value

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        if value is not None:
            assert all(isinstance(col, Column) for col in value)
            assert all(col.table == self.table for col in value)
        self._columns = value

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        if value is not None:
            assert isinstance(value, (list, Select))
        if isinstance(value, list):
            value = Values(value)
        self._values = value

    @property
    def returning(self):
        return self._returning

    @returning.setter
    def returning(self, value):
        if value is not None:
            assert isinstance(value, list)
        self._returning = value

    @staticmethod
    def _format(value, param=None):
        if param is None:
            param = Flavor.get().param
        if isinstance(value, Expression):
            return str(value)
        elif isinstance(value, Select):
            return '(%s)' % value
        else:
            return param

    def __str__(self):
        columns = ''
        if self.columns:
            assert all(col.table == self.table for col in self.columns)
            columns = ' (' + ', '.join(map(str, self.columns)) + ')'
        if isinstance(self.values, Query):
            values = ' %s' % str(self.values)
            # TODO manage DEFAULT
        elif self.values is None:
            values = ' DEFAULT VALUES'
        returning = ''
        if self.returning:
            returning = ' RETURNING ' + ', '.join(map(str, self.returning))
        with AliasManager():
            return (self._with_str()
                + 'INSERT INTO %s' % self.table + columns
                + values + returning)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        if isinstance(self.values, Query):
            p.extend(self.values.params)
        if self.returning:
            for exp in self.returning:
                p.extend(exp.params)
        return tuple(p)


class Update(Insert):
    __slots__ = ('_where', '_values', 'from_')

    def __init__(self, table, columns, values, from_=None, where=None,
            returning=None, **kwargs):
        super(Update, self).__init__(table, columns=columns, values=values,
            returning=returning, **kwargs)
        self._where = None
        self.from_ = From(from_) if from_ else None
        self.where = where

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        if isinstance(value, Select):
            value = [value]
        assert isinstance(value, list)
        self._values = value

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    def __str__(self):
        assert all(col.table == self.table for col in self.columns)
        # Get columns without alias
        columns = map(str, self.columns)

        with AliasManager():
            from_ = ''
            if self.from_:
                table = From([self.table])
                from_ = ' FROM %s' % str(self.from_)
            else:
                table = self.table
                AliasManager.set(table, str(table)[1:-1])
            values = ', '.join('%s = %s' % (c, self._format(v))
                for c, v in zip(columns, self.values))
            where = ''
            if self.where:
                where = ' WHERE ' + str(self.where)
            returning = ''
            if self.returning:
                returning = ' RETURNING ' + ', '.join(map(str, self.returning))
            return (self._with_str()
                + 'UPDATE %s SET ' % table + values + from_
                + where + returning)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        for value in self.values:
            if isinstance(value, (Expression, Select)):
                p.extend(value.params)
            else:
                p.append(value)
        if self.from_:
            p.extend(self.from_.params)
        if self.where:
            p.extend(self.where.params)
        if self.returning:
            for exp in self.returning:
                p.extend(exp.params)
        return tuple(p)


class Delete(WithQuery):
    __slots__ = ('_table', '_where', '_returning', 'only')

    def __init__(self, table, only=False, using=None, where=None,
            returning=None, **kwargs):
        self._table = None
        self._where = None
        self._returning = None
        self.table = table
        self.only = only
        # TODO using (not standard)
        self.where = where
        self.returning = returning
        super(Delete, self).__init__(**kwargs)

    @property
    def table(self):
        return self._table

    @table.setter
    def table(self, value):
        assert isinstance(value, Table)
        self._table = value

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._where = value

    @property
    def returning(self):
        return self._returning

    @returning.setter
    def returning(self, value):
        if value is not None:
            assert isinstance(value, list)
        self._returning = value

    def __str__(self):
        with AliasManager(exclude=[self.table]):
            only = ' ONLY' if self.only else ''
            where = ''
            if self.where:
                where = ' WHERE ' + str(self.where)
            returning = ''
            if self.returning:
                returning = ' RETURNING ' + ', '.join(map(str, self.returning))
            return (self._with_str()
                + 'DELETE FROM%s %s' % (only, self.table)
                + where + returning)

    @property
    def params(self):
        p = []
        p.extend(self._with_params())
        if self.where:
            p.extend(self.where.params)
        if self.returning:
            for exp in self.returning:
                p.extend(exp.params)
        return tuple(p)


class CombiningQuery(FromItem, SelectQuery):
    __slots__ = ('queries', 'all_')
    _operator = ''

    def __init__(self, *queries, **kwargs):
        assert all(isinstance(q, Query) for q in queries)
        self.queries = queries
        self.all_ = kwargs.pop('all_', False)
        super(CombiningQuery, self).__init__(**kwargs)

    def __str__(self):
        with AliasManager():
            operator = ' %s %s' % (self._operator, 'ALL ' if self.all_ else '')
            return (operator.join(map(str, self.queries)) + self._order_by_str
                + self._limit_str + self._offset_str)

    @property
    def params(self):
        p = []
        for q in self.queries:
            p.extend(q.params)
        if self.order_by:
            for expression in self.order_by:
                p.extend(expression.params)
        return tuple(p)


class Union(CombiningQuery):
    __slots__ = ()
    _operator = 'UNION'


class Intersect(CombiningQuery):
    __slots__ = ()
    _operator = 'INTERSECT'


class Interesect(Intersect):
    def __init__(self, *args, **kwargs):
        warnings.warn('Interesect query is deprecated, use Intersect',
            DeprecationWarning, stacklevel=2)
        super(Interesect, self).__init__(*args, **kwargs)


class Except(CombiningQuery):
    __slots__ = ()
    _operator = 'EXCEPT'


class Table(FromItem):
    __slots__ = ('_name', '_schema', '_database')

    def __init__(self, name, schema=None, database=None):
        super(Table, self).__init__()
        self._name = name
        self._schema = schema
        self._database = database

    def __str__(self):
        if self._database:
            return '"%s"."%s"."%s"' % (
                self._database, self._schema, self._name)
        elif self._schema:
            return '"%s"."%s"' % (self._schema, self._name)
        else:
            return '"%s"' % self._name

    @property
    def params(self):
        return ()

    def insert(self, columns=None, values=None, returning=None, with_=None):
        return Insert(self, columns=columns, values=values,
            returning=returning, with_=with_)

    def update(self, columns, values, from_=None, where=None, returning=None,
            with_=None):
        return Update(self, columns=columns, values=values, from_=from_,
            where=where, returning=returning, with_=with_)

    def delete(self, only=False, using=None, where=None, returning=None,
            with_=None):
        return Delete(self, only=only, using=using, where=where,
            returning=returning, with_=with_)


class Join(FromItem):
    __slots__ = ('_left', '_right', '_condition', '_type_')

    def __init__(self, left, right, type_='INNER', condition=None):
        super(Join, self).__init__()
        self._left, self._right = None, None
        self._condition = None
        self._type_ = None
        self.left = left
        self.right = right
        self.condition = condition
        self.type_ = type_

    @property
    def left(self):
        return self._left

    @left.setter
    def left(self, value):
        assert isinstance(value, FromItem)
        self._left = value

    @property
    def right(self):
        return self._right

    @right.setter
    def right(self, value):
        assert isinstance(value, FromItem)
        self._right = value

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, value):
        from sql.operators import And, Or
        if value is not None:
            assert isinstance(value, (Expression, And, Or))
        self._condition = value

    @property
    def type_(self):
        return self._type_

    @type_.setter
    def type_(self, value):
        value = value.upper()
        assert value in ('INNER', 'LEFT', 'LEFT OUTER',
            'RIGHT', 'RIGHT OUTER', 'FULL', 'FULL OUTER', 'CROSS')
        self._type_ = value

    def __str__(self):
        join = '%s %s JOIN %s' % (From([self.left]), self.type_,
            From([self.right]))
        if self.condition:
            condition = ' ON %s' % self.condition
        else:
            condition = ''
        return join + condition

    @property
    def params(self):
        p = []
        for item in (self.left, self.right):
            if hasattr(item, 'params'):
                p.extend(item.params)
        if hasattr(self.condition, 'params'):
            p.extend(self.condition.params)
        return tuple(p)

    @property
    def alias(self):
        raise AttributeError

    def __getattr__(self, name):
        raise AttributeError

    def select(self, *args, **kwargs):
        return super(Join, self).select(*args, **kwargs)


class From(list):
    __slots__ = ()

    def select(self, *args, **kwargs):
        return Select(args, from_=self, **kwargs)

    def __str__(self):
        def format(from_):
            template = '%s'
            if isinstance(from_, Query):
                template = '(%s)'
            alias = getattr(from_, 'alias', None)
            # TODO column_alias
            columns_definitions = getattr(from_, 'columns_definitions',
                None)
            # XXX find a better test for __getattr__ which returns Column
            if (alias and columns_definitions
                    and not isinstance(columns_definitions, Column)):
                return (template + ' AS "%s" (%s)') % (from_, alias,
                    columns_definitions)
            elif alias:
                return (template + ' AS "%s"') % (from_, alias)
            else:
                return template % from_
        return ', '.join(map(format, self))

    @property
    def params(self):
        p = []
        for from_ in self:
            p.extend(from_.params)
        return tuple(p)

    def __add__(self, other):
        assert isinstance(other, FromItem)
        assert not isinstance(other, CombiningQuery)
        return From(super(From, self).__add__([other]))


class Values(list, Query, FromItem):
    __slots__ = ()

    # TODO order, fetch

    def __str__(self):
        param = Flavor.get().param

        def format_(value):
            if isinstance(value, Expression):
                return str(value)
            else:
                return param
        return 'VALUES ' + ', '.join(
            '(%s)' % ', '.join(map(format_, v))
            for v in self)

    @property
    def params(self):
        p = []
        for values in self:
            for value in values:
                if isinstance(value, Expression):
                    p.extend(value.params)
                else:
                    p.append(value)
        return tuple(p)


class Expression(object):
    __slots__ = ()

    def __str__(self):
        raise NotImplementedError

    @property
    def params(self):
        raise NotImplementedError

    def __and__(self, other):
        from sql.operators import And
        return And((self, other))

    def __or__(self, other):
        from sql.operators import Or
        return Or((self, other))

    def __invert__(self):
        from sql.operators import Not
        return Not(self)

    def __add__(self, other):
        from sql.operators import Add
        return Add(self, other)

    def __sub__(self, other):
        from sql.operators import Sub
        return Sub(self, other)

    def __mul__(self, other):
        from sql.operators import Mul
        return Mul(self, other)

    def __div__(self, other):
        from sql.operators import Div
        return Div(self, other)

    __truediv__ = __div__

    def __floordiv__(self, other):
        from sql.functions import Div
        return Div(self, other)

    def __mod__(self, other):
        from sql.operators import Mod
        return Mod(self, other)

    def __pow__(self, other):
        from sql.operators import Pow
        return Pow(self, other)

    def __neg__(self):
        from sql.operators import Neg
        return Neg(self)

    def __pos__(self):
        from sql.operators import Pos
        return Pos(self)

    def __abs__(self):
        from sql.operators import Abs
        return Abs(self)

    def __lshift__(self, other):
        from sql.operators import LShift
        return LShift(self, other)

    def __rshift__(self, other):
        from sql.operators import RShift
        return RShift(self, other)

    def __lt__(self, other):
        from sql.operators import Less
        return Less(self, other)

    def __le__(self, other):
        from sql.operators import LessEqual
        return LessEqual(self, other)

    def __eq__(self, other):
        from sql.operators import Equal
        return Equal(self, other)

    # When overriding __eq__, __hash__ is implicitly set to None
    __hash__ = object.__hash__

    def __ne__(self, other):
        from sql.operators import NotEqual
        return NotEqual(self, other)

    def __gt__(self, other):
        from sql.operators import Greater
        return Greater(self, other)

    def __ge__(self, other):
        from sql.operators import GreaterEqual
        return GreaterEqual(self, other)

    def in_(self, values):
        from sql.operators import In
        return In(self, values)

    def like(self, test):
        from sql.operators import Like
        return Like(self, test)

    def ilike(self, test):
        from sql.operators import ILike
        return ILike(self, test)

    def as_(self, output_name):
        return As(self, output_name)

    def cast(self, typename):
        return Cast(self, typename)

    @property
    def asc(self):
        return Asc(self)

    @property
    def desc(self):
        return Desc(self)


class Literal(Expression):
    __slots__ = ('_value')

    def __init__(self, value):
        super(Literal, self).__init__()
        self._value = value

    @property
    def value(self):
        return self._value

    def __str__(self):
        return Flavor.get().param

    @property
    def params(self):
        return (self._value,)

Null = None


class Column(Expression):
    __slots__ = ('_from', '_name')

    def __init__(self, from_, name):
        super(Column, self).__init__()
        self._from = from_
        self._name = name

    @property
    def table(self):
        return self._from

    @property
    def name(self):
        return self._name

    def __str__(self):
        if self._name == '*':
            t = '%s'
        else:
            t = '"%s"'
        alias = self._from.alias
        if alias:
            t = '"%s".' + t
            return t % (alias, self._name)
        else:
            return t % self._name

    @property
    def params(self):
        return ()


class As(Expression):
    __slots__ = ('expression', 'output_name')

    def __init__(self, expression, output_name):
        super(As, self).__init__()
        self.expression = expression
        self.output_name = output_name

    def __str__(self):
        return '"%s"' % self.output_name

    @property
    def params(self):
        return ()


class Cast(Expression):
    __slots__ = ('expression', 'typename')

    def __init__(self, expression, typename):
        super(Expression, self).__init__()
        self.expression = expression
        self.typename = typename

    def __str__(self):
        if isinstance(self.expression, Expression):
            value = self.expression
        else:
            value = Flavor.get().param
        return 'CAST(%s AS %s)' % (value, self.typename)

    @property
    def params(self):
        if isinstance(self.expression, Expression):
            return self.expression.params
        else:
            return (self.expression,)


class Order(Expression):
    __slots__ = ('expression')
    _sql = ''

    def __init__(self, expression):
        super(Order, self).__init__()
        self.expression = expression
        # TODO USING

    def __str__(self):
        return '%s %s' % (self.expression, self._sql)

    @property
    def params(self):
        return self.expression.params


class Asc(Order):
    __slots__ = ()
    _sql = 'ASC'


class Desc(Order):
    __slots__ = ()
    _sql = 'DESC'


class For(object):
    __slots__ = ('_tables', '_type_', 'nowait')

    def __init__(self, type_, *tables, **kwargs):
        self._tables = None
        self._type_ = None
        self.tables = list(tables)
        self.type_ = type_
        self.nowait = kwargs.get('nowait')

    @property
    def tables(self):
        return self._tables

    @tables.setter
    def tables(self, value):
        if not isinstance(value, list):
            value = [value]
        all(isinstance(table, Table) for table in value)
        self._tables = value

    @property
    def type_(self):
        return self._type_

    @type_.setter
    def type_(self, value):
        value = value.upper()
        assert value in ('UPDATE', 'SHARE')
        self._type_ = value

    def __str__(self):
        tables = ''
        if self.tables:
            tables = ' OF ' + ', '.join(map(str, self.tables))
        nowait = ''
        if self.nowait:
            nowait = ' NOWAIT'
        return ('FOR %s' % self.type_) + tables + nowait
