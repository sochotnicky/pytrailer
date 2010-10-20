import json
import urllib2 as urllib
import re
from HTMLParser import HTMLParser

def getMoviesFromJSON(jsonURL):
    """Main function for this library

    Returns list of Movie classes from apple.com/trailers json URL
    such as: http://trailers.apple.com/trailers/home/feeds/just_added.json

    The Movie classes use lazy loading mechanisms so that data not
    directly available from JSON are loaded on demand. Currently these
    lazy loaded parts are:
     * poster
     * trailerLinks
     * description

    Be warned that accessing these fields can take long time due to
    network access. Therefore do the loading in thread separate from
    UI thread or your users will notice.

    There are optional fields that may or may not be present in every
    Movie instance. These include:
     * actors (list)
     * directors (list)
     * rating (string)
     * genre (string)
     * studio (string)
     * releasedate (sring)
    Please take care when trying to access these fields as they may
    not exist.
    """
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
    """Main class representing all trailers for single Movie

    Most fields should be self-descriptive
    """

    def __init__(self):
        self.title = None
        # URL of poster for the movie
        self.posterURL = None
        # base URL of movie such as "/trailers/magnolia/nightcatchesus/"
        self.baseURL = None
        # trailers as present in JSON URL (not used)
        self.trailers = []
        self._posterData = None
        self._trailerLinks = None
        self._description = None

    @property
    def trailerLinks(self):
        """Returns dictionary with trailer names as keys and list of
        trailer urls as values. Each trailer can have more links due
        to different qualities.

        Example:
        {'Trailer':['url1','url2'],'Featurette':['url1','url2']}
        """
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
        """Returns poster data itself (as in JPEG/GIF/PNG file)"""
        if self._posterData:
            return self._posterData

        response = urllib.urlopen(self.posterURL)
        self._posterData = response.read()
        return self._posterData

    @property
    def description(self):
        """Returns description text as provided by the studio"""
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
    """Class for parsing data from web.inc html files that exist for
    every Movie

    Each movie has associated web.inc file that contains pieces of
    html containing trailer names (as in "Trailer", "Featurette"
    etc) and links to trailers themselves.
    """

    H3 = 1
    URLS = 2

    def getTrailers(self, data):
        """Returns dictionary with trailer names as keys and list of
        trailer urls as values. Each trailer can have more links due
        to different qualities.

        data - HTML page containing Trailer names/links

        Example:
        {'Trailer':['url1','url2'],'Featurette':['url1','url2']}
        """
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

