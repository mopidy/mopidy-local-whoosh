from __future__ import unicode_literals

import logging
import os
import re
import shutil
import sys

from mopidy import models, local
from mopidy.local import translator
from mopidy.utils import path

from whoosh import collectors, fields, index, query as query_lib

logger = logging.getLogger('mopidy_local_whoosh.library')

schema = fields.Schema(
    uri=fields.ID(stored=True, unique=True),
    type=fields.ID(stored=True),
    object=fields.STORED(),
    name=fields.TEXT(),
    artists=fields.TEXT(),
    album=fields.TEXT(),
    content=fields.TEXT())

mapping = {'uri': 'uri',
           'track_name': 'name',
           'album': 'album',
           'artist': 'artists',
           'any': 'content'}


class _CountingCollector(collectors.Collector):
    def prepare(self, top_searcher, q, context):
        super(_CountingCollector, self).prepare(top_searcher, q, context)
        self.count = 0

    def collect(self, sub_docnum):
        self.count += 1


class WhooshLibrary(local.Library):
    name = 'whoosh'

    def __init__(self, config):
        self._data_dir = os.path.join(config['local']['data_dir'], b'whoosh')
        self._writer = None
        self._directories = {}

        if not os.path.exists(self._data_dir):
            path.get_or_create_dir(self._data_dir)
            self._index = index.create_in(self._data_dir, schema)
        else:
            self._index = index.open_dir(self._data_dir)

    def load(self):
        self._index.refresh()
        with self._index.searcher() as searcher:
            counter = _CountingCollector()
            query = query_lib.Term('type', 'track')
            searcher.search_with_collector(query, counter)
        return counter.count

    def lookup(self, uri):
        with self._index.searcher() as searcher:
            result = searcher.document(uri=uri, type='track')
            if result:
                return result['object']
        return []

    def browse(self, uri):
        with self._index.searcher() as searcher:
            result = searcher.document(uri=uri, type='directory')
            if result:
                return result['object']
        return []

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
            tracks = [result['object'] for result in results]

        return models.SearchResult(tracks=tracks)

    def begin(self):
        self._writer = self._index.writer()

        with self._index.reader() as reader:
            for docnum, document in reader.iter_docs():
                if document['type'] == 'track':
                    yield document['object']

    def add(self, track):
        content = [track.name, track.album.name]
        content.extend(a.name for a in track.artists)

        self._writer.update_document(
            uri=unicode(track.uri),
            type='track',
            object=track,
            name=track.name,
            artists=' '.join(a.name for a in track.artists),
            album=track.album.name,
            content=' '.join(content))

        path = translator.local_track_uri_to_path(track.uri, b'/')
        path = path.decode(sys.getfilesystemencoding(), 'replace')
        parts = re.findall(r'([^/]+)', path)

        ref = models.Ref.track(uri=track.uri, name=parts.pop())
        dir_refs = [models.Ref.directory(uri='local:directory')]

        for i in range(len(parts)):
            directory = '/'.join(parts[:i+1])
            uri = translator.path_to_local_directory_uri(directory)
            dir_refs.append(
                models.Ref.directory(uri=unicode(uri), name=parts[i]))

        for dir_ref in reversed(dir_refs):
            if dir_ref.uri in self._directories:
                document = self._directories[dir_ref.uri]
            else:
                with self._index.searcher() as searcher:
                    document = searcher.document(uri=dir_ref.uri)

            if not document:
                document = {
                    'uri': dir_ref.uri, 'type': 'directory', 'object': []}

            if ref not in document['object']:
                document['object'].append(ref)

            if dir_ref.uri in self._directories:
                break

            self._directories[dir_ref.uri] = document
            ref = dir_ref

    def remove(self, uri):
        self._writer.delete_by_term('uri', uri)
        # TODO: cleanup dirs etc.

    def flush(self):
        self._writer.commit(merge=False)
        self._writer = self._index.writer()
        for document in self._directories.values():
            self._writer.update_document(**document)
        self._directories = {}
        return True

    def close(self):
        for document in self._directories.values():
            self._writer.update_document(**document)
        self._writer.commit(optimize=True)

    def clear(self):
        try:
            shutil.rmtree(self._data_dir)
            return True
        except OSError:
            return False
