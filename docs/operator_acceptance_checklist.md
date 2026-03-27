# Operatör Kabul Test Listesi (Manual Engineering Acceptance)

> Bu liste masaüstünde gerçek kullanımla doğrulanmalıdır.
> `python run.py` ile uygulamayı açın ve her maddeyi sırayla test edin.

---

## 1. Temel Açılış ve Stabilite

- [ ] Uygulama `python run.py` ile hatasız açılıyor
- [ ] Pencere başlığı "Jacquard CAD Professional" görünüyor
- [ ] Sol toolbar (Pencil, Eraser, Fill, Line, Rect, Select) görünüyor
- [ ] Sağ paneller (Palet, Doküman/Rapor, CAM Pipeline, İplik) yükleniyor
- [ ] Status bar X/Y/Zoom bilgisi gösteriyor

## 2. Çizim Araçları

- [ ] Pencil ile piksel çizilebiliyor
- [ ] Eraser ile piksel silinebiliyor (index 0)
- [ ] Fill ile alan dolduruluyor, sınırda durduruyor
- [ ] Line ile başlangıç-bitiş arasında çizgi çiziliyor
- [ ] Rect ile dikdörtgen çerçeve çiziliyor
- [ ] Select ile alan seçilebiliyor (sarı kesikli çerçeve)

## 3. Palet

- [ ] Palet panelinde 256 renk indeksi listeleniyor
- [ ] Renk tıklanınca aktif renk değişiyor (status bar'da görünür)
- [ ] Çift tıkla → QColorDialog açılıyor
- [ ] Renk değiştirince kanvas anında güncelleniyor

## 4. Navigasyon

- [ ] Mouse tekerleği ile zoom in/out
- [ ] Space + sol tık ile pan (sürükleme)
- [ ] Orta tuş ile pan
- [ ] Zoom > 5x'te point paper grid çizgileri belirginleşiyor
- [ ] 8'er piksellik kırmızı major grid çizgileri görünür mü

## 5. Kopyala/Yapıştır

- [ ] Select ile alan seç → Ctrl+C → kopyalandı
- [ ] Ctrl+V → floating patch (cyan kesikli çerçeve)
- [ ] Floating patch'i tıklayınca commit ediliyor
- [ ] Commit sonrası undo ile geri alınıyor

## 6. Undo/Redo

- [ ] Ctrl+Z ile son çizim geri alınıyor
- [ ] Ctrl+Y ile geri alınan çizim tekrar uygulanıyor
- [ ] 20+ ardışık undo/redo'da bozulma yok
- [ ] Fill → undo → redo zinciri tutarlı

## 7. CAM Pipeline (Kritik Akış)

Sırayla test edin:

- [ ] 1: Kanvasta desen çiz (en az 2 farklı renk)
- [ ] 2: CAM panelinden örgü seç (Bezayağı/Dimi/Saten)
- [ ] 3: "Aktif Renge Ata" → status "Örgü Atandı"
- [ ] 4: Select ile alan seç → "Seçimi Maske Yap" → region oluştu
- [ ] 5: "Aktif Bölgeye Ata" → region override çalışıyor
- [ ] 6: "Lift Plan Derle" → otomatik weave görünümüne geçti
- [ ] 7: Weave görünümünde siyah-beyaz lift plan doğru görünüyor
- [ ] 8: "Risk Analizi" → hata tablosu doldu (veya boş = temiz desen)
- [ ] 9: Hata varsa kanvasta kırmızı/turuncu overlay göründü

## 8. Mapping / Tahar

- [ ] Kanca sayısı spin box girişi çalışıyor
- [ ] "Özel Tahar Editörü" açılıyor
- [ ] Her tel için hook indeksi girilebiliyor
- [ ] -1 (dead hook) girilebiliyor
- [ ] "Çarpışma Testi" butonu doğru sonuç veriyor
- [ ] "Haritayı Kaydet" kapat sonrası status güncelleniyor

## 9. İplik ve Kumaş Simülasyonu

- [ ] İplik panelinden warp iplikleri ekleniyor (renk seçimi + tel sayısı)
- [ ] Weft iplikleri ekleniyor
- [ ] Faz (Phase X/Y) girişi yapılabiliyor
- [ ] "Kaydır" ile faz uygulanıyor, lift plan yeniden derleniyor
- [ ] "İplikleri Uygula & Kumaşı Gör" → fabric görünüme geçiş
- [ ] Kumaş simülasyonunda iplik renkleri doğru yansıyor

## 10. Görünüm Geçişleri (F5)

- [ ] F5 ile design → weave → fabric → design döngüsü
- [ ] Geçişlerde grid verisi bozulmuyor
- [ ] Weave modunda çizim engelleniyor (status mesajı)
- [ ] Fabric modunda çizim engelleniyor (status mesajı)

## 11. Export

- [ ] "Makineye Gönder" → dosya kaydet dialog
- [ ] Generic format seçili → .bin dosyası üretiliyor
- [ ] JC5 seçili → NotImplementedError mesajı (beklenen)
- [ ] Çıktı dosyası 0 byte değil

## 12. Dosya İşlemleri

- [ ] Ctrl+N → yeni proje (200×200 boş)
- [ ] Ctrl+S → .tcad kaydet dialog
- [ ] Ctrl+O → .tcad aç, eski desen yükleniyor
- [ ] Resim Import → RGB imaj 256 renge kuantize ediliyor
- [ ] Çıktı Export (PNG) → 8-bit indexed PNG

## 13. Autosave & Recovery

- [ ] 3+ dakika çalış → /tmp/tcad_recovery.tcad oluştu mu
- [ ] Uygulamayı kapat (kaydetmeden) → tekrar aç → "Kurtarma" sorusu
- [ ] "Evet" → eski desen geri yükleniyor
- [ ] "Hayır" → recovery dosyası siliniyor

## 14. Teknik Mod

- [ ] "Teknik B/W" toggle → siyah-beyaz görünüm
- [ ] Toggle kapatınca renkli görünüme dönüyor

## 15. Uzun Süreli Stabilite (1 saat)

- [ ] 1 saat sürekli kullanımda crash yok
- [ ] Hızlı zoom/pan'da donma yok
- [ ] 200+ undo/redo sonrası bozulma yok
- [ ] View mode geçişlerinde artefact yok

---

## Sonuç

| Geçen Madde | Kırılan Madde | Notlar |
|---|---|---|
| ___ / 50 | ___ / 50 | |

**Hüküm**: _________________________________
