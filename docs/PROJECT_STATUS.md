# English Master — Tình hình dự án

**Ngày cập nhật:** 2026-09-12
**Nhánh:** `feat/ai-only-m12-framework`  
**Phạm vi:** hệ thống học tiếng Anh tự học A1–C2, ưu tiên người học Việt Nam

## 1. Tóm tắt điều hành

English Master hiện là một pipeline Python offline-first, có thể tái lập và kiểm chứng bằng schema, validator, provenance, hash binding, immutable artifacts và các bài kiểm thử tự động. Dự án đã xây dựng phần lớn hạ tầng phát triển từ M0 đến M14, cùng các workstream curriculum **M15-KG-FULL**, **M16-A1-BLUEPRINT** và **M16-A2-BLUEPRINT**.

Các artifact phát triển hiện có không đồng nghĩa với nội dung đã được phát hành. Nội dung sinh ra vẫn giữ trạng thái `UNREVIEWED`; bằng chứng AI hoặc máy chỉ có thể thiết lập các tầng phát triển như `MACHINE_VALIDATED`, `AI_REVIEWED` và `DEVELOPMENT_APPROVED`. Không có tuyên bố về phê duyệt phát hành, quyền phân phối công khai, hay xử lý media thực tế khi các điều kiện tương ứng chưa đạt.

## 1.1. Workflow hiện hành

Routine development dùng **lightweight consistency audit**: kiểm tra tài liệu active, local implementation paths và các facts đã khai báo có bị lệch nhau hay không. Với code thay đổi, chạy các test local liên quan và `git diff --check`. Khi M9 được yêu cầu rõ ràng, chạy toàn bộ `python -m pytest` và direct-inspect năm lesson packets. Không cần human review, paid/live AI runner, full-population review batch, M10 closure hay release authority.

Một `M9 DEVELOPMENT: PASS` trong phạm vi sample cho phép bước được yêu cầu tiếp theo, nhưng không xác nhận chất lượng toàn bộ corpus, provider behavior hoặc quyền phân phối.

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
| M9 | Lightweight development QA sample — `PASS` | Báo cáo M9 đầu tiên `FAIL` được giữ nguyên; follow-up sau hai M10 successor repairs đã kiểm tra lại 5 lesson packets. Kết quả giới hạn theo sample; nội dung vẫn `UNREVIEWED`, nhưng M9 pass cho phép bước được yêu cầu tiếp theo. |
| M10 | Lightweight revision workflow và hai successor repairs đã có | M7 successor sửa giải thích matching A1; M8.2 v10 full pilot sửa B1 speaking feedback scope. Active workflow chỉ yêu cầu artifact kế nhiệm mới, ghi chú finding/hash predecessor và retest liên quan. |
| M11 | Local-batch exporter đã triển khai; chưa chạy một batch thật trong phiên đồng bộ này | `build-batch`/`verify-batch` xuất JSON, CSV, static web/mobile mặc định; print và IMS là tùy chọn. Không có M9/M10/release-authority gate. |
| M12 | Local-pilot manifest validator đã triển khai | Validator read-only kiểm tra 10–30 file local được liệt kê rõ, hash, source/license/attribution và permission. Chưa có media thật do người dùng cung cấp. |
| M13 | Local-pilot transcription API đã triển khai | Chọn 10–20 record từ M12 và dùng local ASR backend do caller cung cấp. Không bundled model, không download, không media/ASR thật trong repo. |
| M14 | Local metric tooling đã triển khai | Chỉ tính speech rate, vocabulary/grammar proxies, length và anonymous speaker count; không CEFR/composite. |
| M15-KG-FULL | Đã triển khai dưới dạng development population | Knowledge graph original-authored, 120 nodes, 12 tiers, typed prerequisites; không có lesson prose hay release authority. |
| M16-A1-BLUEPRINT | Đã triển khai dưới dạng outline-only blueprint | Blueprint A1.1/A1.2 gồm 10 units và 50 lesson outlines; không có lesson prose, exercises hay M6 authorization. |
| M16-A2-BLUEPRINT | Đã triển khai dưới dạng outline-only blueprint | Blueprint A2.1/A2.2 gồm 10 units, 50 lesson outlines, review lessons và unit-test blueprints; chỉ dùng M15 node/prerequisite references, không có authority bridge hay prose. |
| A1 pilot | Đã build development pilot 10 lesson A1.1 | Mỗi packet có lesson, exercises và 4 prompt modalities; hash/inventory/prerequisite checks pass. Review template được tạo nhưng chưa có user/AI review hoàn chỉnh, vì vậy nội dung vẫn `UNREVIEWED`. |
| Full A1 v2 | Đã build đủ 50 lesson A1.1/A1.2 | Allocation granular, 10 unit content files, 50 immutable packets, full-corpus lightweight audit `PASS`, và sample 12 lesson deterministic theo 10 unit. Giữ `UNREVIEWED`; không có human/release/provider/live-AI/network/media claim. |
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
- Local M11 batch export JSON/CSV/static web/static mobile, với schema/hash/path/source-permission/inventory checks; print/IMS là tùy chọn.
- Local M12 manifest validation, M13 caller-controlled ASR contract, và M14 basic transcript metrics. Các tool chưa xử lý media thật vì chưa có file/manifests/model path được cung cấp.
- Knowledge graph và A1 blueprint mới nhất để hỗ trợ quy hoạch nội dung, không thay thế M5 lịch sử và không tự động cấp quyền M6.

## 4. Các artifact nội dung hiện tại

- M5: architecture compact, outline-only; không phải toàn bộ khóa học 1.000+ giờ.
- M6: 10 lessons development-approved theo batch; lesson content vẫn `UNREVIEWED`.
- M7: 10 sets × 5 exercises = 50 exercises; stimulus là project-authored inline text và transcript-only listening.
- M8.2: 10 lessons × 4 modalities = 40 prompt artifacts.
- M15-KG-FULL: 120 graph nodes, phủ 12 internal tiers và các nhóm grammar, vocabulary senses, functions, pronunciation, discourse, pragmatics, collocations, lexical chunks, topics và skills.
- M16-A1-BLUEPRINT: A1.1/A1.2, 10 units, 50 lessons, mục tiêu và prerequisite/review mappings.
- M16-A2-BLUEPRINT: A2.1/A2.2, 10 units, 50 lesson outlines, review lessons, unit-test blueprints và M15 target coverage có kiểm chứng.
- Full A1 v2: 10 original-authored unit files build thành 50 canonical packets; audit deterministic chạy trên toàn corpus và sample 12 lesson được hash-rank, stratify theo unit.

Các con số trên là development fixtures/populations có giới hạn, không phải tuyên bố exhaustive coverage hay official CEFR endorsement.

## 5. Bước tiếp theo và điều kiện thực tế

1. Chạy integrated validation sau khi hoàn tất đồng bộ tài liệu/audit; không suy ra kết quả trước khi lệnh thực tế chạy.
2. Có thể tạo M11 local batch khi có input JSON hợp lệ với artifact paths, hashes và source permissions.
3. Chỉ chạy M12 real local-media pilot khi người dùng cung cấp 10–30 file licensed local cùng manifest có exact hashes.
4. Chỉ chạy M13 khi có subset M12 hợp lệ và local ASR backend/model path được chỉ rõ.
5. M14 sau đó chỉ phân tích transcript output bằng các metric đã công bố.

## 6. Giới hạn và vấn đề cần theo dõi

- M1 đã có implementation nhưng trạng thái/checklist trong tài liệu milestone cần đồng bộ rõ hơn.
- M9/M10 documents now distinguish the immutable historical findings from the active lightweight sample/revision flow.
- Integrated tests, Full A1 full-corpus consistency audit và project consistency audit đã pass; chưa có real-media pilot vì chưa có local inputs/model path được cung cấp.
- Không có corpus lớn, real-media corpus, ASR model download, network crawler hay dữ liệu `data/approved/` được tạo bởi các workstream hiện tại.
- M5 taxonomy/structure lịch sử và M15/M16 planning artifacts cần tiếp tục được giữ tách biệt khỏi quyền generate lesson và quyền publish.

## 7. Lần full-suite gần nhất được ghi nhận

Đã chạy:

```text
python -m pytest
```

Kết quả thực tế:

- **413 tests collected**
- **413 passed**
- Thời gian: **225.80 giây**
- Không có test failure trong lần chạy ngày 2026-09-12.

## 8. Kết luận

Dự án có development tooling từ M0 đến M16 planning workstreams. M9 lightweight sample follow-up đã ghi nhận `M9 DEVELOPMENT: PASS` trong phạm vi năm packet và cho phép bước được yêu cầu tiếp theo; nó không thay đổi trạng thái `UNREVIEWED`. M11 direct local-batch export cùng M12–M14 local-pilot tooling đã được thêm nhưng chưa có real-media run: cần integrated validation và, cho real processing, licensed local files/manifests cùng local ASR backend/model path. Dự án chưa tự động chuyển sang bất kỳ milestone nào hoặc public deployment.
