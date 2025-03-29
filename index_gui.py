#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template_string, request, send_from_directory, Response, jsonify
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh.highlight import HtmlFormatter, WholeFragmenter
from collections import defaultdict
import os
import fitz  # PyMuPDF
import io

app = Flask(__name__)
app.config['INDEX_DIR'] = "./index"
app.config['PDF_DIR'] = "./pdf"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PDF検索システム</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .search-box { margin-bottom: 20px; }
        .result-item { margin-bottom: 15px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .title { font-weight: bold; font-size: 1.1em; }
        .path { color: #666; font-size: 0.9em; margin-top: 3px; }
        .pages { color: #666; font-size: 0.8em; margin: 5px 0; }
        .snippet { margin-top: 10px; color: #333; background-color: #f8f8f8; padding: 10px; border-radius: 5px; }
        .highlight { background-color: yellow; font-weight: bold; }
        .view-pdf { margin-top: 10px; }
        .view-pdf a { color: #1a73e8; text-decoration: none; }
        .view-pdf a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>PDF検索システム</h1>
    <form class="search-box" method="GET">
        <input type="text" name="q" value="{{ query }}" placeholder="検索語を入力" size="50">
        <button type="submit">検索</button>
    </form>
    
    {% if results is not none %}
        <div class="result-count">{{ results|length }}件見つかりました</div>
        {% for hit in results %}
            <div class="result-item">
                <div class="title">{{ hit['title'] }}</div>
                <div class="path">{{ hit['path'] }}</div>
                <div class="pages">該当ページ: {{ hit['page_nums'] }}</div>
                <div class="snippet">{{ hit['snippet']|safe }}</div>
                <div class="view-pdf">
                    <a href="/view_pdf?path={{ hit['path']|urlencode }}" target="_blank">元のPDFを表示</a> | 
                    <a href="/generate_pdf?path={{ hit['path']|urlencode }}&pages={{ hit['page_nums'] }}" class="generate-pdf" target="_blank">このファイルの検索結果PDFを生成</a>
                </div>
            </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    results = None
    
    if query:
        try:
            ix = open_dir(app.config['INDEX_DIR'])
            with ix.searcher() as searcher:
                parser = QueryParser("content", ix.schema)
                query_obj = parser.parse(query)
                
                search_results = searcher.search(query_obj, limit=50, terms=True)
                search_results.fragmenter = WholeFragmenter()
                
                grouped_results = defaultdict(list)
                for hit in search_results:
                    grouped_results[hit['path']].append(hit)
                
                output = []
                for path, hits in grouped_results.items():
                    combined_text = " ".join([h.get('raw_content', '') for h in hits])
                    page_nums = ", ".join(sorted(set(h['page_num'] for h in hits), key=int))
                    
                    try:
                        highlighter = hits[0].highlights("content", text=combined_text[:1000])
                        highlighter = highlighter.replace('class="highlight"', 
                                                     'style="background-color: yellow; font-weight: bold;"')
                        if len(combined_text) > 1000:
                            highlighter += "..."
                    except Exception as e:
                        print(f"ハイライトエラー: {str(e)}")
                        highlighter = combined_text[:1000] + ("..." if len(combined_text) > 1000 else "")
                    
                    output.append({
                        'title': hits[0]['title'],
                        'path': path,
                        'page_nums': page_nums,
                        'snippet': highlighter
                    })
                
                results = sorted(output, key=lambda x: len(x['page_nums']), reverse=True)
                    
        except Exception as e:
            return f"エラーが発生しました: {str(e)}", 500
    
    return render_template_string(HTML_TEMPLATE, query=query, results=results)

@app.route('/generate_pdf')
def generate_pdf():
    try:
        pdf_path = request.args.get('path', '')
        page_nums = request.args.get('pages', '')
        
        if not pdf_path or not pdf_path.startswith('./pdf/') or not page_nums:
            return "無効なリクエストです", 400
        
        # ページ番号を解析
        pages = sorted([int(p) for p in page_nums.split(',')])
        
        # 元のPDFを開く
        pdf_filename = os.path.basename(pdf_path)
        src_pdf = fitz.open(os.path.join(app.config['PDF_DIR'], pdf_filename))
        
        # 新しいPDFドキュメントを作成
        pdf_doc = fitz.open()
        
        # 指定ページを抽出
        for page_num in pages:
            pdf_doc.insert_pdf(src_pdf, from_page=page_num-1, to_page=page_num-1)
        src_pdf.close()
        
        # メモリ上にPDFを保存
        pdf_bytes = io.BytesIO()
        pdf_doc.save(pdf_bytes)
        pdf_doc.close()
        
        # ファイル名を安全に生成
        safe_name = pdf_filename.replace('.pdf', '') + '_selected_pages.pdf'
        
        # PDFをレスポンスとして返す
        pdf_bytes.seek(0)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment;filename={safe_name}",
                "Content-Type": "application/pdf"
            }
        )
    
    except Exception as e:
        return f"PDF生成エラー: {str(e)}", 500

@app.route('/view_pdf')
def view_pdf():
    pdf_path = request.args.get('path', '')
    if not pdf_path or not pdf_path.startswith('./pdf/'):
        return "無効なPDFパスです", 400
    
    pdf_filename = os.path.basename(pdf_path)
    return send_from_directory(app.config['PDF_DIR'], pdf_filename, as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
