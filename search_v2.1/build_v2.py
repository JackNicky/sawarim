import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "search_v2"
BOOKS_OUT_DIR = OUT_DIR / "books"
INDEX_OUT_DIR = OUT_DIR / "index_buckets"

# تعبير منتظم لإزالة التشكيل العربي
DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")
# تعبير منتظم لاستخراج الكلمات العربية والأرقام
WORD_RE = re.compile(r"[\u0600-\u06FF0-9]+")


def normalize_arabic(text: str) -> str:
    """توحيد الحروف العربية وإزالة التشكيل لتسهيل المطابقة الدقيقة."""
    if not text:
        return ""
    text = DIACRITICS_RE.sub("", text)
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي")
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")
    text = text.replace("ة", "ه")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_bucket_key(word: str) -> str:
    """تحديد اسم ملف الفهرس الفرعي بناءً على أول حرف من الكلمة."""
    if not word:
        return "misc"
    first_char = word[0]
    if "\u0600" <= first_char <= "\u06FF":
        return first_char
    if first_char.isdigit():
        return "num"
    return "misc"


def main() -> None:
    books_path = DATA_DIR / "books.json"
    if not books_path.exists():
        print("خطأ: لم يتم العثور على data/books.json")
        return

    with books_path.open("r", encoding="utf-8") as f:
        raw_books = json.load(f)

    # معالجة حالة وجود الكتب داخل قائمة واحدة
    if isinstance(raw_books, list) and len(raw_books) == 1 and isinstance(raw_books[0], list):
        books_list = raw_books[0]
    elif isinstance(raw_books, list):
        books_list = raw_books
    else:
        print("خطأ: بنية books.json غير متوقعة.")
        return

    BOOKS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_OUT_DIR.mkdir(parents=True, exist_ok=True)

    catalog_summary = []
    # قاموس الفهرس العكسي مقسّم حسب الحرف الأول: bucket -> word -> {book_id: [page_idx, ...]}
    buckets: dict[str, dict[str, dict[str, list[int]]]] = {}

    total_pages = 0
    total_books_done = 0

    for book in books_list:
        book_id = book.get("id")
        title = book.get("title", "")
        author = book.get("author", "")
        subtitle = book.get("subtitle", "")

        parts = book.get("parts")
        if parts and isinstance(parts, list):
            part_files = [p.get("file") for p in parts if p.get("file")]
        else:
            part_files = [f"book_{book_id}.json"]

        book_pages = []
        norm_title = normalize_arabic(title)

        for part_file in part_files:
            file_path = DATA_DIR / part_file
            if not file_path.exists():
                print(f"تنبيه: الملف {part_file} غير موجود وتم تجاوزه.")
                continue

            with file_path.open("r", encoding="utf-8") as pf:
                book_data = json.load(pf)

            for vol in book_data.get("volumes", []):
                vol_num = vol.get("volumeNumber")
                vol_title = vol.get("volumeTitle", "")

                for page in vol.get("content", []):
                    page_num = page.get("pageNumber")
                    chapter = page.get("chapter", "")
                    text = page.get("text", "")

                    page_index = len(book_pages)
                    book_pages.append({
                        "i": page_index,
                        "v": vol_num,
                        "vt": vol_title,
                        "p": page_num,
                        "c": chapter,
                        "t": text,
                    })

                    norm_chapter = normalize_arabic(chapter)
                    norm_text = normalize_arabic(text)

                    words = set(WORD_RE.findall(f"{norm_title} {norm_chapter} {norm_text}"))
                    b_key_str = str(book_id)

                    for w in words:
                        if len(w) < 2:
                            continue
                        bucket_name = get_bucket_key(w)
                        bucket = buckets.setdefault(bucket_name, {})
                        word_map = bucket.setdefault(w, {})
                        pages_for_book = word_map.setdefault(b_key_str, [])
                        pages_for_book.append(page_index)

        # حفظ صفحات هذا الكتاب في ملف مستقل لتقليل حجم التحميل عند البحث
        book_out_file = BOOKS_OUT_DIR / f"book_{book_id}.json"
        with book_out_file.open("w", encoding="utf-8") as bof:
            json.dump({
                "bookId": book_id,
                "title": title,
                "pages": book_pages,
            }, bof, ensure_ascii=False, separators=(",", ":"))

        catalog_summary.append({
            "id": book_id,
            "title": title,
            "author": author,
            "subtitle": subtitle,
            "pagesCount": len(book_pages),
            "file": f"books/book_{book_id}.json",
        })

        total_pages += len(book_pages)
        total_books_done += 1
        print(f"[{total_books_done}/{len(books_list)}] {title} -> {len(book_pages)} صفحة")

    # حفظ فهرس الكلمات العكسي مقسماً إلى ملفات صغيرة حسب الحرف
    bucket_files = {}
    unique_words_count = 0

    for bucket_name, word_map in sorted(buckets.items()):
        unique_words_count += len(word_map)
        safe_name = f"bucket_{ord(bucket_name)}.json" if len(bucket_name) == 1 else f"bucket_{bucket_name}.json"
        bucket_path = INDEX_OUT_DIR / safe_name
        with bucket_path.open("w", encoding="utf-8") as bkf:
            json.dump(word_map, bkf, ensure_ascii=False, separators=(",", ":"))
        bucket_files[bucket_name] = f"index_buckets/{safe_name}"

    manifest = {
        "version": 2,
        "totalBooks": len(catalog_summary),
        "totalPages": total_pages,
        "uniqueWords": unique_words_count,
        "books": catalog_summary,
        "buckets": bucket_files,
    }

    with (OUT_DIR / "manifest_v2.json").open("w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)

    print("\nتم بناء الفهرس المجزأ بنجاح!")
    print(f"عدد الكتب: {len(catalog_summary)}")
    print(f"إجمالي الصفحات المفهرسة: {total_pages}")
    print(f"إجمالي الكلمات الموحّدة الفريدة: {unique_words_count}")


if __name__ == "__main__":
    main()