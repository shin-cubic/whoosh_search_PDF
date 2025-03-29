import os
import glob
import shutil
import concurrent.futures
import pymupdf as fitz  # PyMuPDF
import MeCab
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID

class PDFIndexer:
    def __init__(self):
        try:
            self.mecab = MeCab.Tagger("-Owakati -r /etc/mecabrc")
        except RuntimeError as e:
            print(f"MeCabの初期化に失敗しました: {e}")
            self.mecab = None
        
    def extract_text(self, pdf_path):
        """PDFからテキストを抽出 (ページ番号付きで返す)"""
        try:
            pages = []
            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    text = page.get_text("text").strip()
                    if not text:
                        text = ''.join([block[4] for block in page.get_text("blocks") if block[4]]).strip()
                    text = text.encode('utf-8', 'ignore').decode('utf-8')
                    if text:
                        pages.append({'text': text, 'page_num': page_num})
            return pages if pages else None
        except Exception as e:
            print(f"エラー: {pdf_path}の読み込み失敗 - {str(e)}")
            return None
            
    def tokenize(self, text):
        """MeCabでテキストを分かち書き"""
        try:
            if self.mecab:
                return self.mecab.parse(text).strip()
            else:
                return text  # MeCabが使用できない場合はそのまま返す
        except Exception as e:
            print(f"分かち書きエラー: {str(e)}")
            return ""

    def process_pdf(self, pdf_path):
        """PDFを処理してインデックス追加用データを返す"""
        try:
            pages = self.extract_text(pdf_path)
            if not pages:
                return None
                
            title = os.path.basename(pdf_path)
            documents = []
            
            for page in pages:
                tokens = self.tokenize(page['text'])
                doc_data = {
                    'title': title,
                    'content': tokens,  # 検索用(トークン化済み)
                    'raw_content': page['text'],  # 表示用(生テキスト)
                    'path': pdf_path,
                    'page_num': str(page['page_num'])
                }
                documents.append(doc_data)
            
            return documents
        except Exception as e:
            print(f"処理エラー: {pdf_path} - {str(e)}")
            return None

def main():
    pdf_dir = "./pdf"
    index_dir = "./index"
    
    os.makedirs(index_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    
    schema = Schema(
        title=TEXT(stored=True),
        content=TEXT,  # 検索用(トークン化済み)
        raw_content=TEXT(stored=True),  # 表示用(生テキスト)
        path=ID(stored=True),
        page_num=ID(stored=True)  # ページ番号
    )
    
    # インデックスが存在しない場合、新規作成
    if not exists_in(index_dir):
        ix = create_in(index_dir, schema)
    else:
        ix = open_dir(index_dir)
    
    writer = ix.writer()
    indexer = PDFIndexer()
    
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    
    if pdf_files:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as executor:
            futures = {executor.submit(indexer.process_pdf, pdf): pdf for pdf in pdf_files}
        
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            if results:
                for doc in results:
                    writer.add_document(**doc)
    
    writer.commit()
    print(f"{len(pdf_files)}個のPDFを処理しました")

def search_index():
    from whoosh.qparser import QueryParser
    ix = open_dir("./index")
    
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        while True:
            query_str = input("検索語を入力 (終了はq): ")
            if query_str.lower() == 'q':
                break
            query = parser.parse(query_str)
            results = searcher.search(query, limit=10)
            
            print(f"\n検索結果 ({len(results)}件):")
            for hit in results:
                print(f"- {hit['title']} (ページ {hit['page_num']})")
                print(f"  {hit['raw_content'][:200]}...")
                print(f"  パス: {hit['path']}\n")

if __name__ == "__main__":
    main()
