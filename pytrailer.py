import codecs
import json
import re
import locale
from time import mktime
try:
    import urllib2 as urllib
    urllib.request = urllib

    from HTMLParser import HTMLParser
except ImportError:
    # python3.x
    import urllib.request, urllib.error, urllib.parse
    from html.parser import HTMLParser

import dateutil.parser as dparser


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
    response = urllib.request.urlopen(jsonURL)
    jsonData = response.read().decode('utf-8')
    objects = json.loads(jsonData)
    # make it work for search urls
    if jsonURL.find('quickfind') != -1:
        objects = objects['results']
    optionalInfo = ['actors','directors','rating','genre','studio','releasedate']
    movies = []
    for obj in objects:
        movie = Movie()
        movie.title = obj['title']
        movie.baseURL = obj['location']
        movie.posterURL = obj['poster']
        # sometimes posters don't have http part
        if movie.posterURL.find('http:') == -1:
            movie.posterURL = "http://apple.com%s" % movie.posterURL
        movie.trailers = obj['trailers']

        for i in optionalInfo:
            if i in obj:
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

    def get_trailerLinks(self):
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

        response = urllib.request.urlopen(trailerHTMLURL)
        wip = WebIncParser()

        trailersHTML = response.read().decode('utf-8')
        self._trailerLinks = wip.getTrailers(trailersHTML)
        return self._trailerLinks

    def set_trailerLinks(self, val):
        self._trailerLinks = val

    trailerLinks = property(get_trailerLinks, set_trailerLinks)

    def get_poster(self):
        """Returns poster data itself (as in JPEG/GIF/PNG file)"""
        if self._posterData:
            return self._posterData

        response = urllib.request.urlopen(self.posterURL)
        self._posterData = response.read()
        return self._posterData

    def set_poster(self, val):
        self._posterData = val

    poster = property(get_poster, set_poster)

    def get_description(self):
        """Returns description text as provided by the studio"""
        if self._description:
            return self._description

        try:
            trailerURL= "http://trailers.apple.com%s" % self.baseURL
            response = urllib.request.urlopen(trailerURL)
            Reader = codecs.getreader("utf-8")
            responseReader = Reader(response)
            trailerHTML = responseReader.read()
            description = re.search('<meta *name="Description" *content="(.*?)" *[/]*>'
                                    ,trailerHTML)
            if description:
                self._description = description.group(1)
            else:
                self._description = "None"
        except:
            self._description = "Error"
        return self._description

    def set_description(self, val):
        self._description = val

    description = property(get_description, set_description)

    def get_latest_trailer_date(self):
        """Returns date (unix timestamp) of latest trailer for this movie
        """
        tsMax = 0
        for trailer in self.trailers:
            locale.setlocale(locale.LC_ALL, "C")
            pdate = dparser.parse(trailer['postdate'])
            locale.resetlocale()
            ts = mktime(pdate.timetuple())
            if ts > tsMax:
                tsMax = ts
        return tsMax


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
            val = self.trailers[list(self.trailers.keys())[0]]
            if len(val) == 0:
                self.trailers[list(self.trailers.keys())[0]] = self.dirtyURLS
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
            if data in list(self.trailers.keys()):
                self.handle_data("%s_1" % data)
            self.trailers[data]=[]
            self.next_title = data

    def handle_endtag(self, tag):
        if tag.lower() == 'h3':
            self.pos = self.URLS

