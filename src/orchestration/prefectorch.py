import prefect
from prefect import task, Flow, Task


@task
def read_data(x):

	return [ x, 2 ] * 2


@task
def c(x):
	print( x )
	return x + 3


@task
def d(x):
	print( sum( x ) )


class BufferedTask( Task ):

	def open(self):
		...

	...


def over(x):

	@task
	def ret(y):
		return x.map( y )

	return ret


with Flow( "Hello-Flow" ) as flow:
	x = (a()
	     .pipe( read_data ))

	d.map( x )

flow.run()
