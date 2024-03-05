from langchain_core.documents import Document


class DocumentModel:
    def __init__(self, result: tuple[Document, float]):
        doc, score = result
        metadata = doc.metadata
        
        self.score = score
        self.page_content = doc.page_content
        # self.source = metadata['source']
        self.source = metadata.get('source', 'unknown')
        self.path = metadata['tags'].split('\t')
        self.title = self.path[-1]