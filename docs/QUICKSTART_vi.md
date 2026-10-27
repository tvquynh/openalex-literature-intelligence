# Quick Start - Windows 11 (OpenAlex Literature Intelligence v3.0.5 Stable)

```powershell
git clone https://github.com/tvquynh/openalex-literature-intelligence.git C:\OpenAlexV3
cd C:\OpenAlexV3
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Tạo file cấu hình riêng và điền key vào `openalex.api_key` (file này git-ignored và không bao giờ được đóng gói):

```powershell
Copy-Item config.example.json config.json
notepad config.json
```

Trong `config.json` sửa:

```json
"api_key": "YOUR_OPENALEX_API_KEY"
```

(có thể điền `"email"` để OpenAlex nhận `mailto`; không cần sửa source code).

Thứ tự ưu tiên: CLI argument > `config.json` > default trong code. Chỉ `run` cần key; thiếu key thì `run` dừng ngay và báo cách sửa.

Sync + verify SCImago:

```powershell
python literature_pipeline.py sync-scimago
python literature_pipeline.py validate-repo
```

Test 100 paper:

```powershell
python literature_pipeline.py run `
  --query "malware detection machine learning" `
  --from-year 2020 `
  --to-year 2026 `
  --require-abstract `
  --max-per-query 100 `
  --output test_malware
```

Full multi-query:

```powershell
python literature_pipeline.py run `
  --query-file examples\queries_example.txt `
  --from-year 2010 `
  --to-year 2026 `
  --require-abstract `
  --output PE_Malware_Research
```

Main corpus mặc định chỉ giữ **journal** còn có trong snapshot SCImago latest theo manifest. Dùng `--all-source-types` nếu muốn tắt journal-only; raw/enriched vẫn giữ toàn bộ source type.
