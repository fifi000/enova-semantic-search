import json
import os
import dotenv

dotenv.load_dotenv()

from tqdm import tqdm

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker



DATABASE_PATH = './db/chroma_db_path'
DATA_PATH = './data/combined.json'
# DATA_PATH = '/data/wszystkie.json'

JSON_DATA = []


# helpers
def chunks(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def find_article_path(url: str) -> list[str]:
    if not JSON_DATA:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            JSON_DATA = json.load(f)
    
    docs = (doc for doc in JSON_DATA if doc['metadata']['source'] == url)
    article = next(docs, None)

    if not article:
        return []
    
    return article['metadata']['tags'].split('\t')


def load_docs() -> list[Document]:
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        json_docs = json.load(f)

        return [
            Document(**doc)
            for doc in json_docs
        ]
    

def create_db() -> Chroma:
    print('Loading documents...')
    docs = load_docs()
    print(f'Loaded {len(docs)} documents')

    assert docs, 'No documents found'

    # create vector store
    vectorstore = Chroma(persist_directory='./db/chroma_db_semantic', embedding_function=OpenAIEmbeddings())

    # split docs into chunks
    splitter = SemanticChunker(embeddings=OpenAIEmbeddings())
    # splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    # splits = splitter.split_documents(docs)

    # add chunks to vector store
    print('Adding documents to vector store...')
    for chunk in tqdm(chunks(docs, 80)[19:]):
        splits = splitter.split_documents(chunk)
        for el in chunks(splits, 1000):
            vectorstore.add_documents(el)
    print('Done')

    return vectorstore


def get_db(create_if_not_exists: bool = False):
    if os.path.exists(DATABASE_PATH):
        print('Loading database from file')
        return Chroma(persist_directory=DATABASE_PATH, embedding_function=OpenAIEmbeddings())
    
    if create_if_not_exists:
        print('Creating database')
        return create_db()
    
    raise FileNotFoundError(f'Database not found at `{DATABASE_PATH}`')
       

def main():
    db = Chroma(persist_directory='./db/chroma_db_paths', embedding_function=OpenAIEmbeddings())
    db._collection.add()
    data = json.load(open(DATA_PATH, 'r', encoding='utf-8'))
    tags = [
        { 'data': d['metadata']['tags'], 'source': d['metadata']['source'], 'tags': d['metadata']['tags'] }
        for d in data
    ]
    titles = [
        { 'data': path[-1], 'source': t['source'], 'tags': t['tags']}
        for t in tags if len(path := t['data'].split('\t')) > 1
    ]

    for tag in tags:
        tag['data'] = tag['data'].replace('\t', '. ')

    # all data
    all_data = tags + titles

    # create docs
    docs = [
        Document(page_content=d['data'], metadata={'source': d['source'], 'tags': d['tags']}) 
        for d in all_data
    ]

    # add to db
    print('Adding data to db...')
    for chunk in tqdm(chunks(docs, 1000)):
        db.add_documents(chunk)


if __name__ == '__main__':
    pass
  
