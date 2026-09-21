# Zabıt Katibi

Yapay zeka ajanlarının UYAP Doküman Editörü `.udf` dosyalarını okumasını ve UYAP'ta doğrudan açılabilen `.udf` dosyaları yazmasını sağlayan bir skill. Tek bağımlılık Python 3; ek kütüphane gerekmez.

## Kurulum

### Claude Code

```bash
git clone https://github.com/myyusuf17/zabit-katibi.git ~/.claude/skills/zabit-katibi
```

Sonra Claude'a örneğin "bu metni udf olarak kaydet" ya da "şu udf dosyasını özetle" demeniz yeterli. Skill kendiliğinden devreye girer; isterseniz `/zabit-katibi` ile de çağırabilirsiniz.

### Claude.ai (web / masaüstü / mobil)

Bu sayfadan **Code → Download ZIP** ile indirin ve Claude.ai'de **Ayarlar → Capabilities → Skills** bölümünden yükleyin. Kod çalıştırma özelliğinin açık olması gerekir.

### Diğer ajanlar (Codex, Gemini CLI, Cursor vb.)

Kod çalıştırabilen bir ajana şunu söyleyin:

> https://github.com/myyusuf17/zabit-katibi repo'sunu klonla, SKILL.md'yi oku ve ona göre çalış.

## Komut satırı

```bash
python3 scripts/udf_tool.py dosya.udf                 # tek dosyanın metnini oku
python3 scripts/udf_tool.py klasör/                   # klasördeki tüm .udf'leri oku
python3 scripts/udf_tool.py yaz belge.txt belge.udf   # işaretlemeli metinden .udf yaz
```

## İşaretleme

| Yazım | Sonuç |
|---|---|
| Her satır | Bir paragraf |
| Boş satır | Boş paragraf |
| `[orta] ...` / `[sağ] ...` / `[iki] ...` | Ortalı / sağa yaslı / iki yana yaslı |
| Önek yok veya `[sol] ...` | Sola dayalı |
| `**metin**` / `*metin*` / `__metin__` | Kalın / italik / altı çizili |
| Tab karakteri veya `\t` | Tab |

Örnek `belge.txt`:

```
[orta] **BAŞLIK**

[iki] Bu paragraf iki yana yaslıdır ve içinde *italik* bir ifade vardır.

[sağ] İmza
```

## Uyarılar

- Üretilen belgeler taslaktır; göndermeden önce içerik yönünden kontrol edilmelidir.
- E-imzalı bir `.udf` dosyası düzenlenip yeniden kaydedilirse imza geçersiz olur.

## Lisans

[MIT](LICENSE)
