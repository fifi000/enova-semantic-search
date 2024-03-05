import os
import json
import random

import chromadb

from langchain_core.documents import Document
from langchain.vectorstores.chroma import Chroma
from langchain_openai.embeddings import OpenAIEmbeddings

from models import DocumentModel
from collections import defaultdict


_db_paths = {
    'html-headers': './db/chroma_db_html',
    'paths': './db/chroma_db_paths',
    'znaki-1000': './db/chroma_db_znaki_1000',
    'znaki-150': './db/chroma_db_znaki_150',
    'znaki-400': './db/chroma_db_znaki_400',
    'semantic': './db/chroma_db_semantic',
}
_data_path = './data/combined.json'
_json_data = None


def _find_article_path(url: str) -> list[str]:
    global _json_data

    if not _json_data:
        with open(_data_path, 'r', encoding='utf-8') as f:
            _json_data = json.load(f)
    
    docs = (doc for doc in _json_data if doc['metadata']['source'] == url)
    article = next(docs, None)

    if not article:
        return []
    
    return article['metadata']['tags'].split('\t')


def _get_db(db_path = '') -> Chroma:
    port = os.environ.get('CHROMA_DB_PORT', default=8080)
    client = chromadb.HttpClient(host='chromadb', port=port)
    return Chroma(client=client, embedding_function=OpenAIEmbeddings(), collection_name='langchain')

    # if os.path.exists(db_path):
    #     return Chroma(persist_directory=db_path, embedding_function=OpenAIEmbeddings())
    
    # raise FileNotFoundError(f'Database not found at `{db_path}`')


async def search_many(query: str, k: int = 10) -> dict[str, list[DocumentModel]]:
    # vector = await OpenAIEmbeddings().aembed_query(query)
    # tasks = [search(vector=vector, k=k, db_path=val) for val in _db_paths.values()]
    search_results = [await asearch(query=query, k=k, db_path=val) for val in _db_paths.values()]

    # if vector := await OpenAIEmbeddings().aembed_query(query):
    #     search_results = [search(vector=vector, k=k, db_path=val) for val in _db_paths.values()]
    # else:
    #     tasks = [asearch(query=query, k=k, db_path=val) for val in _db_paths.values()]
    #     search_results = await asyncio.gather(*tasks)

    return { key: res for key, res in zip(_db_paths.keys(), search_results) } 


def find_best(results: dict[str, list[DocumentModel]], n: 10) -> list[DocumentModel]:
    docs = [doc for res in results.values() for doc in res]

    # group by source
    groups = defaultdict(list)
    for doc in docs:
        groups[doc.source].append(doc)

    # get best from each group
    docs = [max(group, key=lambda x: x.score) for group in groups.values()]

    # sort by score
    docs = sorted(docs, key=lambda x: x.score, reverse=True)

    return docs[:n]


async def asearch(
        *,
        query: str = '',
        k: int = 10,
        db_path = ''
    ) -> list[DocumentModel]:

    db = _get_db(db_path)
    results = await db.asimilarity_search_with_relevance_scores(query, k=k)

    # map to DocumentModel
    results = [
        DocumentModel(res)
        for res in results
    ]
    
    # remove duplicates based on urls
    # group based on source {url: [doc1, doc2, ...]}
    groups = defaultdict(list)
    for doc in results:
        groups[doc.source].append(doc)

    # get best from each group
    docs = [max(group, key=lambda x: x.score) for group in groups.values()]

    # sort by score
    docs = sorted(docs, key=lambda x: x.score, reverse=True)

    return docs


def search(
        *,
        vector: list[float] = [],
        k: int = 10,
        db_path = ''
    ) -> list[DocumentModel]:

    db = _get_db(db_path)
    results = db.similarity_search_by_vector_with_relevance_scores(vector, k=k)

    # map to DocumentModel
    results = [
        DocumentModel(res)
        for res in results
    ]
    results = sorted(results, key=lambda x: x.score, reverse=True)

    return results


def search_mmr(query: str, k: int = 10) -> list[DocumentModel]:
    db = _get_db()
    results: list[Document] = db.as_retriever(search_type='mmr').get_relevant_documents(query)

    results = [(doc, random.random()) for doc in results]

    # map to DocumentModel
    results = [
        DocumentModel(res)
        for res in results
    ]

    # remove duplicates based on urls
    seen = set()
    new_results = []
    for res in results:
        if res.source not in seen:
            new_results.append(res)
            seen.add(res.source)
    results = new_results

    # remove duplicates based on content
    seen = set()
    new_results = []

    for res in results:
        if res.page_content not in seen:
            new_results.append(res)
            seen.add(res.page_content)
    results = new_results

    # sort by score
    # results = sorted(results, key=lambda x: x.score, reverse=True)

    return results

