/* Basic ooRexx class definition, for lexer sample/testing purposes. */

mystem = .stem~new
mystem[foo] = 'bar'
say mystem[foo]

arr = .array~of('a', 'b', 'c')
do item over arr
    say item
end

point = .Point~new(3, 4)
say point~toString
say point~distanceFromOrigin

::CLASS Point
::CONSTANT Pi 3.14159265358979

::ATTRIBUTE x
::ATTRIBUTE y

::METHOD init
    expose x y
    use strict arg x, y

::METHOD toString
    expose x y
    return '(' || x || ',' || y || ')'

::METHOD distanceFromOrigin
    expose x y
    return (x * x + y * y) ** 0.5
