import os
import json
import random
import asyncio

from langchain_core.documents import Document
from langchain.vectorstores.chroma import Chroma
from langchain_openai.embeddings import OpenAIEmbeddings

from models import DocumentModel


_db_paths = {
    'html-headers': './db/chroma_db_html',
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
    if os.path.exists(db_path):
        return Chroma(persist_directory=db_path, embedding_function=OpenAIEmbeddings())
    
    raise FileNotFoundError(f'Database not found at `{db_path}`')


async def search_many(query: str, k: int = 10) -> dict[str, list[DocumentModel]]:
    # create tasks
    tasks = [search(query, k, val) for val in _db_paths.values()]

    # wait for all tasks to complete
    search_results = await asyncio.gather(*tasks[len(tasks)//2:])
    search_results.extend(await asyncio.gather(*tasks[:len(tasks)//2]))

    return { key: res for key, res in zip(_db_paths.keys(), search_results) } 


def find_best(results: dict[str, list[DocumentModel]], n: 10) -> list[DocumentModel]:
    docs = [doc for res in results.values() for doc in res]

    # remove duplicates based on urls
    seen = set()
    new_docs = []
    for doc in docs:
        if doc.source not in seen:
            new_docs.append(doc)
            seen.add(doc.source)
    docs = new_docs

    # sort by score
    docs = sorted(docs, key=lambda x: x.score, reverse=True)

    return docs[:n]



async def search(query: str, k: int = 10, db_path = '') -> list[DocumentModel]:
    db = _get_db(db_path)
    results = await db.asimilarity_search_with_relevance_scores(query, k=k)

    # add tags
    for i, res in enumerate(results):
        doc, _ = res
        metadata = doc.metadata
        path = _find_article_path(metadata['source'])
        results[i][0].metadata['tags'] = path

    # map to DocumentModel
    results = [
        DocumentModel(res)
        for res in results
    ]

    # # remove duplicates based on urls
    # seen = set()
    # new_results = []
    # for res in results:
    #     if res.source not in seen:
    #         new_results.append(res)
    #         seen.add(res.source)
    # results = new_results

    # # remove duplicates based on content
    # seen = set()
    # new_results = []

    # for res in results:
    #     if res.page_content not in seen:
    #         new_results.append(res)
    #         seen.add(res.page_content)
    # results = new_results

    # sort by score
    results = sorted(results, key=lambda x: x.score, reverse=True)

    return results


def search_mmr(query: str, k: int = 10) -> list[DocumentModel]:
    db = _get_db()
    results: list[Document] = db.as_retriever(search_type='mmr').get_relevant_documents(query)

    results = [(doc, random.random()) for doc in results]

    # add tags
    for i, res in enumerate(results):
        doc, _ = res
        metadata = doc.metadata
        path = _find_article_path(metadata['source'])
        results[i][0].metadata['tags'] = path

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

