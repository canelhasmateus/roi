

if __name__ == '__main__':


	import unittest


	class TestSolution( unittest.TestCase ):
		youtube_html = Tests.load_html( "test_youtube_1.html" )

		def test1( self ):
			author = Youtube.author( self.youtube_html )
			categories = Youtube.categories( self.youtube_html )
			comments = Youtube.comments( self.youtube_html )
			date = Youtube.date( self.youtube_html )
			duration = Youtube.duration( self.youtube_html )
			image = Youtube.image( self.youtube_html )
			neighbors = Youtube.neighbors( self.youtube_html )
			tags = Youtube.tags( self.youtube_html )
			title = Youtube.title( self.youtube_html )

			self.assertEqual( author, 'http://www.youtube.com/user/GISIGeometry' )
			self.assertEqual( categories, [ 'Science & Technology' ] )
			self.assertEqual( date, '2020-11-21' )
			self.assertEqual( duration, 1177 )
			self.assertEqual( image, 'https://i.ytimg.com/vi/B5Vw6H3oSD8/hqdefault.jpg' )
			self.assertTrue( len( [ i for i in tags ] ) == 14 )
			self.assertTrue( title.startswith( "NEW GENIUS DNS" ) )


	unittest.main()
