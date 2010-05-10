import json
import urllib2 as urllib
import sys
import re
import multiprocessing
import os

def getMoviesFromJSON(jsonURL):
    response = urllib.urlopen(jsonURL)
    jsonData = response.read()
    objects = json.loads(jsonData)
    optionalInfo = ['actors','directors','rating','genre','studio','releasedate']
    movies = []
    for obj in objects:
        movie = Movie()
        movie.title = obj['title']
        movie.baseURL = obj['location']
        movie.posterURL = obj['poster']
        movie.trailers = obj['trailers']

        for i in optionalInfo:
            if obj.has_key(i):
                setattr(movie, i, obj[i])

        movies.append(movie)

    return movies



class Movie:

    def __init__(self):
        self.title = None
        self.releasedate = None
        self.studio = None
        self.posterURL = None
        self.baseURL = None
        self.trailers = []
        self.genre = None
        self.rating = None
        self.actors = []
        self.directors = []
        self.cached = False
        self._posterData = None
        self._trailerLinks = None
        self._description = None

    @property
    def trailerLinks(self):
        trailerHTMLURL = "http://trailers.apple.com%sincludes/playlists/web.inc" % \
            (self.baseURL)
        if self._trailerLinks:
            return self._trailerLinks

        response = urllib.urlopen(trailerHTMLURL)

        trailersHTML = response.read()
        trailerURLS = re.findall('"http:.*?"',trailersHTML)
        self._trailerLinks = []
        for url in trailerURLS:
            if url.find('.mov') != -1:
                url=url[1:-1]
                subPos = url.rfind('_')
                if subPos == url.rfind('_h.'):
                    url = re.sub('(.*)/([^/]*)_h.([^/]*)',r'\1/\2_h\3', url)
                else:
                    url = re.sub('(.*)/([^/]*)_([^/]*)',r'\1/\2_h\3', url)

                url = re.sub('_hh','_h', url)
                self._trailerLinks.append(url)
        return self._trailerLinks

    @property
    def poster(self):
        if self._posterData:
            return self._posterData

        response = urllib.urlopen(self.posterURL)
        self._posterData = response.read()
        return self._posterData

    @property
    def description(self):
        if self._description:
            return self._description

        trailerURL= "http://trailers.apple.com%s" % self.baseURL
        response = urllib.urlopen(trailerURL)
        trailerHTML = response.read()
        description = re.search('<meta *name="Description" *content="(.*?)" *[/]*>'
                                ,trailerHTML)
        if description:
            description = description.group(1)
            self._description = description
        else:
            self._description = "None"
        return self._description
