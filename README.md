# 透け影工房_v2  
**ノベルゲーム制作者のための影絵・シルエット生成ツール**  

PNG画像から、透け感のある影絵・シルエット画像を生成できます。  
主に **ノベルゲームの立ち絵素材制作** を想定したツールです。  

コード、READMEなどのテキストの作成において、OpenAI の対話型AI「ChatGPT」を使用しています。  

本リポジトリでは、アプリの **ソースコード** と **実行ファイル** を公開しています。  

- アプリマニュアル：[README_PLAY.md](./README_PLAY.md)  
- 実行ファイルのダウンロード：[Releases](https://github.com/AglaoDev-jp/sukekage-kobo/releases/download/v2/sukekage-kobo_v2.zip)  

---

## 開発について

本プロジェクトの制作にあたり、OpenAI の対話型AI「ChatGPT」のサポートを受けて、  
アイデア出し、コード設計、実装、文章表現の改善などを効率的に行いました。  

- **GPT-5.2**
- **GPT-5.3**
- **GPT-5.5**
（ChatGPT Plus）  

開発に携わったすべての研究者・開発者・関係者の皆様に、心より感謝申し上げます。

---

## 免責事項
本アプリの利用や環境設定に起因するいかなる損害や不具合について、  
作者は一切の責任を負いません。

---

**製作期間**

- **v1**: 2026年1月10日 (試作・設計・実装で約3時間ほど)
- **v2**: 2026年2月16日 ~ 2026年5月3日

---

v2の変更点
- プリセットを記憶できるようにしました。
- 出力ファイルのリネーム方法を変更しました。


---

※ 本リポジトリは個人学習・個人制作を目的としています。  
そのため、Pull Request（PR）はお受けできません。ご了承ください。

---

## 使用言語とライブラリ

### 使用言語
- **Python 3.12.5**

---

### 使用モジュール・ライブラリ

#### 標準ライブラリ

- threading
- queue
- time
- random
- dataclasses
- pathlib
- typing
- tkinter

#### 外部ライブラリ
- **Pillow (PIL)**

### 実行ファイル化
- **PyInstaller**

---

### 使用エディター
- **Visual Studio Code (VSC)**  

---

### 著作権表示とライセンス

## 📂 ライセンスファイルまとめ[licenses](./licenses/)
- Python [LICENSE-PSF.txt](./licenses/LICENSE-PSF.txt)
- Tkinter [Tcl/Tk License](./licenses/third_party/LICENSE-TclTk.txt)
- Pillow (PIL)[MIT-CMU License](./licenses/third_party/LICENSE-Pillow.txt)
- PyInstaller [GNU GPL v2 or later（例外付き）](./licenses/third_party/LICENSE_PyInstaller.txt)

---

### **Python**  
- Copyright © 2001 Python Software Foundation. All rights reserved.
Licensed under the PSF License Version 2.  
[Python license](https://docs.python.org/3/license.html)  
 ※ コードのみであればライセンス添付は不要ですが、PyInstallerを使って実行ファイル化する際にはPythonのライセンス（PSF License）の添付が必要です。  
   (内部にPythonの一部が組み込まれるため)

#### **Tkinter**  
- © Regents of the University of California, Sun Microsystems, Inc., Scriptics Corporation, and other parties  
TkinterはPythonに含まれるGUIライブラリですが、その動作にはTcl/Tkが使用されています。  
- [Tcl/Tk License](https://www.tcl.tk/software/tcltk/license.html) 

---

### Pillow
- The Python Imaging Library (PIL): © 1997 Secret Labs AB / © 1995 Fredrik Lundh and Contributors  
- Pillow: © 2010 Jeffrey A. Clark and contributors  
- Licensed under the MIT-CMU License  
- [License](https://github.com/python-pillow/Pillow/blob/main/LICENSE)

---

#### 📦 PyInstaller  

このプロジェクトは、**PyInstaller** を使用して実行ファイル化に対応しています。  
PyInstaller は GNU GPL ライセンスですが、例外規定により  
**生成される実行ファイル自体は GPL の制約を受けません**。
- Copyright (c) 2010–2023, PyInstaller Development Team  
- Copyright (c) 2005–2009, Giovanni Bajo  
- Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.

#### ⚖️ PyInstaller のライセンス構成について

PyInstaller は以下のように**複数のライセンス形態**で構成されています：

- 🔹 **GNU GPL v2 or later（例外付き）**  
  本体およびブートローダに適用されます。  
  → **生成された実行ファイルは任意のライセンスで配布可能**です（依存ライブラリに従う限り）。

- 🔹 **Apache License 2.0**  
  ランタイムフック（`./PyInstaller/hooks/rthooks/`）に適用されています。  
  → 他プロジェクトとの連携や再利用を意識した柔軟なライセンス。

- 🔹 **MIT License**  
  一部のサブモジュール（`PyInstaller.isolated/`）およびそのテストコードに適用。  
  → 再利用を目的としたサブパッケージに限定適用されています。

####  詳細情報へのリンク

- [PyInstallerのライセンス文書（GitHub）](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)  
- [PyInstaller公式サイト](https://pyinstaller.org/en/v6.13.0/index.html)  

---

## 使用フォントについて

本アプリの UI は **Tkinter（ttk）標準のUIフォント**を使用しています。  
フォントは OS ごとに自動的に選択され、  
Windows / macOS / Linux それぞれの環境に適した表示になります。
※ プロジェクト内にはフォントファイルを同梱していません。

---

これらのプロジェクトの開発者の皆様、貢献者の皆様に、心より感謝申し上げます。

---

## ソースコードについて

### **Pythonのインストール**  
   `.py`ファイルの実行には、Pythonがインストールされている環境が必要です。

### 必要なライブラリのインストール

   - インストールがまだの場合は、以下のコマンドを使用してください。
  ```shell
  pip install pillow
  ```

### アプリの起動  
   コマンドラインインターフェースを使用して、以下の手順でアプリを起動します。  

   - `cd`コマンドで`main.py`ファイルのディレクトリに移動します。  
   例: `main.py`ファイルを右クリックして「プロパティ」の「場所」をコピーなど。  
   ```shell
   # 例: デスクトップにフォルダがある場合 (パスはPC環境により異なります)
   cd C:\Users\<ユーザー名>\Desktop\...\src
   ```

   - フォルダに移動後、以下のコマンドでアプリを起動します。  
   ```shell
   python main.py
   ```

### **コードエディターでの実行**  
   一部のコードエディター（VSCなど）では、直接ファイルを実行することが可能です。  

---

## PyInstallerによる実行ファイル化

このソースコードでは、**PyInstaller**を使用してPythonスクリプトを単一の実行ファイルに変換して使用することができました。  
この手順を実施することで、Python環境をインストールしていない環境でもアプリを実行できるようになります。配布にも適した形に仕上げることが可能です。  
以下に手順を示します：  

ディレクトリ構成：  

```
sukekage-kobo_v1/
  main.py
  icon.ico            ← exe のアイコンに使用

```

---

### 実行ファイルの作成方法

### 1. 必要なライブラリをインストール  
※ すでにインストール済みの場合は必要ありません。  

```shell
pip install pyinstaller pillow
```

### 2. プロジェクトフォルダに移動

```shell
cd <プロジェクトフォルダのパス>
```

例：デスクトップにプロジェクトがある場合

```shell
cd C:/Users/<ユーザー名>/Desktop/sukekage-kobo_v2
```

### 3. PyInstallerでビルド

以下のコマンドを **コマンドプロンプト** で実行します。

```shell
pyinstaller main.py ^
  --onefile ^
  --windowed ^
  --name "sukekage-kobo_v2" ^
  --icon "icon.ico" ^

```

### オプションの詳細説明

| オプション        | 説明                           |
| ------------ | ---------------------------- |
| `--onefile`  | 実行ファイルを **1つの exe** にまとめます   |
| `--windowed` | コンソール（黒い画面）を表示しません（GUIアプリ向け） |
| `--name`     | 出力される実行ファイルの名前を指定します         |
| `--icon`     | 実行ファイルに使用するアイコン（.ico）を指定します  |

---


### 実行ファイルの確認

PyInstallerが成功すると、以下のようなディレクトリ構成が作成されます：

```
プロジェクトフォルダ/
├── build/                 <- ビルド用一時ファイル（削除可）
├── dist/
│   └── SukekageStudio.exe <- 作成された実行ファイル
├── main.py
├── icon.ico
└── SukekageStudio.spec    <- 設定ファイル（削除可）

```

実行ファイルは`dist`フォルダ内に出力されます。  
`dist`フォルダ内に作成された実行ファイル（例: `SukekageStudio.exe`）を使用してアプリを実行できます。  
生成された実行ファイルは、Python環境を必要とせずに動作します。  
ひとつのシステムファイルにまとめられていますので、配布にも適した形になっています。  
distフォルダ内に作成された実行ファイルをそのまま配布するだけで、他のユーザーがアプリを使用できるようになります。  

### 注意事項
  ※この注意事項は、PyInstallerで生成された.exeファイルなどの実行ファイルについて記載しています。  
  Pythonスクリプト（.pyファイル）には該当しません。

- **セキュリティに関する注意**  
  PyInstallerはスクリプトを実行ファイルにまとめるだけのツールであり、コードの暗号化や高度な保護機能を提供するものではありません。  
  そのため、悪意のあるユーザーが実行ファイルを解析し、コードやデータを取得する可能性があります。  
  コードやデータなどにセキュリティが重要なプロジェクトで使用する場合は、**追加の保護手段を検討してください。**  

- **OSに応じた調整**  
  MacやLinux環境で作成する場合、`--add-data` オプションのセパレータやアイコン指定の書式が異なるようです。  
  詳細は[PyInstaller公式ドキュメント](https://pyinstaller.org)をご確認ください。  
  実行ファイル化において発生した問題は、PyInstallerのログを確認してください。  

- **ライセンスとクレジットに関する注意**   
    **推奨事項**  
     PyInstallerのライセンスはGPLv2（GNU General Public License Version 2）ですが、例外的に商用利用や非GPLプロジェクトでの利用を許可するための追加条項（特別例外）が含まれています。  
     実行ファイルを配布するだけであれば、PyInstallerの特別例外が適用されるため、GPLv2ライセンスの条件に従う必要はないようです。
     ライセンス条件ではありませんが、プロジェクトの信頼性を高めるため、READMEやクレジットに「PyInstallerを使用して実行ファイルを作成した」旨を記載することを推奨します。  

    **PyInstallerのライセンスが必要な場合**  
     PyInstallerのコードをそのまま再配布する場合、もしくは改変して再利用する場合は、GPLv2ライセンスに従う必要があります。  
     この場合、以下を実施してください：  
      - PyInstallerのライセンス文を同梱する。  
      - ソースコードを同梱するか、ソースコードへのアクセス手段を提供する。  

    **詳細情報**  
     PyInstallerのライセンスについて詳しく知りたい場合は、[公式リポジトリのLICENSEファイル](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)をご参照ください。  

---

## このアプリのライセンス

- **このアプリのコード**: MIT License。詳細は[LICENSE-CODE](./licenses/game/LICENSE-CODE.txt)ファイルを参照してください。
- **画像**: Creative Commons Attribution 4.0 (CC BY 4.0)。詳細は[LICENSE-IMAGES](./licenses/game/LICENSE-IMAGES.txt)ファイルを参照してください。

## ライセンスの簡単な説明

- **このアプリのコード**: （MIT License）
このアプリのコードは、MITライセンスのもとで提供されています。自由に使用、改変、配布が可能ですが、著作権表示とライセンスの文言を含める必要があります。

- **画像**: （Creative Commons Attribution 4.0, CC BY 4.0）
このアプリの画像は、CC BY 4.0ライセンスのもとで提供されています。自由に使用、改変、配布が可能ですが、著作権者のクレジットを表示する必要があります。

※これらの説明はライセンスの概要です。詳細な内容は各ライセンスの原文に準じます。

---

## クレジット表示のテンプレート（例）  

### コード
```plaintext
Code by AglaoDev-jp © 2026, licensed under the MIT License.
```

### 画像
```plaintext
Image by AglaoDev-jp © 2026, licensed under CC BY 4.0.
```

---

#### ライセンスの理由
現在のAI生成コンテンツの状況を踏まえ、私は本作品を可能な限りオープンなライセンス設定になるように心がけました。  
問題がある場合、状況に応じてライセンスを適切に見直す予定です。  

このライセンス設定は、権利の独占を目的とするものではありません。  
明確なライセンスを設定することにより、パブリックドメイン化するリスクを避けつつ、自由な利用ができるように期待するものです。  
  
© 2026 AglaoDev-jp  

