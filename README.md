# magcnv

magcnvは**デジタル8色専用**のMAG画像コンバータです。

任意の形式からMAG形式への変換、及び、MAG形式から任意の形式への変換が多分可能です。

256色形式のMAGには対応しておらず、16色形式で、なおかつデジタル8色に強制変換しますので、デジタル8色の古いPC向けにお使いください。

## Install

```
pip install git+https://github.com/h-o-soft/magcnv
```

## Usage

```
usage: magcnv [-h] [-f] [path ...]

magcnv MAG image converter Version 0.1.0 Copyright 2022 H.O SOFT Inc.

positional arguments:
  path         file path(s)

optional arguments:
  -h, --help   show this help message and exit
  -f, --force  set force write
```
### MAG形式への変換

```
magcnv image-file-path
```

または

```
magcnv image-file-path output-file-path
```

拡張子がMAG以外の画像を引数として渡すと、そのファイル名の拡張子を「mag」に変更して出力します。また、明示的に出力ファイル名を渡すと、そのパスに出力します。

既に画像ファイルがある場合は上書きされませんので、上書きしたい場合はオプション「-f」をつけてください。

### 任意の画像形式への変換

```
magcnv mag-file-path
```

または

```
magcnv mag-file-path output-file-path
```

拡張子がMAGまたはmagのファイルを渡すと、その画像を任意の画像形式に変換して出力します。

出力される形式は拡張子から判断されますが、通常はpngなどにしておくのが良いでしょう。

## 謝辞

MAGの展開コードはemkさんの[HTML5 まぐろーだー](http://emk.name/2015/03/magjs.html)を参考に実装しました。ありがとうございます。

## Author
* OGINO Hiroshi
* H.O SOFT Inc.
* twitter: @honda_ken

## License
"magcnv" is under [MIT license](LICENSE)

