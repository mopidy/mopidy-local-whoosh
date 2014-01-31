from __future__ import unicode_literals

import logging
import os
import shutil

from mopidy import models, local
from mopidy.utils import path

from whoosh import fields, index, query as query_lib

logger = logging.getLogger('mopidy_local_whoosh.library')

schema = fields.Schema(
    uri=fields.ID(stored=True, unique=True),
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


class WhooshLibrary(local.Library):
    name = 'whoosh'

    def __init__(self, config):
        self._data_dir = os.path.join(config['local']['data_dir'], b'whoosh')
        self._writer = None

        if not os.path.exists(self._data_dir):
            path.get_or_create_dir(self._data_dir)
            self._index = index.create_in(self._data_dir, schema)
        else:
            self._index = index.open_dir(self._data_dir)

    def load(self):
        self._index.refresh()
        return self._index.doc_count()

    def lookup(self, uri):
        with self._index.searcher() as searcher:
            result = searcher.document(uri=uri)
            if result:
                return [result['track']]
        return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        # TODO: add limit and offset, and total to results
        parts = []
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

        return models.SearchResult(tracks=tracks)

    def begin(self):
        self._writer = self._index.writer()

        with self._index.reader() as reader:
            for docnum, doc in reader.iter_docs():
                yield doc['track']

    def add(self, track):
        content = [track.name, track.album.name]
        content.extend(a.name for a in track.artists)

        self._writer.update_document(
            uri=unicode(track.uri),
            name=track.name,
            artists=' '.join(a.name for a in track.artists),
            album=track.album.name,
            content=' '.join(content),
            track=track)

    def remove(self, uri):
        self._writer.delete_by_term('uri', uri)

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
