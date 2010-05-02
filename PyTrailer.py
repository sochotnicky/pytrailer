import sys
import pickle
import time
from multiprocessing import Process, Queue

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import amt


categories = {'Just added':'/trailers/home/feeds/just_added.json',
              'Exclusive':'/trailers/home/feeds/exclusive.json',
              'Only HD':'/trailers/home/feeds/just_hd.json',
              'Most popular':'/trailers/home/feeds/most_pop.json',
              'Search':'/trailers/home/scripts/quickfind.php?callback=searchCallback&q='}


class PyTrailerWidget(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)

        READ_AHEAD_PROC=1
        self.readAheadTaskQueue = Queue()
        self.readAheadDoneQueue = Queue()

        self.readAheadProcess = []
        for i in range(READ_AHEAD_PROC):
            p = Process(target=movieReadAhead,
                        args=(self.readAheadTaskQueue,
                              self.readAheadDoneQueue))
            p.start()
            self.readAheadProcess.append(p)

        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshMovies)
        self.refreshTimer.start()
        self.setWindowTitle("PyTrailer - Apple Trailer Downloader")

        hbox = QHBoxLayout()
        group = QButtonGroup(hbox)
        group.setExclusive(True)
        for cat in categories.keys():
            but = CategoryPushButton(cat, self, categories[cat])
            but.setCheckable(True)
            group.addButton(but)
            hbox.addWidget(but)

        group.buttonClicked.connect(self.groupChange)
        vbox = QVBoxLayout()
        vbox.addLayout(hbox)

        self.movieModel = MovieListModel(self)
        self.paintDelegate = MoviePaintDelegate(self)

        self.movieListView = QListView()
        self.movieListView.setModel(self.movieModel)
        self.loadGroup("Just added")

        self.movieListView.setItemDelegate(self.paintDelegate)

        shortcut = QShortcut(QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
                          self);
        self.connect(shortcut, SIGNAL('activated()'), SLOT('close()'))

        vbox.addWidget(self.movieListView)
        self.setLayout(vbox)


    def groupChange(self, button):
        self.loadGroup(str(button.text()))

    def loadGroup(self, groupName):
        url = "http://trailers.apple.com%s" % categories[groupName]
        managedList = amt.getMoviesFromJSON(url)
        self.movieModel.setMovies(managedList)
        while not self.readAheadTaskQueue.empty():
            self.readAheadTaskQueue.get()
            
        for i in range(len(managedList)):
            self.readAheadTaskQueue.put((i, managedList[i]))

    def closeEvent(self, closeEvent):
        for p in self.readAheadProcess:
            p.terminate()

    def refreshMovies(self):
        changed = False
        if not self.readAheadDoneQueue.empty():
            i, updatedMovie = self.readAheadDoneQueue.get_nowait()
            t0 = time.time()
            oldMovie = self.movieModel.listdata[i]
            oldMovie.poster = updatedMovie.poster
            oldMovie.trailerLinks = updatedMovie.trailerLinks
            oldMovie.cached = True
            changed = True
            print "Spent: %f" % (time.time() - t0)
        if changed:
            self.movieModel.updated()


def movieReadAhead(taskQueue, doneQueue):
    while True:
        i, movie = taskQueue.get()
        try:
            movie.poster
            movie.trailerLinks
            doneQueue.put((i, movie))
        except:
            pass


class CategoryPushButton(QPushButton):
    def __init__(self, text, parent, jsonLink):
        QPushButton.__init__(self, text, parent)
        self.jsonLink = jsonLink


class MoviePaintDelegate(QItemDelegate):
    def __init__(self, parent=None, *args):
        QItemDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        painter.save()

        # set background color
        painter.setPen(QPen(Qt.NoPen))
        if option.state & QStyle.State_Selected:
            painter.setBrush(QBrush(Qt.gray))
        else:
            painter.setBrush(QBrush(Qt.white))
        painter.drawRect(option.rect)

        # set text color
        painter.setPen(QPen(Qt.black))
        value = index.data(Qt.UserRole)
        if value.isValid():
            ba = value.toByteArray()
            m = pickle.loads(ba)
            posterImg = QImage()
            option.rect.setLeft(option.rect.left()+10)
            if m.cached == True:
                if posterImg.loadFromData(m.poster) is True :
                    posterRect = QRect(option.rect)
                    posterRect.setWidth(90)
                    posterRect.setHeight(130)
                    posterRect.setTop(posterRect.top()+20)
                    painter.drawImage(posterRect, posterImg)

                    trailerRect=QRect(option.rect)

                    trailerRect.setLeft(trailerRect.left()+ 100)
                    trailerRect.setTop(trailerRect.top() + 20)
                    trailerRect.setWidth(700)
                    trailerNames = []
                    for trailerLink in m.trailerLinks:
                        label = '%s' % trailerLink
                        trailerNames.append(label)
                        painter.drawText(trailerRect, Qt.AlignLeft, "\n".join(trailerNames))

            fn = painter.font()
            fn.setWeight(QFont.Bold)
            painter.setFont(fn)
            painter.drawText(option.rect, Qt.AlignLeft, m.title)
        else:
            painter.drawText(option.rect, Qt.AlignLeft, "Error")

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100,150)


class MovieListModel(QAbstractListModel):
    def __init__(self, parent=None, *args):
        """ movies: a list where each item is one amt.Movie
        """
        QAbstractListModel.__init__(self, parent, *args)
        
    def rowCount(self, parent=QModelIndex()):
        return len(self.listdata)

    def data(self, index, role):
        if index.isValid() and role == Qt.UserRole:
            self.listdata[index.row()].poster
            tmp = pickle.dumps(self.listdata[index.row()], 0)
            return QVariant(tmp)
        else:
            return QVariant()

    def setMovies(self, movies):
        self.listdata = movies
        
    def updated(self):
        self.emit(SIGNAL("dataChanged(1,1000)"))

app = QApplication(sys.argv)

widget = PyTrailerWidget()
widget.resize(800, 600)
widget.setWindowTitle('simple')
widget.show()
sys.exit(app.exec_())
