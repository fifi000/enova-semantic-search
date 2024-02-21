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



DATABASE_PATH = './db/chroma_db_znaki_150'
DATA_PATH = './data/combined.json'
# DATA_PATH = '/data/wszystkie.json'

JSON_DATA = []


# helpers
def chunks(lst, n):
    output = []
    for i in range(0, len(lst), n):
        output.append(lst[i:i + n])
    return output


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
    vectorstore = get_db(create_if_not_exists=True)

    while question := input('Question:\n'):
        print(f'\nSearch:')
        results = vectorstore.similarity_search_with_relevance_scores(question, k=10)        
        results = sorted(results, key=lambda x: x[1], reverse=True)

        seen = set()

        for doc, score in results:
            if doc.metadata['source'] in seen:
                continue
            print(f'Score: {score:.2f}')
            print(f'Doc: {doc.page_content[:250]}...')
            print(f'Source: {doc.metadata["source"]}\n')            
        print()


if __name__ == '__main__':
    create_db()
  
