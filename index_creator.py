#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import concurrent.futures
import fitz  # PyMuPDF
import MeCab
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID

class PDFIndexer:
    def __init__(self):
        self.mecab = MeCab.Tagger("-Owakati")
        
    def extract_text(self, pdf_path):
        """PDFからテキストを抽出 (ページ番号付きで返す)"""
        try:
            pages = []
            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    # 複数の方法でテキスト抽出を試みる
                    text = ""
                    try:
                        # 方法1: 標準的なテキスト抽出
                        text = page.get_text("text").strip()
                        if not text:
                            # 方法2: 代替抽出方法
                            text = ''.join([block[4] for block in page.get_text("blocks") if block[4]]).strip()
                        
                        # 文字コード正規化
                        text = text.encode('utf-8', 'ignore').decode('utf-8')
                        
                        if text:
                            pages.append({
                                'text': text,
                                'page_num': page_num 
                            })
                            print(f"抽出成功: {pdf_path} ページ{page_num} - 文字数: {len(text)}")
                        else:
                            print(f"警告: 空のテキスト - {pdf_path} ページ{page_num}")
                    except Exception as e:
                        print(f"テキスト抽出エラー: {pdf_path} ページ{page_num} - {str(e)}")
            
            return pages if pages else None
        except Exception as e:
            print(f"エラー: {pdf_path}の読み込み失敗 - {str(e)}")
            return None
            
    def tokenize(self, text):
        """MeCabでテキストを分かち書き"""
        try:
            return self.mecab.parse(text)
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
                # デバッグ用にテキスト内容を表示
                print(f"処理中: {title} ページ{page['page_num']} - テキスト長:{len(page['text'])}")
                
                # raw_contentに確実にテキストが保存されるように
                doc_data = {
                    'title': title,
                    'content': tokens,  # 検索用(トークン化済み)
                    'raw_content': page['text'] if page['text'] else "",  # 表示用(生テキスト)
                    'path': pdf_path,
                    'page_num': str(page['page_num'])
                }
                documents.append(doc_data)
            
            return documents
        except Exception as e:
            print(f"処理エラー: {pdf_path} - {str(e)}")
            return None

def search_index(ix):
    """インデックスを検索して結果を表示"""
    from whoosh.qparser import QueryParser
    
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
                print(f"  パス: {hit['path']}\n")

def get_existing_indexed_files(ix):
    """既にインデックス化されているファイルのパスを取得"""
    indexed_files = set()
    with ix.searcher() as searcher:
        for fields in searcher.all_stored_fields():
            indexed_files.add(fields['path'])
    return indexed_files

def needs_update(pdf_path, indexed_time):
    """PDFファイルが更新されているかチェック"""
    return os.path.getmtime(pdf_path) > indexed_time

def main():
    # ディレクトリ設定
    pdf_dir = "./pdf"
    index_dir = "./index"
    
    # ディレクトリ作成
    os.makedirs(index_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    
    # スキーマ定義 (ページ番号と生テキスト追加)
    schema = Schema(
        title=TEXT(stored=True),
        content=TEXT,  # 検索用(トークン化済み)
        raw_content=TEXT(stored=True),  # 表示用(生テキスト)
        path=ID(stored=True),
        page_num=ID(stored=True)  # ページ番号も保存
    )
    
    # インデックスディレクトリをクリアして新規作成
    if os.path.exists(index_dir):
        for f in os.listdir(index_dir):
            os.remove(os.path.join(index_dir, f))
    ix = create_in(index_dir, schema)
    
    writer = ix.writer()
    
    # PDFインデクサ初期化
    indexer = PDFIndexer()
    
    # 全てのPDFファイルを処理
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    
    if pdf_files:
        # 並列処理でPDFを処理
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(indexer.process_pdf, pdf) for pdf in pdf_files]
        
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            if results:
                for doc in results:
                    writer.add_document(**doc)
    
    if pdf_files:
        # インデックス保存
        writer.commit()
        print(f"{len(pdf_files)}個のPDFを追加/更新しました")
    else:
        writer.cancel()
        print("更新が必要なPDFはありませんでした")

if __name__ == "__main__":
    main()
