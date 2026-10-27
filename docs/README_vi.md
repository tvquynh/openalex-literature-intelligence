# OpenAlex Literature Intelligence v3.0.5 Stable

> Bản tiếng Việt của README v3.0.5. Hướng dẫn đầy đủ bằng tiếng Anh: [USER_GUIDE.md](USER_GUIDE.md). Các đường dẫn file trong bản này tính từ thư mục gốc của repository.

Phiên bản: **3.0.5** · Trạng thái: **Stable** · Ngày phát hành: 2026-10-25 · Xem [`RELEASE_NOTES.md`](../RELEASE_NOTES.md) (tóm tắt bản phát hành) và [`CHANGELOG.md`](../CHANGELOG.md) (chi tiết).

## Công cụ làm gì (What does the tool do?)

- **OpenAlex discovery**: tìm paper theo query (một hoặc nhiều query), có cursor paging, resume và deduplicate theo DOI / OpenAlex ID.
- **SCImago enrichment**: so khớp venue với mirror SCImago 2010-2025 theo ISSN / ISSN-L, rồi mới đến title; title không bao giờ thắng khi ISSN mâu thuẫn.
- **Historical SJR / quartile**: SJR, Best Quartile và quartile theo category lấy đúng năm publication; không nội suy từ năm khác.
- **Latest source status**: `ACTIVE_LATEST` / `HISTORICAL_ONLY` / `UNMATCHED` / `AMBIGUOUS` theo snapshot SCImago mới nhất.
- **Journal screening**: main corpus mặc định = journal + `ACTIVE_LATEST`; có thể lọc thêm theo quartile, category, APC ước tính, DOAJ, CWTS Core.
- **Audit / reproducibility**: giữ nguyên raw corpus, ghi lý do loại từng paper, audit từng source, `summary.json`, `run_metadata.json` (phiên bản, policy, manifest, môi trường), SHA-256 cho mọi file SCImago.

Pipeline chính:

```text
OpenAlex discovery
    -> DOI / ISSN / source normalization
    -> SCImago remote repository sync + SHA-256 verification
    -> historical SJR / quartile at publication year
    -> latest SCImago status / quartile
    -> Journal Value / estimated APC snapshot
    -> venue screening
    -> raw + enriched + main + excluded + audit outputs
```

## Policy

- Main corpus mặc định: **journal only + `ACTIVE_LATEST`** (source có trong snapshot SCImago mới nhất). Raw/enriched không bị xóa, nên conference, repository, ebook, `HISTORICAL_ONLY`, `UNMATCHED`, `AMBIGUOUS` vẫn được giữ để audit.
- **SCImago presence must not be described as proof of current Scopus indexing.** Có trong SCImago (`in_scimago_latest=True`) không có nghĩa là đang được Scopus index.
- **SCImago absence must not be used to classify a venue as predatory.** Không có trong SCImago (`UNMATCHED`) không có nghĩa là predatory, bị Scopus loại hay chất lượng thấp.
- Matching: `ISSN_EXACT` > `ISSNL_EXACT` > `TITLE_EXACT` > `TITLE_NORMALIZED` > `TITLE_STATUS_NORMALIZED`. **Title fallback must not override an explicit ISSN conflict.**
- Paper năm sau snapshot mới nhất (hiện là 2026) không có quartile "năm 2026"; chỉ có metadata latest với `ranking_basis = LATEST_AVAILABLE`.

## Nguồn dữ liệu

- OpenAlex Works API: https://api.openalex.org/works
- OpenAlex API docs: https://help.openalex.org/api/
- OpenAlex cursor paging: https://help.openalex.org/api/paging/
- OpenAlex authentication: https://help.openalex.org/api/authentication/
- SCImago mirror manifest: https://scopus.cuatui.cloud/du-lieu/scimago/manifest.json
- SCImago mirror checksums: https://scopus.cuatui.cloud/du-lieu/scimago/SHA256SUMS.txt
- Original SCImago source: https://www.scimagojr.com/

## Yêu cầu

- Windows 11 / Linux / macOS
- Python 3.11+ khuyến nghị
- Internet cho OpenAlex và lần đầu đồng bộ SCImago
- OpenAlex API key: bắt buộc cho lệnh `run` (đặt trong `config.json`); `sync-scimago`, `validate-repo`, `enrich`, `inspect-source` không cần key

## Cài nhanh trên Windows 11

### 1. Cài Python

Tải Python chính thức từ:

https://www.python.org/downloads/windows/

Khi cài nhớ chọn `Add python.exe to PATH`.

Kiểm tra:

```powershell
python --version
python -m pip --version
```

### 2. Lấy mã nguồn

Clone repository (`git clone https://github.com/tvquynh/openalex-literature-intelligence.git C:\OpenAlexV3`) hoặc tải file ZIP mã nguồn ở trang Releases rồi giải nén vào một thư mục cố định, ví dụ:

```text
C:\OpenAlexV3\
```

Mở PowerShell:

```powershell
cd C:\OpenAlexV3
```

### 3. Tạo môi trường ảo

```powershell
python -m venv .venv
```

Nếu PowerShell cho phép script:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu bị lỗi `running scripts is disabled`, chỉ bypass cho phiên PowerShell hiện tại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Nếu máy công ty không cho activate venv, vẫn chạy trực tiếp:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe literature_pipeline.py --help
```

### 4. Cài dependency

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Cấu hình: `config.json` (chứa OpenAlex API key)

Từ v3.0.4 key và các thiết lập mặc định đặt trong file cấu hình riêng `config.json`, cùng thư mục với `literature_pipeline.py`:

```text
OpenAlexV3\
├── literature_pipeline.py
├── config.json             <- private, chứa API key thật (git-ignored, không bao giờ đóng gói)
├── config.example.json     <- public, không có key
├── .gitignore
├── requirements.txt
├── litintel\
└── cache\                  <- cache SCImago nếu dùng cache_dir mặc định của config.example.json
```

Tạo file từ mẫu rồi điền key:

```powershell
Copy-Item config.example.json config.json
notepad config.json
```

```json
{
  "openalex": { "api_key": "YOUR_OPENALEX_API_KEY", "email": "" },
  "scimago":  { "manifest_url": "https://scopus.cuatui.cloud/du-lieu/scimago/manifest.json", "cache_dir": "cache/scimago" },
  "run":      { "from_year": 2010, "to_year": 2026, "require_abstract": false, "max_per_query": null }
}
```

Thứ tự ưu tiên của mọi thiết lập:

```text
CLI argument  >  config.json  >  default trong code
```

- Chuỗi rỗng trong `config.json` nghĩa là "dùng default". `cache_dir` tương đối được tính theo thư mục chứa `config.json`.
- Có thể chỉ tới file khác bằng `--config <đường dẫn>`. Nếu không có `--config` và không có `config.json`, tool chạy bằng tham số CLI và default.
- File được kiểm tra chặt: section/khóa lạ hoặc sai kiểu dữ liệu đều báo `ERROR (config)` và dừng (exit 2). Thông báo lỗi không bao giờ in lại giá trị trong file.
- `run` cần key. Nếu không có key, tool dừng ngay trước mọi request với hướng dẫn tạo `config.json`. `sync-scimago`, `validate-repo`, `enrich`, `inspect-source` không cần key.
- `run_metadata.json` chỉ ghi `openalex_api_key_configured: true`, `openalex_api_key_source: "config.json"`, `openalex_api_key_stored_in_output: false` (cùng `config_file`, `settings_sources`), không bao giờ ghi giá trị key.
- Từ v3.0.5 code không còn email mặc định: `mailto` gửi cho OpenAlex lấy từ `--email` hoặc `openalex.email` trong `config.json`; để trống thì không gửi `mailto`.
- Tương thích ngược: `--api-key` (lộ trong shell history) và biến môi trường `OPENALEX_API_KEY` vẫn dùng được nhưng không khuyến khích; biến môi trường chỉ được dùng khi `config.json` không có key.

OpenAlex hiện yêu cầu API key để cursor paging qua trang đầu ở quy mô thực tế. Xem: https://help.openalex.org/api/authentication/

---

# Các lệnh chính

## 1. Đồng bộ và verify SCImago repository

```powershell
python literature_pipeline.py sync-scimago
```

Tool sẽ:

1. tải `manifest.json`;
2. tải `SHA256SUMS.txt`;
3. xác định các file SJR cần có;
4. kiểm tra cache local;
5. file đúng SHA-256 -> dùng lại;
6. file thiếu/sai hash -> tải lại;
7. verify SHA-256 sau download.

Cache mặc định:

```text
data\scimago\
```

Kiểm tra cache:

```powershell
python literature_pipeline.py validate-repo
```

## 2. Chạy test 100 paper

```powershell
python literature_pipeline.py run `
  --query "malware detection machine learning" `
  --from-year 2020 `
  --to-year 2026 `
  --require-abstract `
  --max-per-query 100 `
  --output test_malware
```

## 3. Chạy một query lớn hơn

```powershell
python literature_pipeline.py run `
  --query "malware detection machine learning" `
  --from-year 2010 `
  --to-year 2026 `
  --require-abstract `
  --max-per-query 3000 `
  --output malware_3000
```

## 4. Chạy nhiều query từ file

```powershell
python literature_pipeline.py run `
  --query-file examples\queries_example.txt `
  --from-year 2010 `
  --to-year 2026 `
  --require-abstract `
  --output PE_Malware_Research
```


### Policy source type mặc định

Không cần thêm `--source-type journal`: journal-only đã là mặc định. Nếu muốn giữ mọi loại source trong main corpus:

```powershell
python literature_pipeline.py run `
  --query "malware detection" `
  --all-source-types `
  --output malware_all_sources
```

Nếu muốn journal + conference/proceedings:

```powershell
python literature_pipeline.py run `
  --query "malware detection" `
  --source-type journal `
  --source-type "conference and proceedings" `
  --output malware_journal_conference
```

Raw/enriched corpus vẫn giữ tất cả source type; filter này chỉ quyết định `main.csv`.

## 5. Chỉ journal Q1/Q2 tại năm publication

```powershell
python literature_pipeline.py run `
  --query-file examples\queries_example.txt `
  --from-year 2010 `
  --to-year 2026 `
  --require-abstract `
  --source-type journal `
  --quartile Q1 `
  --quartile Q2 `
  --quartile-basis publication `
  --output PE_Malware_Q1_Q2
```

Lưu ý: paper năm 2026 chưa có SJR 2026 nên `quartile_at_publication` để trống. Nếu dùng filter publication-year quartile, các paper 2026 sẽ không qua filter Q1/Q2. Nếu muốn lọc bằng snapshot mới nhất, dùng `--quartile-basis latest`.

## 6. Lọc Q1/Q2 theo relevant category

Ví dụ với malware / security / software:

```powershell
python literature_pipeline.py run `
  --query-file examples\queries_example.txt `
  --from-year 2010 `
  --to-year 2026 `
  --require-abstract `
  --source-type journal `
  --quartile Q1 `
  --quartile Q2 `
  --quartile-mode relevant-category `
  --quartile-basis publication `
  --relevant-category "Computer Networks and Communications" `
  --relevant-category "Computer Science Applications" `
  --relevant-category "Software" `
  --relevant-category "Information Systems" `
  --output PE_Malware_CS_Q1_Q2
```

Tool giữ cả `SJR Best Quartile` và category-specific quartile; không ghi đè hai khái niệm này lên nhau.

Từ v3.0.4, `--relevant-category` so khớp **chính xác** tên category (không phân biệt hoa/thường và dấu câu). Bản trước so khớp chuỗi con nên `"Information Systems"` khớp nhầm `"Management Information Systems"`/`"Information Systems and Management"`, và `"Computer Networks and Communications"` khớp nhầm `"Communication"`. Hãy ghi đúng tên category như trong SCImago.

## 7. Lọc estimated APC

Ví dụ Q1/Q2 và estimated APC <= 500 USD:

```powershell
python literature_pipeline.py run `
  --query-file examples\queries_example.txt `
  --require-abstract `
  --source-type journal `
  --quartile Q1 `
  --quartile Q2 `
  --max-apc 500 `
  --output low_apc_q1_q2
```

`Estimated APC (USD)` là snapshot ước lượng của file Journal Value/APC, không phải APC lịch sử và không thay thế việc kiểm tra website publisher trước khi submit.

## 8. Chỉ DOAJ hoặc CWTS Core

```powershell
python literature_pipeline.py run `
  --query "malware detection" `
  --require-abstract `
  --require-doaj `
  --output malware_doaj
```

hoặc:

```powershell
python literature_pipeline.py run `
  --query "malware detection" `
  --require-abstract `
  --require-cwts-core `
  --output malware_cwts
```

Các cờ này dùng metadata source trả về bởi OpenAlex.

## 9. Giữ cả historical-only trong main corpus

Policy mặc định yêu cầu source còn có trong snapshot SCImago latest. Để nhận thêm source `HISTORICAL_ONLY` (có trong snapshot cũ, không có trong latest):

```powershell
python literature_pipeline.py run `
  --query-file examples\queries_example.txt `
  --include-historical-only `
  --output broad_corpus
```

Từ v3.0.4, cờ này chỉ thêm `HISTORICAL_ONLY`. Bản trước bỏ hẳn bộ lọc status nên `UNMATCHED` và `AMBIGUOUS` cũng lọt vào main corpus (corpus test 100 bài: 52 paper thay vì 26). Nếu thật sự muốn bỏ hẳn bộ lọc status như trước, dùng `--any-source-status`.

Raw/enriched corpus luôn giữ các record này dù main corpus mặc định loại.


## Audit/reporting (từ v3.0.2)

`summary.json` tách riêng:

- `paper_source_status_counts`: số paper theo `ACTIVE_LATEST/HISTORICAL_ONLY/UNMATCHED`;
- `unique_source_status_counts`: số unique source theo status;
- `paper_source_class_counts` và `unique_source_class_counts`: journal/conference/repository/ebook/no-source;
- `paper_source_status_by_class`: giúp biết `UNMATCHED` chủ yếu là conference/repository hay journal.

`source_audit.csv` có thêm `openalex_source_type`, `scimago_source_type`, `source_class`.

Khi OpenAlex dừng vì `--max-per-query`, checkpoint/summary dùng các trường rõ nghĩa:

```text
query_exhausted
stopped_by_limit
has_more_results
resume_available
run_completed_successfully
```

`stopped_by_limit=true` không phải lỗi; nó nghĩa là lần chạy hoàn tất đúng giới hạn và cursor đã được lưu để resume.

## 10. Enrich một corpus OpenAlex đã có sẵn

Nếu anh đã có CSV từ v1/v2:

```powershell
python literature_pipeline.py enrich `
  --input malware_1000.csv `
  --output malware_1000_v3
```

Hoặc JSONL:

```powershell
python literature_pipeline.py enrich `
  --input malware_1000.jsonl `
  --output malware_1000_v3
```

## 11. Xem lịch sử một journal

Theo title:

```powershell
python literature_pipeline.py inspect-source `
  --title "Journal of Information Security and Applications"
```

Theo ISSN:

```powershell
python literature_pipeline.py inspect-source `
  --issn 22142126
```

Tool in trajectory SJR/Q theo từng năm và APC snapshot nếu match được.

## 12. Offline mode

Sau khi đã sync và verify cache:

```powershell
python literature_pipeline.py validate-repo --offline
```

Enrich corpus không cần truy cập SCImago server:

```powershell
python literature_pipeline.py enrich `
  --offline `
  --input malware_1000.csv `
  --output malware_offline
```

Lệnh `run` vẫn cần Internet để query OpenAlex; `--offline` ở đây chỉ áp dụng repository SCImago.

## 13. Force tải lại SCImago

```powershell
python literature_pipeline.py sync-scimago --force-redownload
```

Hoặc trong full run:

```powershell
python literature_pipeline.py run `
  --query "malware detection" `
  --refresh-scimago `
  --output malware_refresh
```

## 14. Resume OpenAlex

Pipeline lưu:

```text
<output>_checkpoint.json
<output>_raw.jsonl
```

Nếu kết nối bị ngắt, chạy lại đúng command/output prefix để tiếp tục.

Nếu muốn bỏ toàn bộ state và chạy lại từ đầu:

```powershell
python literature_pipeline.py run ... --no-resume
```

Nếu thay đổi query/year/filter nhưng vẫn dùng cùng output prefix, nên dùng `--no-resume` hoặc đổi output prefix.

---

# Các output chính

Với `--output PE_Malware`, tool tạo:

```text
PE_Malware_raw.csv
PE_Malware_raw.jsonl
PE_Malware_checkpoint.json

PE_Malware_enriched.csv
PE_Malware_enriched.jsonl

PE_Malware_main.csv
PE_Malware_excluded.csv
PE_Malware_source_audit.csv

PE_Malware_summary.json
PE_Malware_run_metadata.json
```

| File | Nội dung |
|---|---|
| `_raw.csv` / `_raw.jsonl` | Mọi paper OpenAlex đã discovery (đã deduplicate), chưa enrich; luôn được giữ |
| `_checkpoint.json` | Trạng thái cursor để resume |
| `_enriched.csv` / `_enriched.jsonl` | Raw + toàn bộ metadata SCImago/APC, status, match method, chẩn đoán |
| `_main.csv` | Paper qua policy (mặc định journal + `ACTIVE_LATEST`) và các filter CLI |
| `_excluded.csv` | Paper bị loại, có cột `main_exclusion_reasons` |
| `_source_audit.csv` | Một dòng mỗi OpenAlex source: status, Sourceid, method, ứng viên, `match_diagnostic`, số paper |
| `_summary.json` | Số paper và số unique source theo status/class, method, quartile, ranking basis |
| `_run_metadata.json` | Phiên bản tool, query, policy, manifest SCImago, môi trường; key chỉ ghi `openalex_api_key_configured`/`openalex_api_key_source`, không bao giờ ghi giá trị |

`enrich` tạo các file `_enriched`, `_main`, `_excluded`, `_source_audit`, `_summary`, `_run_metadata` (không có `_raw`/`_checkpoint`).

### `raw`

Tất cả unique paper đã discovery từ OpenAlex, deduplicate theo:

1. DOI
2. OpenAlex ID
3. title + publication year

### `enriched`

Raw paper + SCImago/APC metadata.

Các field quan trọng:

```text
source_status
scimago_sourceid
latest_match_method
publication_match_method

sjr_year_at_publication
sjr_at_publication
best_quartile_at_publication
categories_at_publication
relevant_category_quartile_at_publication
ranking_basis

latest_scimago_year
in_scimago_latest
sjr_latest
best_quartile_latest
categories_latest
relevant_category_quartile_latest

estimated_apc_usd
estimated_value_usd
apc_data_year
```

### `main`

Paper qua policy hiện hành và các filter CLI bổ sung.

### `excluded`

Paper không qua main policy. Cột:

```text
main_exclusion_reasons
```

cho biết nguyên nhân cụ thể.

### `source_audit`

Một dòng cho mỗi OpenAlex source, gồm match status/method/candidate và số paper. Đây là file nên xem đầu tiên nếu tỷ lệ `UNMATCHED` hoặc `AMBIGUOUS` cao.

---

# Source status

```text
ACTIVE_LATEST
```

Source match được snapshot SCImago latest. Main corpus mặc định giữ.

```text
HISTORICAL_ONLY
```

Source match được ở một snapshot SCImago trước latest nhưng Sourceid đó không có trong latest snapshot (đúng định nghĩa trong `manifest.json`). Enriched giữ; main mặc định loại.

Từ v3.0.4 tool tìm theo hai bước: (1) snapshot đúng năm publication (`historical_match_method = PUBLICATION_YEAR_<method>`, có SJR/Q đúng năm); (2) nếu vẫn chưa match, mọi snapshot trước latest (`ANY_EARLIER_SNAPSHOT_<method>`, `historical_snapshot_years` ghi các năm tìm thấy). Bước (2) áp dụng cả cho paper năm 2026, paper ngoài 2010-2025 và năm mà source vắng mặt trong SCImago; khi đó SJR/Q tại năm publication vẫn để trống (`UNAVAILABLE`), không lấy từ năm khác. Bản v3.0.3 chỉ xét đúng năm publication nên các paper này bị ghi `UNMATCHED`, trong khi `inspect-source` ghi `HISTORICAL_ONLY`.

Nếu Sourceid tìm được qua lịch sử vẫn có trong latest snapshot (source đổi tên/ISSN), status là `ACTIVE_LATEST` với `latest_match_method = SOURCEID_VIA_PUBLICATION_YEAR_<method>` hoặc `SOURCEID_VIA_HISTORICAL_<method>`.

```text
UNMATCHED
```

Không match được bằng ISSN/ISSN-L/title ở bất kỳ snapshot nào. Riêng trạng thái này không có nghĩa là predatory, bị Scopus loại hay chất lượng thấp.

```text
AMBIGUOUS
```

Có hơn một candidate hợp lý. Tool không tự nhận bừa; candidates được ghi trong `latest_match_candidates`, `publication_match_candidates` hoặc `historical_match_candidates`.

# Match priority

```text
ISSN_EXACT
ISSNL_EXACT
TITLE_EXACT
TITLE_NORMALIZED
TITLE_STATUS_NORMALIZED
```

### ISSN mâu thuẫn chặn match theo title (v3.0.5)

| Tình huống | Kết quả |
|---|---|
| ISSN/ISSN-L của OpenAlex trùng ISSN của SCImago | match bằng `ISSN_EXACT` hoặc `ISSNL_EXACT` (luôn ưu tiên hơn title, kể cả khi title khác) |
| OpenAlex có ISSN, ứng viên title có ISSN nhưng không trùng | ứng viên bị loại; nếu mọi ứng viên bị loại thì `UNMATCHED`, `TITLE_MATCH_ISSN_CONFLICT`, không thử tiếp các mức title yếu hơn |
| OpenAlex không có ISSN hợp lệ | được dùng `TITLE_EXACT` > `TITLE_NORMALIZED` > `TITLE_STATUS_NORMALIZED` |
| Ứng viên SCImago không có ISSN | không tính là mâu thuẫn; title vẫn được dùng nếu duy nhất |
| Còn hơn một ứng viên | `AMBIGUOUS`, không tự chọn |

- Chỉ ISSN hợp lệ (7 chữ số + chữ số kiểm tra hoặc `X`) mới được tính là bằng chứng; chuỗi ISSN hỏng không chặn title.
- Khi chuẩn hóa title, `&` được hiểu là `and` (OpenAlex `Computers & Security` khớp SCImago `Computers and Security`); bản trước xóa `&` nên các title này không bao giờ khớp nếu thiếu ISSN.
- Quy tắc áp dụng như nhau cho snapshot latest, snapshot năm publication, mọi snapshot cũ và `inspect-source`.
- Cột mới `match_diagnostic` (`ISSN_CONFLICT`) và `issn_conflict_candidates` (Sourceid bị loại) có trong enriched, main/excluded và `source_audit.csv`; `summary.json` có `match_diagnostic_counts`.
- Đánh đổi: nếu OpenAlex chỉ ghi e-ISSN còn SCImago chỉ ghi print-ISSN của cùng tạp chí thì kết quả là `UNMATCHED` (có ghi `TITLE_MATCH_ISSN_CONFLICT` và Sourceid ứng viên để soát tay), thay vì có thể nhận nhầm một tạp chí khác.

`TITLE_STATUS_NORMALIZED` (mới ở v3.0.4, ưu tiên thấp nhất) bỏ nhãn trạng thái mà SCImago gắn vào cuối title, ví dụ `Mobile Information Systems (discontinued)`. Trong mirror hiện tại có 9.830 dòng (mọi năm) mang nhãn này, kể cả 132 source trong snapshot 2025.

Khi source đã match latest bằng Sourceid, lookup lịch sử ưu tiên `SOURCEID_HISTORY`. Nếu Sourceid đó không có ở năm publication, tool match theo ISSN/title trong năm đó như trước, nhưng ghi rõ Sourceid đã cung cấp số liệu vào `scimago_sourceid_at_publication` và đặt `publication_sourceid_differs = True` khi khác Sourceid định danh.

# Historical ranking policy

Paper 2010-2025:

```text
ranking_basis = EXACT_PUBLICATION_YEAR
```

nếu source có dữ liệu đúng năm đó.

Paper 2026 khi latest snapshot là 2025:

```text
sjr_at_publication = NA
best_quartile_at_publication = NA
ranking_basis = LATEST_AVAILABLE
```

Tool vẫn lưu `sjr_latest`/`best_quartile_latest`, nhưng **không gọi chúng là Q2026**. `LATEST_AVAILABLE` chỉ dùng khi source thật sự có metadata latest (`ACTIVE_LATEST`); paper 2026 có source `HISTORICAL_ONLY`/`UNMATCHED`/`AMBIGUOUS` được ghi `ranking_basis = UNAVAILABLE` (bản v3.0.3 ghi nhầm `LATEST_AVAILABLE` cho 12 paper như vậy trong corpus test 100 bài).

Nếu publication year nằm trong phạm vi SJR nhưng source không có dữ liệu đúng năm, hoặc paper không có publication year:

```text
ranking_basis = UNAVAILABLE
```

Tool không nội suy quartile từ năm khác.

## Quartile `-`, H-index và các trường audit mới

- SCImago xuất `-` khi một source không được gán quartile (123.121 dòng trong 16 file). Từ v3.0.4 giá trị này được lưu là rỗng, nên filter `--quartile` báo `QUARTILE_UNAVAILABLE` thay vì `QUARTILE_-_NOT_SELECTED`. Trong `summary.json`, `NOT_ASSIGNED` = có dòng SCImago nhưng không có quartile; `UNAVAILABLE` = không có dòng SCImago cho snapshot đó.
- `h_index_at_publication` được đọc từ đúng file năm publication, nhưng trong mirror hiện tại H-index của mọi source (32.193/32.193 source trong snapshot 2025) giống nhau ở mọi năm. Vì vậy hãy coi đây là H-index tại thời điểm xuất dữ liệu, không phải H-index lịch sử.
- Trường mới: `scimago_sourceid_at_publication`, `scimago_type_at_publication`, `publication_sourceid_differs`, `historical_match_method`, `historical_match_candidates`, `historical_snapshot_years`, `scimago_type_historical`, `scimago_discontinued_label_latest` (chỉ để tham khảo: SCImago tự gắn nhãn `(discontinued)` vào title; tool không dùng trường này để lọc).
- `source_audit.csv` tổng hợp trạng thái trên mọi paper của một source: `paper_status_counts` cho số paper theo status, `source_status = MIXED` nếu các paper của cùng source có status khác nhau. Mọi paper không có metadata source được gom vào một dòng `NO_SOURCE`.
- `enrich` cũng ghi `<output>_run_metadata.json` (phiên bản tool, SHA-256 của input, policy, manifest, môi trường).
- `enrich` xóa mọi cột enrichment/screening có sẵn trong input trước khi enrich, nên chạy lại trên `_enriched.csv` hoặc `_main.csv` cũ cho kết quả giống hệt chạy trên raw (bản v3.0.3 giữ lại giá trị `*_latest` cũ trên các dòng không còn `ACTIVE_LATEST`).
- Matching rule `TITLE_STATUS_NORMALIZED` và quy tắc ISSN mâu thuẫn chưa có trong `matching_policy` của `manifest.json` trên mirror. Client không đọc trường này, nên việc cập nhật chỉ là đồng bộ tài liệu trên server.

---

# SCImago cache integrity

Tool đọc `manifest.json`, sau đó `SHA256SUMS.txt`.

Mỗi file cache phải khớp SHA-256. Nếu sai hash:

- online -> tải lại và verify;
- offline -> dừng với lỗi integrity.

Nếu remote metadata tạm thời không truy cập được nhưng local `manifest.json` + `SHA256SUMS.txt` đã cache, tool có thể dùng metadata cache và các data file đã verify.

# Bảo mật

Xem [`SECURITY.md`](../SECURITY.md).

Không đưa API key vào:

- Python source;
- README;
- ZIP chia sẻ;
- Git repository;
- screenshot/log public.

# Hạn chế đã biết (Known limitations)

1. Kết quả tìm kiếm OpenAlex thay đổi theo thời gian (dữ liệu và thứ tự xếp hạng); search không tương đương hoàn toàn cú pháp Scopus/WoS.
2. Mirror SCImago hiện bao phủ 2010-2025.
3. Paper năm 2026 dùng metadata latest (2025) với `LATEST_AVAILABLE`, không phải "quartile 2026".
4. Độ phủ conference trong SCImago thay đổi nhiều giữa các năm; conference vắng mặt trong một năm không có nghĩa là bị Scopus loại.
5. Có trong SCImago không đồng nghĩa với trạng thái Scopus chính thức hiện tại; Q1/Q2 không phải nhãn predatory / non-predatory.
6. APC là giá ước tính theo snapshot 2025, không phải giá chính thức hay giá lịch sử của publisher.
7. Bảo vệ chống mâu thuẫn ISSN chấp nhận âm tính giả để tránh dương tính giả: nếu OpenAlex chỉ ghi e-ISSN còn SCImago chỉ ghi print-ISSN của cùng tạp chí thì kết quả là `UNMATCHED` (`TITLE_MATCH_ISSN_CONFLICT`, có ghi Sourceid ứng viên để soát tay).
8. H-index trong các file SCImago của mirror lặp lại giá trị hiện tại ở mọi năm, nên `h_index_at_publication` không phải H-index lịch sử.
9. Với systematic review, nên giữ raw discovery corpus và ghi rõ screening policy thay vì chỉ lưu main corpus.

# Kiểm thử

Kết quả kiểm thử của bản phát hành: xem [`TEST_REPORT.md`](../TEST_REPORT.md).

Kiểm thử offline (52 test; không cần Internet, không cần API key; dùng repository SCImago giả lập và server 127.0.0.1):

```powershell
python -m unittest discover -s tests -v
```

Kiểm tra bất biến độc lập trên một corpus đã enrich (đọc thẳng các file SCImago bằng `csv`, không dùng parser của tool):

```powershell
python literature_pipeline.py enrich --offline --input <raw.csv> --output out\default
python tools\check_reference_invariants.py cache\scimago <raw.csv> out\default default
```

(`cache\scimago` là thư mục cache khi dùng `config.json` tạo từ `config.example.json`; không có `config.json` thì mặc định là `data\scimago`.)


## Understanding SCImago sync messages

- `Local cache not found -> downloading from remote` means the file is not yet stored on this computer; it does **not** mean the remote dataset is missing.
- `OK - downloaded and SHA-256 verified` means the download succeeded and integrity matched `SHA256SUMS.txt`.
- `OK - local cache verified` means the existing local copy was reused after checksum verification.
- `Local cache checksum mismatch -> re-downloading from remote` means the local copy failed integrity validation and was replaced.

A successful sync ends with `integrity_verified: True` and an explicit `SUCCESS` message.
