"""
UYAP .udf dosya format okuyucu/yazıcı.

Bir .udf dosyası aslında bir ZIP arşividir:
  - content.xml            : zorunlu, belge metni + biçimlendirme
  - documentproperties.xml : opsiyonel, belge özellikleri
  - sign.sgn               : opsiyonel, e-imza verisi (varsa dosyayı imzasız
                              yeniden yazınca imza geçersiz kalır)

content.xml yapısı:
  <template format_id="1.8">
    <content><![CDATA[ ... düz metin ... ]]></content>
    <properties><pageFormat .../></properties>
    <elements resolver="hvl-default">
      <paragraph Alignment="1">
        <content bold="true" family="Calibri" startOffset="0" length="38" />
        ...
      </paragraph>
      ...
    </elements>
  </template>

Biçimlendirme metinden ayrı tutulur: <elements> içindeki her <content>/<space>
etiketi, ana CDATA metninin startOffset:startOffset+length aralığına karşılık
gelir ve o aralığın bold/italic/underline/family/fontSize gibi özelliklerini
taşır. <paragraph> etiketleri satır/paragraf sınırlarını belirler.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape


@dataclass
class Run:
    """Bir paragraf içindeki, tek biçimlendirmeye sahip metin parçası."""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    # family/size normalde YAZILMAZ: belge geneli <styles> içindeki
    # hvl-default (Times New Roman 12) ile belirlenir. Sadece o paragrafta
    # fontu gerçekten değiştiriyorsan doldur.
    family: str | None = None
    size: int | None = None
    is_space: bool = False


@dataclass
class Paragraph:
    alignment: int = 0  # 0=sol,1=orta,2=sağ,3=iki yana yasla (UYAP'ta gözlenen)
    tabset: str | None = None
    runs: list[Run] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class UdfDocument:
    paragraphs: list[Paragraph] = field(default_factory=list)
    format_id: str = "1.8"
    page_format: dict = field(default_factory=lambda: {
        "mediaSizeName": "1",
        "leftMargin": "70.8661413192749",
        "rightMargin": "42.51968479156494",
        "topMargin": "42.51968479156494",
        "bottomMargin": "42.51968479156494",
        "paperOrientation": "1",
        "headerFOffset": "20.0",
        "footerFOffset": "20.0",
    })

    @property
    def text(self) -> str:
        """Tüm belgenin düz metni (paragraflar arasında satır sonu ile)."""
        return "\n".join(p.text for p in self.paragraphs)


_TAG_RE = re.compile(r"<(paragraph|content|space)\b([^>]*)/?>|</paragraph>", re.S)
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def _parse_attrs(attr_str: str) -> dict:
    return {k: v for k, v in _ATTR_RE.findall(attr_str)}


def _read_zip_member(zf: zipfile.ZipFile, name: str) -> str | None:
    try:
        return zf.read(name).decode("utf-8")
    except KeyError:
        return None


def read_udf(path: str | Path) -> UdfDocument:
    """Bir .udf dosyasını okuyup UdfDocument olarak döndürür."""
    path = Path(path)
    with zipfile.ZipFile(path, "r") as zf:
        content_xml = _read_zip_member(zf, "content.xml")
        if content_xml is None:
            raise ValueError(f"{path}: content.xml bulunamadı, geçerli bir .udf değil")

    cdata_match = re.search(r"<content><!\[CDATA\[(.*?)\]\]></content>", content_xml, re.S)
    if not cdata_match:
        raise ValueError(f"{path}: CDATA içerik bloğu bulunamadı")
    full_text = cdata_match.group(1)

    format_id_match = re.search(r'format_id="([^"]*)"', content_xml)
    format_id = format_id_match.group(1) if format_id_match else "1.8"

    page_format = {}
    pf_match = re.search(r"<pageFormat\b([^>]*)/>", content_xml)
    if pf_match:
        page_format = _parse_attrs(pf_match.group(1))

    elements_match = re.search(r"<elements\b[^>]*>(.*)</elements>", content_xml, re.S)
    doc = UdfDocument(format_id=format_id, page_format=page_format or UdfDocument().page_format)

    if not elements_match:
        # elements bloğu yoksa düz metni tek paragraf gibi ele al
        doc.paragraphs.append(Paragraph(runs=[Run(text=full_text)]))
        return doc

    elements_xml = elements_match.group(1)

    current_para: Paragraph | None = None
    pos = 0
    for m in re.finditer(
        r'<paragraph\b([^>]*)>|</paragraph>|<content\b([^>]*)/>|<space\b([^>]*)/>',
        elements_xml,
        re.S,
    ):
        whole = m.group(0)
        if whole.startswith("<paragraph"):
            attrs = _parse_attrs(m.group(1) or "")
            current_para = Paragraph(
                alignment=int(attrs.get("Alignment", "0")),
                tabset=attrs.get("TabSet"),
            )
            doc.paragraphs.append(current_para)
        elif whole == "</paragraph>":
            # Her paragrafın CDATA'daki kendi "\n" sonlandırıcısını, model
            # temiz kalsın diye burada düşürüyoruz; write_udf tekrar ekliyor.
            if current_para and current_para.runs and current_para.runs[-1].text == "\n":
                current_para.runs.pop()
            current_para = None
        elif whole.startswith("<content") or whole.startswith("<space"):
            is_space = whole.startswith("<space")
            attrs = _parse_attrs(m.group(3) if is_space else m.group(2))
            start = int(attrs.get("startOffset", "0"))
            length = int(attrs.get("length", "0"))
            run_text = full_text[start:start + length]
            run = Run(
                text=run_text,
                bold=attrs.get("bold") == "true",
                italic=attrs.get("italic") == "true",
                underline=attrs.get("underline") == "true",
                family=attrs.get("family", "Calibri"),
                size=int(attrs["size"]) if "size" in attrs else None,
                is_space=is_space,
            )
            if current_para is None:
                current_para = Paragraph()
                doc.paragraphs.append(current_para)
            current_para.runs.append(run)

    return doc


def extract_text(path: str | Path) -> str:
    """Sadece düz metni döndürür (biçimlendirmesiz)."""
    return read_udf(path).text


def _build_content_xml(doc: UdfDocument) -> str:
    full_text_parts: list[str] = []
    elements_parts: list[str] = []
    offset = 0

    for para in doc.paragraphs:
        # Alignment yalnızca sola dayalı olmadığında yazılır (UYAP çıktılarında
        # 0 için öznitelik hiç konmuyor). LeftIndent/RightIndent de yazılmıyor.
        attrs = ""
        if para.alignment:
            attrs += f' Alignment="{para.alignment}"'
        if para.tabset:
            attrs += f' TabSet="{para.tabset}"'
        elements_parts.append(f"<paragraph{attrs}>")

        for run in para.runs:
            full_text_parts.append(run.text)
            length = len(run.text)
            tag = "space" if run.is_space else "content"
            run_attrs = ""
            if run.bold:
                run_attrs += ' bold="true"'
            if run.italic:
                run_attrs += ' italic="true"'
            if run.underline:
                run_attrs += ' underline="true"'
            if run.family:
                run_attrs += f' family="{escape(run.family)}"'
            if run.size:
                run_attrs += f' size="{run.size}"'
            run_attrs += f' startOffset="{offset}" length="{length}"'
            elements_parts.append(f"<{tag}{run_attrs} />")
            offset += length

        # UYAP her paragrafın sonuna CDATA içinde gerçek bir "\n" koyar ve
        # bunu da elements içinde length=1'lik bir content etiketiyle offsete
        # dahil eder. Bu olmadan belge editörde açılmıyor (sonsuz loading).
        full_text_parts.append("\n")
        elements_parts.append(f'<content startOffset="{offset}" length="1" />')
        offset += 1

        elements_parts.append("</paragraph>")

    full_text = "".join(full_text_parts)
    elements_xml = "".join(elements_parts)

    pf_attrs = " ".join(f'{k}="{v}"' for k, v in doc.page_format.items())

    # <styles> bloğu ZORUNLU. Bu olmadan UYAP Doküman Editörü dosyayı parse
    # edemiyor ve sonsuz "loading" ekranında kalıyor.
    styles_xml = (
        '<styles><style name="default" description="Geçerli" '
        'family="Lucida Grande" size="13" bold="false" italic="false" '
        'FONT_ATTRIBUTE_KEY="com.apple.laf.AquaFonts$DerivedUIResourceFont['
        'family=Lucida Grande,name=Lucida Grande,style=plain,size=13]" />'
        '<style name="hvl-default" family="Times New Roman" size="12" '
        'description="Gövde" /></styles>'
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        f'<template format_id="{doc.format_id}">\n'
        f"<content><![CDATA[{full_text}]]></content>\n"
        f"<properties><pageFormat {pf_attrs} /></properties>\n"
        f'<elements resolver="hvl-default">\n{elements_xml}\n</elements>\n'
        f"{styles_xml}\n"
        "</template>"
    )


def write_udf(doc: UdfDocument, path: str | Path) -> None:
    """UdfDocument nesnesini .udf (ZIP) dosyası olarak kaydeder.

    Not: Yeni yazılan dosyada e-imza (sign.sgn) olmaz — UYAP'ta açılabilir
    ama imzasız bir belge olarak görünür.
    """
    path = Path(path)
    content_xml = _build_content_xml(doc)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.xml", content_xml)


def text_to_udf(text: str, path: str | Path) -> None:
    """Düz metni (her satır bir paragraf) biçimsiz olarak .udf'ye kaydeder."""
    doc = UdfDocument()
    for line in text.split("\n"):
        doc.paragraphs.append(Paragraph(runs=[Run(text=line)] if line else []))
    write_udf(doc, path)


_ALIGN_PREFIX = {"[sol]": 0, "[orta]": 1, "[sağ]": 2, "[sag]": 2, "[iki]": 3}
_INLINE_RE = re.compile(
    r"\*\*(?P<b>.+?)\*\*"
    r"|__(?P<u>.+?)__"
    r"|(?<![\w*])\*(?=\S)(?P<i>.+?)(?<=\S)\*(?![\w*])"
)


def _parse_inline(line: str) -> list[Run]:
    runs: list[Run] = []
    pos = 0
    for m in _INLINE_RE.finditer(line):
        if m.start() > pos:
            runs.append(Run(text=line[pos:m.start()]))
        if m.group("b") is not None:
            runs.append(Run(text=m.group("b"), bold=True))
        elif m.group("u") is not None:
            runs.append(Run(text=m.group("u"), underline=True))
        else:
            runs.append(Run(text=m.group("i"), italic=True))
        pos = m.end()
    if pos < len(line):
        runs.append(Run(text=line[pos:]))
    return runs


def markup_to_doc(text: str) -> UdfDocument:
    """Basit işaretlemeli metni UdfDocument'e çevirir.

    - Her satır bir paragraf; boş satır boş paragraf.
    - Satır başı hizalama: [orta], [sağ], [iki] (iki yana yasla), [sol] (varsayılan).
    - Satır içi: **kalın**, *italik*, __altı çizili__.
    - Tab için gerçek tab karakteri ya da \\t yazılabilir.
    """
    doc = UdfDocument()
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.replace("\\t", "\t")
        align = 0
        for prefix, value in _ALIGN_PREFIX.items():
            if line.startswith(prefix):
                align = value
                line = line[len(prefix):].lstrip(" ")
                break
        doc.paragraphs.append(Paragraph(alignment=align, runs=_parse_inline(line) if line else []))
    return doc


def markup_to_udf(text: str, path: str | Path) -> None:
    write_udf(markup_to_doc(text), path)


def batch_extract_texts(folder: str | Path, pattern: str = "*.udf") -> dict[str, str]:
    """Bir klasördeki tüm .udf dosyalarının metnini {dosya_adı: metin} olarak döndürür."""
    folder = Path(folder)
    results: dict[str, str] = {}
    for udf_path in sorted(folder.glob(pattern)):
        try:
            results[udf_path.name] = extract_text(udf_path)
        except Exception as e:
            results[udf_path.name] = f"[HATA: {e}]"
    return results


if __name__ == "__main__":
    import sys

    usage = (
        "Kullanım:\n"
        "  python3 udf_tool.py <dosya.udf | klasör>        metni oku\n"
        "  python3 udf_tool.py yaz <girdi.txt | -> <çıktı.udf>   işaretlemeli metinden .udf yaz"
    )
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    if sys.argv[1] == "yaz":
        if len(sys.argv) != 4:
            print(usage)
            sys.exit(1)
        src = sys.stdin.read() if sys.argv[2] == "-" else Path(sys.argv[2]).read_text(encoding="utf-8")
        markup_to_udf(src, sys.argv[3])
        print(f"Yazıldı: {sys.argv[3]}")
        sys.exit(0)

    target = Path(sys.argv[1])
    if target.is_dir():
        texts = batch_extract_texts(target)
        for name, txt in texts.items():
            print(f"===== {name} =====")
            print(txt[:500])
            print()
    else:
        print(extract_text(target))
