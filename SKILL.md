---
name: zabit-katibi
description: UYAP Doküman Editörü .udf dosyalarını okur ve yazar. Kullanıcı bir .udf dosyasının içeriğini okumak, özetlemek veya düzenlemek, bir klasördeki .udf'leri taramak ya da herhangi bir metni UYAP'ta açılabilen .udf olarak kaydetmek istediğinde kullan.
---

# Zabıt Katibi

UYAP `.udf` dosyalarını okur ve yazar. Tek bağımlılık Python 3 (standart kütüphane).

Script: bu dosyanın bulunduğu klasördeki `scripts/udf_tool.py`.

## Okuma

```bash
python3 scripts/udf_tool.py dosya.udf     # tek dosyanın metni
python3 scripts/udf_tool.py klasör/       # klasördeki tüm .udf'ler
```

## Yazma

Metni işaretlemeli olarak bir dosyaya yaz, sonra çevir:

```bash
python3 scripts/udf_tool.py yaz belge.txt belge.udf
```

| Yazım | Sonuç |
|---|---|
| Her satır | Bir paragraf |
| Boş satır | Boş paragraf |
| `[orta] ...` / `[sağ] ...` / `[iki] ...` | Ortalı / sağa yaslı / iki yana yaslı |
| Önek yok veya `[sol] ...` | Sola dayalı |
| `**metin**` / `*metin*` / `__metin__` | Kalın / italik / altı çizili |
| Tab karakteri veya `\t` | Tab |

Yazdıktan sonra dosyayı okuma komutuyla açıp içeriği kontrol et.

## Python ile

```python
import sys; sys.path.insert(0, "<skill-klasörü>/scripts")
import udf_tool as u

doc = u.read_udf("dosya.udf")         # paragraphs -> runs (text, bold, italic, underline)
print(doc.text)
doc.paragraphs[0].runs[0].text = "..."
u.write_udf(doc, "yeni.udf")          # düzenleyip geri yaz
u.markup_to_udf(metin, "belge.udf")   # işaretlemeli metinden .udf
u.batch_extract_texts("klasör/")      # {dosya_adı: metin}
```

## Format notları

`udf_tool.py` bunları doğru yapıyor; doğrudan XML üretirken bozma, yoksa UYAP Doküman Editörü sonsuz "loading" ekranında kalır.

- UDF = ZIP içinde `content.xml` (imzalılarda ayrıca `sign.sgn`; düzenlenen dosyada imza geçersizleşir).
- Metin tek bir CDATA havuzunda; `<elements>` içindeki `startOffset`/`length` bu havuza işaret eder (karakter sayısı, byte değil).
- Her paragraf CDATA'da `\n` ile biter ve bu `\n` de `length="1"` bir `<content>` ile kapsanır.
- `<styles>` bloğu zorunlu. Belge fontu `hvl-default` = Times New Roman 12; run'lara `family`/`size` yazılmaz.
- Font boyutu özniteliğinin adı `size` (`fontSize` değil).
