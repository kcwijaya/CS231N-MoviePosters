import http.client
import json
from io import BytesIO
from PIL import Image
import progressbar  # pip install progressbar2
import numpy as np
import requests
import time

# Returns a list of named genres (i.e. ['Action', 'Adventure', ... ]), and
# a map from genre_ids to the index of the genre in |genre_list|.
def get_genres(api_key):
	connection = http.client.HTTPSConnection("api.themoviedb.org")
	connection.request("GET", "/3/genre/movie/list?language=en-US&api_key={0}".format(api_key))

	genres = {}
	for elem in json.loads(connection.getresponse().read())['genres']:
		genres[elem['id']] = elem['name']
	
	genre_list = sorted(genres.values())
	genre_map = { key : genre_list.index(value) for key, value in genres.items() }
	
	return genre_list, genre_map

# Builds the request string for the movie database API.
def build_request(api_key, params, page=None):
	request = '/3/discover/movie?'
	request += '&'.join(['{0}={1}'.format(key, value) for key, value in params.items()])
	if page is not None:
		request += '&page={0}'.format(page)
	request += '&api_key={0}'.format(api_key)
	return request

# Returns a JSON object from The Movie Database API when making a
# request with the given |params|.
def make_request(api_key, params, page=None):
	connection = http.client.HTTPSConnection("api.themoviedb.org")
	connection.request("GET", build_request(api_key, params, page))
	return json.loads(connection.getresponse().read())

# Returns the shape associated with a given poster size (used by the API).
def get_poster_shape(size):
	size_to_shape = {
		'w92' : (138, 92, 3),
		'w154' : (231, 154, 3),
		'w185' : (278, 185, 3),
		'w342' : (513, 342, 3)
	}
	return size_to_shape[size]

# Given the |poster_path| returns a 3D numpy array which stores the image of
# of the specified |size|. If the image is invalid (rare), return None.
def get_poster(poster_path, size='w185'):
	if poster_path is None: return None
	
	poster_url = 'https://image.tmdb.org/t/p/{0}'.format(size) + poster_path
	response = requests.get(poster_url)
	img = Image.open(BytesIO(response.content))

	try:
		image = np.array(img.getdata(), dtype=np.uint8).reshape(img.size[1], img.size[0], 3)
	except ValueError:
		return None

	required_shape = get_poster_shape(size)
	if image.shape[0] < required_shape[0]:
		padding = required_shape[0] - image.shape[0]
		image = np.pad(image, [(0, padding), (0, 0), (0, 0)], mode='constant')
	if image.shape[0] > required_shape[0]:
		image = image[0:required_shape[0], :, :]

	assert image.shape == required_shape
	return image


# Generates a binary vector where 1s represent that the movie is classified
# as that genre. *NOTE: movies can belong to any number of genres*
def to_genre_vector(genre_map, genre_ids):
	vector = np.zeros(len(genre_map), dtype=np.uint8)
	for genre_id in genre_ids:
		vector[genre_map[genre_id]] = 1
	return vector

# Download movie data from The Movie Database API. 
def download_movie_data(api_key, params, start_page=1, max_pages=1000):
	genre_list, genre_map = get_genres(api_key)

	movie_posters, movie_genres = [], []

	total_pages = make_request(api_key, params)['total_pages']
	total_pages = min(total_pages, max_pages)
	pbar = progressbar.ProgressBar(max_value=total_pages)
	
	for page in range(start_page, total_pages+1):
		results = make_request(api_key, params, page)
		for movie in results['results']:
			poster = get_poster(movie['poster_path'])
			if poster is None:
				continue
			genres = to_genre_vector(genre_map, movie['genre_ids'])
			
			movie_posters.append(poster)
			movie_genres.append(genres)

		if page % 100 == 0 or page == total_pages:
			np.save('movie_data/posters_{0}.npy'.format(1000+page), movie_posters, allow_pickle=False)
			np.save('movie_data/genres_{0}.npy'.format(1000+page), movie_genres, allow_pickle=False)
			movie_posters.clear()
			movie_genres.clear()

		pbar.update(page)


def main():
	API_KEY = '1463092fc575fb3cac262efb34f94dde'
	PARAMS = {
		'language' : 'en-US',
		'vote_count.gte' : 10,
		'primary_release_date.lte' : '2017-12-31',
		'sort_by' : 'vote_average.desc',
		'include_video' : False,
		'include_adult' : False,
		'vote_average.lte' : 5.7,
	}
	
	print(get_genres(API_KEY))
	exit()

	print('Downloading Movie Posters/Genres...')
	download_movie_data(API_KEY, PARAMS)
	print('Done.')

if __name__ == '__main__':
	main()
