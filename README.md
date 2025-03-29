# PDF検索システム

日本語PDFファイルの全文検索と該当ページ抽出ができるWebアプリケーションです。

## 主な機能

- PDFファイルの全文検索（日本語対応）
- 検索結果のハイライト表示
- 該当ページのみを抽出したPDF生成
- オリジナルPDFの表示

## 動作環境

- Python 3.7+
- 必要なライブラリ:
  - Flask
  - Whoosh
  - PyMuPDF (fitz)
  - MeCab

## インストール方法

1. リポジトリをクローン:
```bash
git clone [リポジトリURL]
cd whoosh
```

2. 依存ライブラリをインストール:
```bash
pip install -r requirements.txt
```

3. MeCab辞書をインストール（必要な場合）:
```bash
sudo apt-get install mecab mecab-ipadic-utf8 libmecab-dev
```

## 使用方法

1. PDFファイルを`pdf/`ディレクトリに配置

2. インデックスを作成:
```bash
python index_creator.py
```

3. Webサーバーを起動:
```bash
python index_gui.py
```

4. ブラウザでアクセス:
```
http://localhost:5001
```

## 操作方法

1. 検索ボックスにキーワードを入力
2. 検索結果から:
   - 「元のPDFを表示」でオリジナルPDFを表示
   - 「このファイルの検索結果PDFを生成」で該当ページのみのPDFをダウンロード

## ディレクトリ構成

```
whoosh/
├── pdf/              # PDF保存ディレクトリ
├── index/            # 検索インデックス
├── index_creator.py  # インデックス作成スクリプト
├── index_gui.py      # Webインターフェース
└── README.md         # このファイル
```

## ライセンス

MIT License
