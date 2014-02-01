from __future__ import unicode_literals

import logging
import os
import re
import shutil
import sys

from mopidy import local
from mopidy.local import translator
from mopidy.models import Ref, SearchResult
from mopidy.utils import path

from whoosh import collectors, fields, index, query as query_lib

logger = logging.getLogger(__name__)

schema = fields.Schema(
    uri=fields.ID(stored=True, unique=True),
    parent=fields.ID(stored=True),
    pathname=fields.ID(stored=True),
    type=fields.ID(stored=True),
    name=fields.TEXT(),
    artists=fields.TEXT(),
    album=fields.TEXT(),
    content=fields.TEXT(),
    track=fields.STORED())

mapping = {'uri': 'uri',
           'track_name': 'name',
           'album': 'album',
           'artist': 'artists',
           'any': 'content'}


class _CountingCollector(collectors.Collector):
    """Collector which only counts documents found without fetching."""
    def prepare(self, top_searcher, q, context):
        super(_CountingCollector, self).prepare(top_searcher, q, context)
        self.count = 0

    def collect(self, sub_docnum):
        self.count += 1


def _track_to_refs(track):
    track_path = translator.local_track_uri_to_path(track.uri, b'/')
    track_path = track_path.decode(sys.getfilesystemencoding(), 'replace')
    parts = re.findall(r'([^/]+)', track_path)

    track_ref = Ref.track(uri=track.uri, name=parts.pop())
    refs = [Ref.directory(uri='local:directory')]

    for i in range(len(parts)):
        directory = '/'.join(parts[:i+1])
        uri = translator.path_to_local_directory_uri(directory)
        refs.append(Ref.directory(uri=unicode(uri), name=parts[i]))

    return refs + [track_ref]


class WhooshLibrary(local.Library):
    name = 'whoosh'

    def __init__(self, config):
        self._data_dir = os.path.join(config['local']['data_dir'], b'whoosh')
        self._writer = None
        self._counts = None

        if not os.path.exists(self._data_dir):
            path.get_or_create_dir(self._data_dir)
            self._index = index.create_in(self._data_dir, schema)
        else:
            self._index = index.open_dir(self._data_dir)

    def load(self):
        self._index.refresh()
        with self._index.searcher() as searcher:
            collector = _CountingCollector()
            query = query_lib.Term('type', 'track')
            searcher.search_with_collector(query, collector)
        return collector.count

    def lookup(self, uri):
        with self._index.searcher() as searcher:
            result = searcher.document(uri=uri, type='track')
            if result:
                return result['track']
        return None

    def browse(self, uri):
        result = []

        with self._index.searcher() as searcher:
            query = query_lib.Term('parent', uri)
            for doc in searcher.search(query, limit=None):
                if doc['type'] == 'track':
                    ref = Ref.track(uri=doc['uri'], name=doc['pathname'])
                else:
                    ref = Ref.directory(uri=doc['uri'], name=doc['pathname'])
                result.append(ref)

        result.sort(key=lambda ref: (ref.type, ref.name))
        return result

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        # TODO: add limit and offset, and total to results

        parts = [query_lib.Term('type', 'track')]
        for name, values in query.items():
            if name not in mapping:
                continue

            terms = []
            field_name = mapping[name]
            field = schema[field_name]

            for value in values:
                tokens = field.process_text(value, mode="query")
                if exact:
                    terms.append(query_lib.Phrase(field_name, list(tokens)))
                else:
                    terms.append(query_lib.And([
                        query_lib.FuzzyTerm(field_name, t) for t in tokens]))

            parts.append(query_lib.Or(terms))

        whoosh_query = query_lib.And(parts)
        logger.debug('Performing search: %s', whoosh_query)

        with self._index.searcher() as searcher:
            results = searcher.search(whoosh_query, limit=limit)
            tracks = [result['track'] for result in results]

        return SearchResult(tracks=tracks)

    def begin(self):
        self._writer = self._index.writer()
        self._counts = {}

        with self._index.reader() as reader:
            for docnum, doc in reader.iter_docs():
                self._counts.setdefault(doc['parent'], 0)
                self._counts[doc['parent']] += 1

                if doc['type'] == 'directory':
                    self._counts.setdefault(doc['uri'], 0)
                elif doc['type'] == 'track':
                    yield doc['track']

    def add(self, track):
        content = [track.name, track.album.name]
        content.extend(a.name for a in track.artists)
        refs = _track_to_refs(track)

        # Add track to search index:
        self._writer.update_document(
            uri=unicode(track.uri), type='track',
            parent=refs[-2].uri, pathname=refs[-1].name,
            name=track.name, album=track.album.name,
            artists=' '.join(a.name for a in track.artists),
            content=' '.join(content), track=track)

        # Add any missing directories to search index:
        for i in reversed(range(1, len(refs)-1)):
            uri = unicode(refs[i].uri)
            name = refs[i].name
            parent = unicode(refs[i-1].uri)

            self._counts.setdefault(uri, 0)
            self._counts[uri] += 1

            if self._counts[uri] > 1:
                break

            self._writer.update_document(
                uri=uri, type='directory', parent=parent, pathname=name)

    def remove(self, uri):
        # Traverse up tree as long as dir is empty, also handles initial track
        while self._counts.get(uri, 0) < 1:

            # Lookup the uri to get its parent.
            with self._index.searcher() as searcher:
                result = searcher.document(uri=uri)

            # Delete the uri and remove its count if it had one.
            self._writer.delete_by_term('uri', uri)
            self._counts.pop(uri, None)

            if not result:
                break

            # Move up to the parent and reduce its count by one.
            uri = result['parent']
            self._counts[uri] -= 1

    def flush(self):
        self._writer.commit(merge=False)
        self._writer = self._index.writer()
        return True

    def close(self):
        self._writer.commit(optimize=True)

    def clear(self):
        try:
            shutil.rmtree(self._data_dir)
            return True
        except OSError:
            return False
