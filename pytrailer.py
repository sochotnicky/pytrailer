import json
import urllib2 as urllib
import re
from HTMLParser import HTMLParser

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
        wip = WebIncParser()

        trailersHTML = response.read()
        self._trailerLinks = wip.getTrailers(trailersHTML)
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

class WebIncParser(HTMLParser):
    H3 = 1
    URLS = 2

    def getTrailers(self, data):
        self.trailers = {}
        self.dirtyURLS = []
        self.next_title = None
        self.pos = 0
        self.feed(data)
        self.close()
        if len(self.trailers) == 1:
            val = self.trailers[self.trailers.keys()[0]]
            if len(val) == 0:
                self.trailers[self.trailers.keys()[0]] = self.dirtyURLS
        return self.trailers

    def _add_url(self, name, url):
        if self.pos == self.URLS:
            self.trailers[name].append(url)
        else:
            self.dirtyURLS.append(url)

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'h3':
            self.pos = self.H3
        elif tag.lower() == 'a':
            for name, val in attrs:
                if name == 'href' and val.find('.mov') != -1:
                    url = val
                    subPos = url.rfind('_')
                    if subPos == url.rfind('_h.'):
                        url = re.sub('(.*)/([^/]*)_h.([^/]*mov).*',r'\1/\2_h\3', url)
                    else:
                        url = re.sub('(.*)/([^/]*)_([^/]*mov).*',r'\1/\2_h\3', url)

                    url = re.sub('_hh','_h', url)
                    url = re.sub('h640','h640w', url)
                    self._add_url(self.next_title, url)

    def handle_data(self, data):
        if self.pos == self.H3:
            if data in self.trailers.keys():
                self.handle_data("%s_1" % data)
            self.trailers[data]=[]
            self.next_title = data

    def handle_endtag(self, tag):
        if tag.lower() == 'h3':
            self.pos = self.URLS

