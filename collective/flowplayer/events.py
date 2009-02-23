from zope.cachedescriptors import property
from zope.interface import alsoProvides, noLongerProvides

from collective.flowplayer.interfaces import IMediaInfo, IAudio, IVideo
from collective.flowplayer.flv import FLVHeader, FLVHeaderError

from Products.ATContentTypes import interface
from Products.Archetypes.interfaces import IObjectInitializedEvent

from StringIO import StringIO

EXTENSIONS = ['.flv',
              '.mp3']

def remove_marker(object):
    changed = False
    if IAudio.providedBy(object):
        noLongerProvides(object, IAudio)
        changed = True
    if IVideo.providedBy(object):
        noLongerProvides(object, IVideo)
        changed = True
    if changed:
        object.reindexObject(idxs=['object_provides'])

class ChangeView(object):

    interface = None

    @property.Lazy
    def value(self):
        return self.content.getField('file').getRaw(self.content)

    def handleAudio(self):
        if not IAudio.providedBy(self.content):
            alsoProvides(self.content, IAudio)
            self.object.reindexObject(idxs=['object_provides'])

    def __init__(self, object, event):
        self.object = object
        # TODO: do we really need this different from object?
        self.content = content = event.object

        if not self.interface.providedBy(content):
            return

        if self.value is None:
            remove_marker(content)
            return

        ext = self.check_extension()
        if ext is None:
            remove_marker(content)
            return

        if IObjectInitializedEvent.providedBy(event):
            content.setLayout('flowplayer')

        if ext == '.mp3':
            self.handleAudio()
        elif ext == '.flv':
            self.handleVideo()

    def handleVideo(self):
        if not IVideo.providedBy(self.content):
            alsoProvides(self.content, IVideo)
            self.object.reindexObject(idxs=['object_provides'])

class ChangeFileView(ChangeView):

    interface = interface.IATFile

    def check_extension(self):
        filename = self.value.filename.lower()
        for ext in EXTENSIONS:
            if filename.endswith(ext):
                return ext
        return None

    def handleVideo(self):
        file_object = self.value
        try:
            # For blobs
            file_handle = file_object.getIterator()
        except AttributeError:
            file_handle = StringIO(str(file_object.data))

        file_handle.seek(0)
        flvparser = FLVHeader()
        try:
            flvparser.analyse(file_handle.read(1024))
        except FLVHeaderError:
            remove_marker(self.content)
            return

        super(ChangeFileView, self).handleVideo()

        width = flvparser.getWidth()
        height = flvparser.getHeight()

        if height and width:
            info = IMediaInfo(self.content)
            info.height = height
            info.width = width

class ChangeLinkView(ChangeView):

    interface = interface.IATLink

    @property.Lazy
    def value(self):
        return self.content.getField('remoteUrl').getRaw(self.content)

    def check_extension(self):
        filename = self.value.lower()
        for ext in EXTENSIONS:
            if filename.endswith(ext):
                return ext
        return None
