# English Master — Tình hình dự án

**Ngày cập nhật:** 2026-09-11  
**Nhánh:** `feat/ai-only-m12-framework`  
**Phạm vi:** hệ thống học tiếng Anh tự học A1–C2, ưu tiên người học Việt Nam

## 1. Tóm tắt điều hành

English Master hiện là một pipeline Python offline-first, có thể tái lập và kiểm chứng bằng schema, validator, provenance, hash binding, immutable artifacts và các bài kiểm thử tự động. Dự án đã xây dựng phần lớn hạ tầng phát triển từ M0 đến M14, cùng hai nhánh công việc mới là **M15-KG-FULL** và **M16-A1-BLUEPRINT**.

Các artifact phát triển hiện có không đồng nghĩa với nội dung đã được phát hành. Nội dung sinh ra vẫn giữ trạng thái `UNREVIEWED`; bằng chứng AI hoặc máy chỉ có thể thiết lập các tầng phát triển như `MACHINE_VALIDATED`, `AI_REVIEWED` và `DEVELOPMENT_APPROVED`. Không có tuyên bố về phê duyệt phát hành, quyền phân phối công khai, hay xử lý media thực tế khi các điều kiện tương ứng chưa đạt.

## 2. Trạng thái theo milestone

| Milestone | Trạng thái hiện tại | Kết quả chính / giới hạn |
|---|---|---|
| M0 | Hoàn tất | Bootstrap repo, tài liệu, schema lõi, fixture và validator. |
| M1 | Artifact đã có; tài liệu trạng thái còn cần đồng bộ | Registry nguồn, license summary và chính sách nguồn đã được triển khai. |
| M2 | Hoàn tất | Taxonomy CEFR nội bộ, knowledge model, vocabulary senses, learner annotations và coverage matrix. |
| M3 | Hoàn tất | Ingestion pipeline offline, provenance, validation, deduplication và fixture adapter. |
| M4 | Hoàn tất | Normalization, raw/normalized hashes, exact groups, n-gram candidates và semantic-review queue. |
| M5 | Hoàn tất | Curriculum architecture, 12 internal tiers, dependency DAG, coverage roadmap và outline-only structure. |
| M6 | Hoàn tất cho development lane | 10 lesson bundles, authority-bound generation và AI linguistic/pedagogical evidence. Chưa phải release authority. |
| M7 | Hoàn tất cho AI-only development lane | 10 exercise sets, tổng 50 exercises; mọi exercise vẫn `UNREVIEWED`. |
| M8 / M8.2 | Hoàn tất cho development lane | QA engine sáu stage và pilot 40 AI-practice prompts trên bốn modality. |
| M9 | Framework development đã triển khai; full-population gate chưa đóng | Có independent-review contracts và representative-sample lane; cần batch v2 đầy đủ. |
| M10 | Framework và lineage đã triển khai; còn finding cần xử lý | Có immutable revision, retry và supersession machinery; một finding liên quan authority M5 còn escalated. |
| M11 | Framework export đã triển khai; chưa được authorize | Có JSON, CSV, mobile/web, print và IMS Common Cartridge renderers; chưa có export đủ authority để phát hành. |
| M12 | Preparation / fixture-only | Có controlled-media contracts và permission-aware checks; operational media ingestion bị chặn bởi gate M11. |
| M13 | Fixture-only hoàn tất | Có transcript/timestamp lineage, permission checks, anonymous speaker labels và verification. Chưa chạy ASR/media thật. |
| M14 | Fixture-only hoàn tất | Có listening-difficulty evidence đa chiều; không suy ra level chỉ từ vocabulary. Chưa có phân tích media thật. |
| M15-KG-FULL | Đã triển khai dưới dạng development population | Knowledge graph original-authored, 120 nodes, 12 tiers, typed prerequisites; không có lesson prose hay release authority. |
| M16-A1-BLUEPRINT | Đã triển khai dưới dạng outline-only blueprint | Blueprint A1.1/A1.2 gồm 10 units và 50 lesson outlines; không có lesson prose, exercises hay M6 authorization. |
| M15 platform / M16 deployment | Chưa bắt đầu | Đây là các milestone tương lai, khác với hai workstream KG/blueprint ở trên. |

> Tên M15/M16 hiện có hai ngữ cảnh: `M15-KG-FULL`/`M16-A1-BLUEPRINT` là workstream curriculum mới; M15 platform và M16 production deployment vẫn là các milestone tương lai riêng.

## 3. Những gì hệ thống đã có

- JSON Schema và semantic validation cho dữ liệu lõi, taxonomy, curriculum, generation, QA, media, transcription, listening evidence, knowledge graph và A1 blueprint.
- Source registry với trạng thái nguồn, license, attribution và operation-specific permission.
- Ingestion và normalization deterministic, lưu provenance và hash.
- Curriculum graph có prerequisite ordering, review edges và coverage theo dimension.
- Generation boundary cho lessons/exercises, với trusted metadata do orchestration chèn vào thay vì tin caller/provider.
- Immutable, atomic, no-overwrite publication cho bundles, reports, review evidence và run manifests.
- QA fail-closed: schema, answer, CEFR, prerequisite, duplicate và AI language QA theo thứ tự cố định.
- AI-practice pilot giới hạn listening, speaking, pronunciation và writing; prompt review chỉ kiểm tra protocol tĩnh, không chứng minh runtime provider behavior.
- Export framework nhiều định dạng nhưng chỉ hoạt động khi predecessor authority đầy đủ.
- Controlled media, transcript và listening-analysis frameworks có hash-bound lineage, nhưng chỉ ở fixture/development boundary.
- Knowledge graph và A1 blueprint mới nhất để hỗ trợ quy hoạch nội dung, không thay thế M5 lịch sử và không tự động cấp quyền M6.

## 4. Các artifact nội dung hiện tại

- M5: architecture compact, outline-only; không phải toàn bộ khóa học 1.000+ giờ.
- M6: 10 lessons development-approved theo batch; lesson content vẫn `UNREVIEWED`.
- M7: 10 sets × 5 exercises = 50 exercises; stimulus là project-authored inline text và transcript-only listening.
- M8.2: 10 lessons × 4 modalities = 40 prompt artifacts.
- M15-KG-FULL: 120 graph nodes, phủ 12 internal tiers và các nhóm grammar, vocabulary senses, functions, pronunciation, discourse, pragmatics, collocations, lexical chunks, topics và skills.
- M16-A1-BLUEPRINT: A1.1/A1.2, 10 units, 50 lessons, mục tiêu và prerequisite/review mappings.

Các con số trên là development fixtures/populations có giới hạn, không phải tuyên bố exhaustive coverage hay official CEFR endorsement.

## 5. Chuỗi gate còn lại

1. Hoàn tất một M9 development batch v2 cho full population, với machine evidence và AI review độc lập đầy đủ.
2. Đóng M10 lineage và xử lý finding/escalation còn tồn tại, không sửa artifact immutable tại chỗ.
3. Independently verify một M11 export được authorize từ authority đầy đủ.
4. Chỉ sau đó mới mở operational M12 cho media được cung cấp hợp pháp và có permission record cụ thể.
5. M13 operational cần M12 authority; M14 operational cần output M13 đã verify.
6. Các bước human/release, redistribution và public deployment là các gate riêng, không được suy ra từ kết quả máy hoặc AI.

## 6. Giới hạn và vấn đề cần theo dõi

- M1 đã có implementation nhưng trạng thái/checklist trong tài liệu milestone cần đồng bộ rõ hơn.
- M9/M10 documentation vẫn cần phản ánh chính xác hơn phần framework đã triển khai và phần gate chưa hoàn tất.
- README và MILESTONES có một số câu mô tả khác mức chi tiết về M12; cách hiểu đúng là preparation/fixture-only, không phải operational ingestion.
- Không có corpus lớn, real-media corpus, ASR model download, network crawler hay dữ liệu `data/approved/` được tạo bởi các workstream hiện tại.
- M5 taxonomy/structure lịch sử và M15/M16 planning artifacts cần tiếp tục được giữ tách biệt khỏi quyền generate lesson và quyền publish.

## 7. Kiểm thử xác nhận tại thời điểm cập nhật

Đã chạy:

```text
python -m pytest
```

Kết quả thực tế:

- **331 tests collected**
- **331 passed**
- Thời gian: **250.82 giây**
- Không có test failure trong lần chạy ngày 2026-09-11.

## 8. Kết luận

Dự án đã đạt mức **hạ tầng phát triển và validation khá đầy đủ**, với development lanes từ M0–M14 và các population/blueprint mới cho knowledge graph và A1. Tuy nhiên dự án **chưa ở trạng thái production/public release**: full-population M9/M10 evidence, authorized M11 export, operational media authority và các gate release tương ứng vẫn còn thiếu. Bước tiếp theo chỉ nên được thực hiện khi có yêu cầu milestone rõ ràng; không tự động chuyển sang M12 operational, M15 platform hoặc M16 deployment.
