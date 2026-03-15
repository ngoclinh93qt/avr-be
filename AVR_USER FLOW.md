
# AVR — USER FLOW 
## Từ Số 0 Đến Bản Thảo: Trải Nghiệm Hoàn Chỉnh

**Cập nhật:** 2026-03  
**Persona:** Bác sĩ X — phẫu thuật nhi, có ý tưởng nghiên cứu lờ mờ, chưa từng publish quốc tế  
**Triết lý cốt lõi:** AVR là mentor nghiên cứu — không phải chatbot, không phải writing tool. Đường thẳng từ ý tưởng đến manuscript, không rẽ nhánh, không brainstorm hộ.

---

## TỔNG QUAN PIPELINE

```
Landing Page (Chọn bắt đầu hoặc quay lại project cũ)
     ↓
Phase 1 — Conversational Idea Engine
     ↓ Chat trái ←→ Blueprint phải (live update)
     ↓ Checkpoint: User confirm blueprint
     ↓ Novelty Check (PubMed scan)
     ↓ Generate Estimated Abstract
     ↓ Checkpoint: User confirm abstract
     ↓ Generate Research Roadmap
     ↓ Export Research Brief (PDF/Word)
     ↓
     ═══ GAP: User đi thu thập data (tuần → tháng) ═══
     ↓
Phase 2 — Submission Gate
     ↓ User paste abstract có data thật
     ↓ Constraint check Tier 0–4
     ↓ Integrity Score + Gate Decision
     ↓ Reviewer Simulation
     ↓ Guided Revision (sửa → chạy lại)
     ↓ Win moment khi READY
     ↓
Phase 3 — Full Manuscript Outline
     ↓ User chọn target journal
     ↓ Generate outline journal-specific
     ↓ Export → User viết manuscript
```

---

## MÀN HÌNH 0: LANDING PAGE

Bác sĩ X vào AVR lần đầu. Màn hình sạch, 2 lựa chọn rõ ràng.

**[Trải nghiệm người dùng — Lần đầu]:**  
X thấy một giao diện đơn giản, không overwhelm. Hai nút lớn. Không sidebar, không dashboard.

**[Trải nghiệm người dùng — Quay lại]:**  
X đã có project cũ. Phía dưới 2 nút chính, X thấy danh sách project dạng card. Click vào → vào thẳng project đó ở phase hiện tại.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│                          ✦ AVR — Research Mentor ✦                            │
│                                                                               │
│                    Bạn đang ở đâu trong nghiên cứu?                           │
│                                                                               │
│   ┌─────────────────────────────┐   ┌─────────────────────────────────────┐   │
│   │                             │   │                                     │   │
│   │  🌱 Tôi có ý tưởng /       │   │  📄 Tôi đã có abstract hoàn chỉnh   │   │
│   │     dữ liệu sơ bộ          │   │     (có data thật)                  │   │
│   │                             │   │                                     │   │
│   │  → Bắt đầu nhào nặn        │   │  → Vào thẳng Cửa ải kiểm duyệt    │   │
│   │    (Free — 3 lượt/ngày)     │   │    (Paid only)                     │   │
│   │                             │   │                                     │   │
│   └─────────────────────────────┘   └─────────────────────────────────────┘   │
│                                                                               │
│   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │
│   📁 Công trình của bạn                                                       │
│                                                                               │
│   ┌───────────────────────────────────────────────────────────────────────┐   │
│   │ 📂 Nội soi 1 lỗ vs 3 lỗ ruột thừa nhi                               │   │
│   │    Phase 2 · Điểm gần nhất: 72/100 · Cập nhật: 15/03/2026            │   │
│   ├───────────────────────────────────────────────────────────────────────┤   │
│   │ 📂 Siêu âm chẩn đoán lồng ruột                                      │   │
│   │    Phase 1 · Đang thu thập data · Cập nhật: 02/02/2026               │   │
│   └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Lưu ý UX:**
- Danh sách project chỉ hiện khi user đã có ít nhất 1 project.
- Mỗi card hiển thị: tên project (tự đặt hoặc auto từ research question), phase hiện tại, score gần nhất (nếu có), ngày cập nhật.
- Không dashboard, không chart, không analytics. Chỉ list card đơn giản.

**Lưu ý cho Dev:**
- Project = wrapper quanh ResearchSession hiện tại. Thêm 1 table `Project` (id, name, user\_id, created\_at, status). Mỗi project chứa 1+ session.
- API: `GET /api/v1/projects` → list projects. `POST /api/v1/projects` → tạo project mới.
- Khi user chọn "Tôi có ý tưởng" → tạo project mới → vào Phase 1.
- Khi user chọn "Tôi đã có abstract" → tạo project mới → vào Phase 2.
- Khi user click project cũ → load session gần nhất trong project đó.

---

## MÀN HÌNH 1: PHASE 1 — NHÀO NẶN Ý TƯỞNG (Chat)

Bác sĩ X chọn "Tôi có ý tưởng". Màn hình chia đôi: Chat trái, Blueprint phải.

**[Trải nghiệm người dùng]:**

1. X gõ: *"Tôi đang tính làm nghiên cứu về mổ ruột thừa bằng nội soi 1 lỗ so với 3 lỗ trên 50 bệnh nhi."*

2. Blueprint bên phải lập tức update — những field extract được sáng xanh, field chưa có hiện placeholder.

3. AVR phản hồi (mentor tone, không phải chatbot):  
	   *"50 bệnh nhi, so sánh 1 lỗ vs 3 lỗ — rõ rồi. Hai câu hỏi nhanh: Anh lấy từ hồ sơ cũ (hồi cứu) hay chuẩn bị thu thập từ giờ (tiến cứu)? Và anh dùng chỉ số gì để đánh giá — thời gian nằm viện, thang điểm đau VAS, hay tỷ lệ biến chứng?"*

4. X gõ: *"Hồi cứu hồ sơ năm ngoái. Đánh giá qua thời gian nằm viện."*

5. Blueprint update: tất cả field xanh. Trạng thái chuyển Complete.

**Lưu ý về Mentor Tone:** chỗ này cần prompt kĩ để nó thành mentor, không phán xét, cũng không cục súc  
- Ghi nhận trước, hỏi sau. Không block ngay câu đầu tiên.
- Hỏi đúng câu theo context — không hỏi lại thông tin user đã cung cấp.
- Gộp câu hỏi khi có thể (ví dụ trên: hỏi cả design lẫn endpoint trong 1 turn).
- Nếu user trả lời lơ mơ (ví dụ: "kết quả tốt hơn"), không block cứng mà hướng dẫn: *"'Tốt hơn' là khái niệm reviewer sẽ hỏi ngay — tốt hơn nghĩa là ít đau hơn (VAS)? Nằm viện ngắn hơn (ngày)? Ít biến chứng hơn (%)? Chọn 1 cái cụ thể làm primary endpoint."*
- Nếu user mô tả sai methodology (ví dụ: "RCT hồi cứu"), không chỉ block mà cho lựa chọn: *"RCT phải prospective — hồi cứu không randomize được. Ý anh có lẽ là: (A) Retrospective cohort — so sánh 2 nhóm từ hồ sơ cũ, hoặc (B) Before-after — so sánh trước và sau khi đổi kỹ thuật?"*

```text
┌──────────────────────────────────────┬────────────────────────────────────────┐
│          💬 Ý TƯỞNG CỦA BẠN          │         📋 RESEARCH BLUEPRINT          │
├──────────────────────────────────────┼────────────────────────────────────────┤
│                                      │                                        │
│ [Bạn]:                               │ 🟢 Câu hỏi NC: So sánh nội soi 1 lỗ   │
│ Tôi đang tính làm nghiên cứu mổ      │    vs 3 lỗ trong mổ ruột thừa nhi     │
│ ruột thừa nội soi 1 lỗ vs 3 lỗ       │ 🟢 Thiết kế: Hồi cứu (Retrospective)  │
│ trên 50 bệnh nhi.                    │    Confidence: HIGH ✓                  │
│                                      │ 🟢 Đối tượng: Bệnh nhi mổ ruột thừa   │
│ [AVR]:                               │    n = 50                              │
│ 50 bệnh nhi, so sánh 1 lỗ vs 3 lỗ.   │ 🟢 Kết cục chính: Thời gian nằm viện  │
│ — rõ rồi. Hai câu hỏi nhanh: Anh     │    Measurable: ✓ (ngày)               │
│ lấy từ hồ sơ cũ (hồi cứu) hay        │ 🟢 Dữ liệu: Hồ sơ bệnh án 2025      │
│ chuẩn bị thu thập từ giờ? Và anh     │                                        │
│ dùng chỉ số gì để đánh giá?          │ ──────────────────────────────────────  │
│                                      │ ⚠ Cỡ mẫu: 50 — đạt ngưỡng tối thiểu  │
│ [Bạn]:                               │   cho retrospective (≥30), nhưng nên   │
│ Hồi cứu hồ sơ năm ngoái. Đánh giá    │   cân nhắc power calculation.          │
│ qua thời gian nằm viện.              │                                        │
│                                      │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                      │ Trạng thái: ✅ COMPLETE                │
│ ┌──────────────────────────────────┐ │                                        │
│ │ Gõ câu trả lời...        [Gửi]   │ │ [📋 Xem Blueprint đầy đủ]             │
│ └──────────────────────────────────┘ │                                        │
└──────────────────────────────────────┴────────────────────────────────────────┘
```

---

### CHECKPOINT 1: Xác nhận Blueprint

Khi blueprint COMPLETE, AVR pause trước khi generate abstract.

**[Trải nghiệm người dùng]:**  
AVR tóm tắt blueprint bằng ngôn ngữ tự nhiên, hỏi user confirm. Đây là chỗ "lỏng" — user có quyền suy nghĩ lại trước khi đi tiếp. Không phải rẽ nhánh, chỉ là checkpoint.

```text
┌──────────────────────────────────────┬────────────────────────────────────────┐
│          💬 Ý TƯỞNG CỦA BẠN          │         📋 RESEARCH BLUEPRINT          │
├──────────────────────────────────────┼────────────────────────────────────────┤
│                                      │                                        │
│ [AVR]:                               │          (Blueprint đầy đủ             │
│ OK, mình tổng hợp lại:              │           như trên)                     │
│                                      │                                        │
│ Anh muốn so sánh mổ nội soi 1 lỗ   │                                        │
│ vs 3 lỗ ruột thừa trên 50 bệnh nhi, │                                        │
│ hồi cứu từ hồ sơ 2025, đo bằng     │                                        │
│ thời gian nằm viện.                  │                                        │
│                                      │                                        │
│ Hướng này ổn rồi, mình tạo bản      │                                        │
│ abstract dự kiến nhé? Nếu cần chỉnh │                                        │
│ gì, nói mình biết.                   │                                        │
│                                      │                                        │
│ ┌───────────────┐ ┌───────────────┐ │                                        │
│ │ ✅ OK, tiếp đi │ │ ✏ Chỉnh lại   │ │                                        │
│ └───────────────┘ └───────────────┘ │                                        │
│                                      │                                        │
└──────────────────────────────────────┴────────────────────────────────────────┘
```

**Logic:**
- "OK, tiếp đi" → Generate abstract + novelty check.
- "Chỉnh lại" → Quay về chat, user nói cần chỉnh gì. Blueprint update, loop lại checkpoint.
- Nếu user chỉnh nhiều hơn 2 lần → AVR nhẹ nhàng: *”Tôi thấy anh đang lăn tăn nhiều. Cứ chốt hướng chính trước, chi tiết có thể chỉnh sau khi có data."*

---

## MÀN HÌNH 2: PHASE 1 — KẾT QUẢ (Abstract + Novelty + Roadmap)

User confirm blueprint → AVR chạy 3 thứ: Novelty Check, Estimated Abstract, Research Roadmap.  
Cả 3 hiển thị trên panel phải, scroll xuống.

### 2A. Novelty Check

AVR search PubMed bằng keywords từ blueprint → hiển thị kết quả.

**[Trải nghiệm người dùng]:**  
X thấy ngay: đã có bao nhiêu bài tương tự, và 3–5 bài gần nhất. AVR không block — nhưng note rõ ràng để user biết cần differentiate ở đâu.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ 🔍 KIỂM TRA ĐỘ MỚI (NOVELTY CHECK)                                         │
│                                                                               │
│ Từ khóa: single-port vs multi-port appendectomy, pediatric, length of stay   │
│ Kết quả PubMed: ~38 bài tương tự                                             │
│                                                                               │
│ Gần nhất:                                                                    │
│ 1. Kim et al. (2024) — "Single-incision vs conventional laparoscopic         │
│    appendectomy in children: a meta-analysis" — J Pediatr Surg               │
│ 2. Nguyen et al. (2023) — "Single-port appendectomy in Vietnamese            │
│    children" — Pediatr Surg Int                                              │
│ 3. Park et al. (2023) — "Cosmetic outcomes of single-port vs multi-port      │
│    in pediatric surgery" — Surg Endosc                                       │
│                                                                               │
│ 💡 Nhận xét: Chủ đề đã có nhiều bài, nhưng chưa có data lớn từ Việt Nam     │
│ về thời gian nằm viện. Để tăng tính mới, anh có thể:                         │
│  · Focus vào population Việt Nam (healthcare setting khác)                   │
│  · Thêm secondary outcome chưa ai đo (ví dụ: chi phí điều trị)             │
│  · Thu hẹp age group (ví dụ: dưới 5 tuổi)                                   │
│                                                                               │
│ ⚠ Đây không phải lý do dừng — nhiều journal vẫn nhận replication study       │
│ từ population khác. Nhưng cần address novelty rõ trong Introduction.         │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Lưu ý cho Dev:**
- MVP: PubMed API search (Entrez E-utilities, miễn phí). Query = concat keywords từ blueprint.
- Trả về: count + top 5 results (title, authors, year, journal).
- Nhận xét do LLM generate dựa trên count + results + blueprint context. 1 call nhẹ.
- Nếu PubMed BigQuery available sau này → nâng cấp thành deeper analysis.

---

### 2B. Estimated Abstract

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ 📄 BẢN TÓM TẮT DỰ KIẾN (ESTIMATED ABSTRACT)                                │
│                                                                               │
│ BACKGROUND: Single-port laparoscopic appendectomy (SPA) has gained           │
│ popularity as an alternative to conventional three-port technique (CPA) in   │
│ pediatric patients. However, comparative data from Vietnamese healthcare     │
│ settings remain limited.                                                     │
│                                                                               │
│ OBJECTIVES: To compare length of hospital stay between SPA and CPA in        │
│ pediatric patients undergoing laparoscopic appendectomy.                     │
│                                                                               │
│ METHODS: A retrospective cohort study was conducted including 50 pediatric   │
│ patients who underwent laparoscopic appendectomy at [HOSPITAL] between       │
│ [DATE] and [DATE]. Patients were divided into SPA (n=[X]) and CPA (n=[X])   │
│ groups. The primary outcome was length of hospital stay (days).              │
│                                                                               │
│ RESULTS:                                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐   │
│ │  [PLACEHOLDER]                                                          │   │
│ │  Thu thập và phân tích dữ liệu trước khi điền phần này.                │   │
│ │  Cần báo cáo: mean LOS ± SD, p-value, 95% CI.                         │   │
│ └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ CONCLUSION: If the SPA group demonstrates shorter length of stay with        │
│ comparable complication rates, single-port technique may be a viable         │
│ alternative for pediatric appendectomy in Vietnamese surgical centers.       │
│                                                                               │
│ ─────────────────────────────────────────────────────────────────────────     │
│ 🎯 TOP 3 TẠP CHÍ PHÙ HỢP                                                  │
│                                                                               │
│ 1. Journal of Pediatric Surgery (Q1, IF 2.8)                                │
│    💰 Hybrid OA — có thể đăng miễn phí                                      │
│    📏 Abstract ≤ 250 từ | Vancouver | Blinded review                        │
│                                                                               │
│ 2. Pediatric Surgery International (Q2, IF 1.8)                              │
│    💰 Hybrid OA — có thể đăng miễn phí                                      │
│    📏 Abstract ≤ 250 từ | Vancouver                                         │
│                                                                               │
│ 3. Annals of Pediatric Surgery (Q4, IF 0.4)                                 │
│    💰 Diamond OA — miễn phí 100%                                             │
│    📏 Abstract ≤ 300 từ | Vancouver                                         │
│                                                                               │
│ ⚠ Luôn kiểm tra scope và yêu cầu trên website journal trước khi submit.    │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### CHECKPOINT 2: Xác nhận Abstract

**[Trải nghiệm người dùng]:**  
AVR hỏi nhẹ nhàng. Không phải "anh hài lòng chưa?" (giọng bán hàng), mà là mentor check:

```text
[AVR]:
Đây là bản abstract dự kiến dựa trên thông tin anh cung cấp.
Anh xem hướng nghiên cứu đã đúng ý chưa — nếu cần chỉnh,
mình quay lại blueprint. Nếu ổn, mình sẽ vẽ lộ trình nghiên cứu
để anh biết các bước tiếp theo.

  [ ✅ Hướng này ổn ]     [ ✏ Chỉnh hướng khác ]
```

**Logic:**
- "Hướng này ổn" → Generate Research Roadmap.
- "Chỉnh hướng khác" → Quay lại chat, chỉnh blueprint. Không generate abstract mới cho đến khi checkpoint 1 pass lại.

---

### 2C. Research Roadmap — Lộ trình nghiên cứu

Ngay sau khi user confirm abstract, AVR generate roadmap customize theo study design. Đây là giá trị mentor thực sự — không chỉ nói "đi thu thập data đi", mà vẽ ra từng bước cụ thể.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ 🗺 LỘ TRÌNH NGHIÊN CỨU CỦA BẠN                                              │
│ Design: Retrospective Cohort | Target: Journal of Pediatric Surgery          │
│                                                                               │
│ ━━━ Bước 1: Xin phê duyệt đạo đức (IRB/Ethics) ━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Hồi cứu thường được miễn informed consent, nhưng VẪN cần số phê duyệt.     │
│ 👤 Anh tự làm — liên hệ Phòng KHCN bệnh viện.                               │
│ ⏱ ~2–4 tuần                                                                  │
│                                                                               │
│ ━━━ Bước 2: Thiết kế bảng thu thập dữ liệu ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Dựa trên blueprint, anh cần thu thập:                                        │
│ · Tuổi, giới, cân nặng (baseline)                                            │
│ · Nhóm phẫu thuật (SPA vs CPA)                                              │
│ · Thời gian nằm viện — primary outcome                                      │
│ · Biến chứng (nếu có) — secondary outcome                                   │
│ 🔧 AVR sẽ hỗ trợ: Data Collection Form Generator (coming soon)              │
│ ⏱ ~1 tuần                                                                    │
│                                                                               │
│ ━━━ Bước 3: Thu thập dữ liệu ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Nguồn: Hồ sơ bệnh án 2025 tại [bệnh viện]                                   │
│ Lưu ý: Record cả missing data — đừng bỏ qua, report trong Results.          │
│ 👤 Anh tự làm — phần này không ai làm thay được.                             │
│ ⏱ ~2–6 tuần tùy cỡ mẫu                                                      │
│                                                                               │
│ ━━━ Bước 4: Phân tích thống kê ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Primary: So sánh LOS giữa 2 nhóm.                                           │
│ · Nếu data phân phối chuẩn → Independent t-test                             │
│ · Nếu không chuẩn → Mann-Whitney U                                          │
│ · Check normality bằng Shapiro-Wilk trước.                                  │
│ · Report: mean ± SD (hoặc median + IQR), p-value, 95% CI.                   │
│ 🔧 AVR sẽ hỗ trợ: Statistical Plan Builder (coming soon)                    │
│ ⏱ ~1–2 tuần                                                                  │
│                                                                               │
│ ━━━ Bước 5: Hoàn thiện Abstract → Chạy Gate ━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Điền data thật vào phần Results của abstract.                                │
│ Quay lại AVR → Phase 2 (Submission Gate) → Kiểm duyệt trước khi nộp.       │
│ 🔧 AVR: Submission Gate + Guided Revision                                    │
│ ⏱ ~1 tuần                                                                    │
│                                                                               │
│ ━━━ Bước 6: Viết full manuscript ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Sau khi Gate pass → AVR tạo khung sườn manuscript theo đúng journal format.  │
│ Anh "đắp thịt" vào khung, submit.                                           │
│ 🔧 AVR: Manuscript Outline Generator                                         │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ 📋 REPORTING CHECKLIST: STROBE (cho Observational study)                     │
│ AVR đã tạo checklist theo STROBE guideline cho nghiên cứu của anh.          │
│ [📥 Tải checklist STROBE]                                                    │
│                                                                               │
│ Tổng ước tính: ~8–14 tuần từ giờ đến submit                                  │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                               │
│   [📥 Tải Research Brief (PDF)]    [📥 Tải Research Brief (Word)]            │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Research Brief — file export gồm:**
1. Research Blueprint (tóm tắt)
2. Estimated Abstract
3. Novelty Check summary
4. Journal suggestions (top 3 + APC + format requirements)
5. Research Roadmap (các bước + timeline)
6. Reporting checklist (STROBE/CONSORT/STARD tùy design)

User tải về, in ra, dán bàn làm việc. Đồng nghiệp thấy → hỏi "lấy ở đâu?" → viral loop tự nhiên.

**Lưu ý cho Dev:**
- Roadmap là template theo `study_design`, populate bằng data từ blueprint. Không cần LLM call.
- Mỗi design có template riêng: retrospective (6 bước), RCT (8 bước, thêm registration + randomization), diagnostic (7 bước, thêm gold standard protocol), case series (5 bước, ngắn hơn).
- Checklist: STROBE cho observational, CONSORT cho RCT, STARD cho diagnostic accuracy — map 1:1 từ study\_design.
- Research Brief export: generate PDF/Word từ data đã có. 1 endpoint, không cần LLM.
- Skills "coming soon" hiện label nhưng chưa cần functional. MVP chỉ cần roadmap text + checklist download.

---

## ══════ GAP: User đi thu thập data ══════

*Tuần → tháng trôi qua. Bác sĩ X đi xin Ethics, lục hồ sơ, nhập data, chạy SPSS. Research Brief nằm trên bàn làm việc, giúp X biết mình đang ở bước nào.*

*Khi xong, X quay lại AVR.*

---

## MÀN HÌNH 3: RE-ENTRY — QUAY LẠI AVR

**[Trải nghiệm người dùng]:**  
X vào lại AVR → thấy project "Nội soi 1 lỗ vs 3 lỗ ruột thừa nhi" trong danh sách → click vào.

X thấy lại Research Brief cũ, nhắc context. Phía dưới có nút rõ ràng để bắt đầu Phase 2.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ 📂 Nội soi 1 lỗ vs 3 lỗ ruột thừa nhi                                      │
│ Tạo: 15/01/2026 | Phase 1 hoàn thành: 15/01/2026                            │
│                                                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐   │
│ │ 📋 Research Brief                                                       │   │
│ │ Design: Retrospective cohort | n=50 | Endpoint: Length of stay         │   │
│ │ Target: J Pediatr Surg (Q1) | Ped Surg Int (Q2) | Ann Ped Surg (Q4)  │   │
│ │                                                                         │   │
│ │ [📄 Xem lại Abstract]   [📥 Tải lại Research Brief]                    │   │
│ └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                               │
│   Anh đã có data thật? Paste abstract hoàn chỉnh vào đây để chạy            │
│   Cửa ải kiểm duyệt (Submission Gate).                                      │
│                                                                               │
│   ┌───────────────────────────────────────────────────────────────────┐       │
│   │                                                                   │       │
│   │   Dán abstract hoàn chỉnh (có data thật) vào đây...             │       │
│   │                                                                   │       │
│   │                                                                   │       │
│   └───────────────────────────────────────────────────────────────────┘       │
│                                                                               │
│   [▶ Chạy Gate]  (Paid feature — 199k–299k VNĐ/tháng)                       │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Lưu ý UX:**
- Phase 2 KHÔNG cần data từ Phase 1. User có thể paste abstract hoàn toàn mới — Gate chạy constraint check trên abstract hiện tại, không so sánh với estimated abstract cũ.
- Research Brief hiển thị ở đây chỉ để nhắc context, không phải input cho Gate.
- User vào thẳng Phase 2 (không qua Phase 1) cũng paste abstract vào form tương tự — chỉ không có Research Brief phía trên.

---

## MÀN HÌNH 4: PHASE 2 — CỬA ẢI KIỂM DUYỆT (Submission Gate)

User paste abstract → bấm "Chạy Gate" → hệ thống duyệt 3–5 giây.

### 4A. Kết quả Gate — Trường hợp REJECT

**[Trải nghiệm người dùng]:**  
X bấm "Chạy Gate". 5 giây. **REJECT**. Nhưng thay vì chỉ thấy điểm và danh sách lỗi lạnh lùng, X thấy một ông Reviewer khó tính đang nói chuyện thẳng thắn, chỉ rõ chỗ sai, cho cách sửa cụ thể. X click vào từng lỗi → Guided Revision mở ra hướng dẫn chi tiết.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                    ⚖ SUBMISSION GATE — KẾT QUẢ KIỂM DUYỆT                    │
│                                                                               │
│   KẾT QUẢ: 🔴 REJECT        ĐIỂM: 45/100                                    │
│   Lần chạy: 1                                                                │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ 🤖 MÔ PHỎNG REVIEWER (Q2/Q3):                                               │
│                                                                               │
│ "Nghiên cứu này có hướng đi hợp lý, nhưng nếu tôi là Reviewer #2, tôi sẽ   │
│ reject ngay vì 2 lỗi cơ bản mà bất kỳ reviewer nào cũng sẽ flag:"          │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ 🔴 FATAL — Fix trước mọi thứ:                                                │
│                                                                               │
│ ► [A-01] Primary outcome khai báo nhưng không báo cáo ← click để xem chi tiết│
│   Anh khai báo trong Methods là đo "length of stay", nhưng ở phần Results    │
│   toàn nói về lượng máu mất. Reviewer sẽ nghĩ: "Tác giả không biết mình    │
│   đang đo gì."                                                               │
│   → Sửa: Thêm "Mean LOS was X.X ± Y.Y days vs X.X ± Y.Y days (p=0.XX)"    │
│                                                                               │
│ 🟡 MAJOR — Fix trước khi nộp:                                                │
│                                                                               │
│ ► [St-01] Thiếu confidence interval                   ← click để xem chi tiết│
│   Tỷ lệ biến chứng 5% vs 10% — nhưng không có 95% CI hay p-value.          │
│   Reviewer không biết sự khác biệt này có ý nghĩa thống kê không.           │
│   → Sửa: Thêm "(95% CI: X–Y, p = Z)" sau mỗi kết quả chính.               │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ PRIORITY ACTION LIST:                                                        │
│ 1. [A-01] Bổ sung primary outcome vào Results ← quan trọng nhất             │
│ 2. [St-01] Thêm CI và p-value                                               │
│                                                                               │
│ Đây là chuyện bình thường — bài nào cũng vậy, không ai pass lần đầu.        │
│ Sửa từng lỗi, chạy lại Gate.                                                 │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                               │
│ ┌───────────────────────────────────────────────────────────────────┐         │
│ │  Dán abstract đã sửa vào đây...                                  │         │
│ └───────────────────────────────────────────────────────────────────┘         │
│ [▶ Chạy lại Gate]                                                            │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### 4B. Guided Revision — Click vào từng lỗi

User click vào issue code → panel mở ra hướng dẫn chi tiết. Đây là chỗ mentor giá trị nhất.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ 📖 HƯỚNG DẪN SỬA: [A-01] Primary Outcome Missing in Results                 │
│                                                                               │
│ ━━━ TẠI SAO REVIEWER FLAG? ━━━                                               │
│ Khi Methods nói đo "length of stay" nhưng Results không báo cáo con số đó,  │
│ reviewer sẽ nghi ngờ: (1) tác giả quên, (2) kết quả không tốt nên giấu,    │
│ hoặc (3) nghiên cứu không được thực hiện đúng protocol. Cả 3 đều dẫn đến   │
│ reject.                                                                       │
│                                                                               │
│ ━━━ CÁCH SỬA ━━━                                                             │
│ Thêm vào đầu phần Results, ngay sau demographic:                             │
│                                                                               │
│ "The mean length of hospital stay was [X.X ± Y.Y] days in the SPA group     │
│ compared with [X.X ± Y.Y] days in the CPA group (mean difference: [X.X]     │
│ days; 95% CI: [X.X–Y.Y]; p = [0.XX])."                                      │
│                                                                               │
│ ━━━ VÍ DỤ TỪ BÀI ĐÃ ĐƯỢC CHẤP NHẬN ━━━                                     │
│ "The median LOS was 2 (IQR 1–3) days in the single-port group versus        │
│  3 (IQR 2–4) days in the three-port group (p = 0.02)."                      │
│                                                                               │
│                                                  [← Quay lại Gate Result]    │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### 4C. Revision Tracking — Chạy lại Gate

User sửa abstract → paste lại → chạy Gate lần 2.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                    ⚖ SUBMISSION GATE — KẾT QUẢ KIỂM DUYỆT                    │
│                                                                               │
│   KẾT QUẢ: ✅ READY          ĐIỂM: 88/100                                    │
│   Lần chạy: 2                                                                │
│                                                                               │
│   ━━━ LỊCH SỬ ━━━                                                            │
│   Lần 1:  🔴 REJECT          45/100   │ Fatal: 1  Major: 1  Minor: 0        │
│   Lần 2:  ✅ READY            88/100   │ Fatal: 0  Major: 0  Minor: 1        │
│                                                    ▲ +43 điểm                │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                               │
│   🎉 Abstract của anh đã đạt chuẩn nộp tạp chí Q2/Q3.                       │
│   Từ 45 điểm lên 88 điểm sau 2 lần chỉnh sửa — đó là tiến bộ thật.         │
│                                                                               │
│   🔵 MINOR (không ảnh hưởng accept, nên sửa nếu có thời gian):              │
│   [St-01] Secondary outcome chưa có CI — thêm thì hoàn hảo hơn.            │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                               │
│   Bước tiếp: Chọn tạp chí mục tiêu để tạo khung sườn manuscript.            │
│                                                                               │
│   ○ Journal of Pediatric Surgery (Q1, IF 2.8) — Hybrid OA                   │
│   ○ Pediatric Surgery International (Q2, IF 1.8) — Hybrid OA                │
│   ○ Annals of Pediatric Surgery (Q4, IF 0.4) — Free                         │
│                                                                               │
│   [▶ Tạo khung sườn Manuscript]                                              │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Lưu ý UX — "Win Moment":**
- Khi Gate chuyển từ REJECT → READY: celebration rõ ràng. Không cần confetti, nhưng cần acknowledge effort: hiển thị delta điểm, số lần chỉnh sửa, tiến bộ cụ thể.
- Score history visualization đơn giản (text-based như trên, không cần chart) — user thấy mình tiến bộ.
- Dòng "đó là tiến bộ thật" — mentor acknowledge, không phải chatbot khen.

---

## MÀN HÌNH 5: PHASE 3 — KHUNG SƯỜN MANUSCRIPT

User chọn journal → AVR generate outline journal-specific. 1 LLM call.

**[Trải nghiệm người dùng]:**  
X chọn "Journal of Pediatric Surgery". AVR nhả ra khung sườn bám sát 100% submission guidelines của JPS. X tải về Word, mở ra, viết theo từng ô.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│              📝 KHUNG SƯỜN MANUSCRIPT — READY TO WRITE                        │
│                                                                               │
│ 🏛 Journal: Journal of Pediatric Surgery (Q1, IF 2.8)                        │
│ 📏 Giới hạn: ~3000 từ nội dung | ≤ 6 hình/bảng | Vancouver                 │
│ 📐 Format: Double-spaced, 12pt, blinded review (trang bìa riêng)             │
│                                                                               │
│ ━━━ TITLE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Target: 15–20 từ                                                              │
│ Gợi ý: "Single-Port Versus Three-Port Laparoscopic Appendectomy in          │
│ Pediatric Patients: A Retrospective Comparative Study"                       │
│ ⚠ JPS không cho abbreviation trong title.                                    │
│                                                                               │
│ ━━━ TITLE PAGE (File riêng — blinded review) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ⚠ JPS yêu cầu ẩn danh. Title page KHÔNG ĐƯỢC để chung file nội dung.        │
│ □ Title                                                                      │
│ □ Authors + affiliations                                                     │
│ □ Corresponding author + email                                               │
│ □ Word count                                                                 │
│ □ Number of figures/tables                                                   │
│                                                                               │
│ ━━━ ABSTRACT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ✅ Dùng abstract đã pass Gate.                                                │
│ 📏 ≤ 250 từ | Sections: Background, Methods, Results, Conclusion             │
│ 🔵 Minor issue còn: [St-01] thêm CI ở secondary outcome thì hoàn hảo hơn.  │
│                                                                               │
│ ━━━ INTRODUCTION (~400 từ) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ □ Đoạn 1: Bối cảnh — mổ nội soi ruột thừa ở trẻ em, xu hướng minimally     │
│   invasive.                                                                   │
│ □ Đoạn 2: Literature gap — tranh cãi single-port vs multi-port, thiếu data  │
│   từ Việt Nam (cite novelty check: ~38 bài nhưng chưa có VN data lớn).     │
│ □ Đoạn 3: "The aim of this study was to compare the length of hospital      │
│   stay between single-port and three-port laparoscopic appendectomy          │
│   in pediatric patients at a Vietnamese tertiary center."                    │
│ 📚 Cần cite ≥ 10 references trong Introduction.                              │
│                                                                               │
│ ━━━ METHODS (~800 từ) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ □ Study Design & Setting: "A retrospective cohort study was conducted at     │
│   [Hospital], [City], Vietnam, between [dates]."                             │
│ □ Participants:                                                               │
│   □ Inclusion: Bệnh nhi mổ ruột thừa nội soi tại [BV] trong [năm]          │
│   □ Exclusion: Chuyển mổ mở, bệnh lý kèm nặng, hồ sơ thiếu data           │
│ □ Surgical Technique: Mô tả kỹ thuật SPA và CPA tại bệnh viện anh          │
│ □ Outcomes:                                                                   │
│   □ Primary: Length of hospital stay (days)                                  │
│   □ Secondary: Complications, operative time (nếu có)                        │
│ □ Statistical Analysis:                                                       │
│   □ Software + version (SPSS/R/Stata)                                        │
│   □ Mann-Whitney U hoặc Independent t-test (check normality trước)           │
│   □ p < 0.05 là có ý nghĩa                                                  │
│ □ Ethical Approval: "This study was approved by [IRB] (approval no. [X])."   │
│                                                                               │
│ ━━━ RESULTS (~800 từ) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ □ Participant flow: 50 bệnh nhi, SPA n=[X], CPA n=[X]                       │
│ □ Table 1: Baseline characteristics (tuổi, giới, BMI, ASA score)             │
│ □ Primary outcome: LOS với 95% CI và p-value                                │
│ □ Secondary outcomes (nếu có)                                                │
│ □ Complications: liệt kê cụ thể                                              │
│                                                                               │
│ ⚠ Statistical reporting checklist:                                            │
│ □ Tất cả kết quả chính có 95% CI                                             │
│ □ Exact p-values (viết p = 0.03, không viết p < 0.05)                        │
│ □ Absolute numbers kèm percentages                                           │
│                                                                               │
│ ━━━ DISCUSSION (~900 từ) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ □ Đoạn 1: "In this study, we found that..." — nhắc lại kết quả chính       │
│ □ Đoạn 2: So sánh với literature (cite bài từ novelty check)                │
│ □ Đoạn 3: Clinical implications                                              │
│ □ Đoạn 4: Limitations — ít nhất 3, trung thực:                               │
│   · Retrospective design → selection bias                                    │
│   · Single-center → limited generalizability                                 │
│   · Small sample size (n=50) → risk of type II error                         │
│ □ Đoạn cuối: "In conclusion, ..." (KHÔNG overclaim)                          │
│                                                                               │
│ ━━━ LEVEL OF EVIDENCE (Bắt buộc của JPS) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ⚠ Ghi dòng này cuối bài:                                                    │
│ "Level of Evidence: Level III, Retrospective comparative study."             │
│                                                                               │
│ ━━━ REFERENCES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Format: Vancouver | Limit: ≤ 40 references                                   │
│ Tool: Zotero (cài CSL: [link]) hoặc Mendeley                                │
│                                                                               │
│ ━━━ FIGURES & TABLES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Limit: ≤ 6 hình + bảng gộp                                                  │
│ □ Table 1: Baseline characteristics                                          │
│ □ Table 2: Surgical outcomes (LOS, operative time, complications)             │
│ □ Figure 1: Patient selection flowchart (optional, khuyến khích)             │
│                                                                               │
│ ━━━ SUBMISSION CHECKLIST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ □ Abstract ≤ 250 từ, structured                                              │
│ □ Manuscript double-spaced, 12pt font                                        │
│ □ Title page file riêng (blinded)                                            │
│ □ Figures/tables có title + legend                                           │
│ □ References đúng Vancouver format                                           │
│ □ STROBE checklist đính kèm                                                  │
│ □ Cover letter                                                                │
│ □ Author contributions (CRediT format)                                       │
│ □ Conflict of interest statement                                              │
│ □ Ethics approval number                                                      │
│ □ Data availability statement                                                │
│ □ Level of Evidence statement                                                │
│                                                                               │
│ ━━━ GHI CHÚ CHO TÁC GIẢ (TIẾNG VIỆT) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ · Introduction: Viết ngắn, mỗi claim phải có citation. Không cần review     │
│   toàn bộ lịch sử — chỉ nêu gap.                                            │
│ · Methods: Phần dễ nhất — kể lại anh đã làm gì, theo thứ tự thời gian.     │
│ · Discussion: Phần khó nhất — đừng lặp lại Results. So sánh với bài khác,  │
│   giải thích tại sao giống/khác.                                             │
│ · Limitations: Viết trung thực. Reviewer biết anh biết điểm yếu =          │
│   tăng credibility.                                                          │
│                                                                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                               │
│   [📥 Tải Manuscript Outline (Word)]   [📥 Tải STROBE Checklist]            │
│                                                                               │
│   🎯 Anh có outline + checklist + abstract đã validated.                     │
│   Mở Word, viết theo khung, submit. Chúc anh publish thành công.            │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## TÓM TẮT: NGUYÊN TẮC THIẾT KẾ TRẢI NGHIỆM

### Triết lý Mentor — Không phải chatbot, không phải chấm bài

| Tình huống               | ❌ Không làm                                   | ✅ Làm                                                                                                             |
| ------------------------ | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| User nói ý tưởng lờ mờ   | "Anh muốn làm đề tài nào?" (brainstorm hộ)    | "50 bệnh nhi, so sánh 2 kỹ thuật — rõ rồi. Hỏi thêm 2 câu nữa." (cấu trúc hóa)                                    |
| User sai methodology     | "BLOCK: RCT hồi cứu không tồn tại." (máy nói) | "RCT phải prospective. Ý anh có lẽ là retrospective cohort hoặc before-after?" (dẫn dắt)                          |
| User viết endpoint mơ hồ | "F-02: Endpoint chưa measurable." (code lỗi)  | "'Kết quả tốt hơn' — reviewer sẽ hỏi: tốt hơn nghĩa là gì? Chọn 1 con số cụ thể." (giải thích tại sao + cách sửa) |
| Gate reject              | Chỉ list lỗi                                  | "Bài nào cũng vậy, không ai pass lần đầu. Sửa 2 chỗ này, chạy lại." (normalize + action)                          |
| Gate pass                | Tick xanh im lặng                             | "Từ 45 lên 88 điểm sau 2 lần sửa — đó là tiến bộ thật." (acknowledge effort)                                      |

### Đường thẳng — Có checkpoint, không có ngã rẽ

```
Idea → [Checkpoint: Blueprint OK?] → [Novelty Check] → Abstract → [Checkpoint: Hướng OK?]
→ Roadmap → Export Brief → [GAP: thu thập data] → Gate → [Revision loop] → Win → Outline
```

- Checkpoints cho user thở, suy nghĩ, điều chỉnh — nhưng luôn quay về đường chính.
- Revision loop là loop duy nhất trong toàn pipeline: sửa → chạy lại → sửa → chạy lại. Mỗi lần đều full constraint check từ đầu (R-11).
- Không rẽ nhánh, không gợi ý đề tài mới, không brainstorm.

### TÓM LẠI: Hội thoại là đường thẳng

AVR là mentor cầm form 5 ô trống. User ném ý tưởng lộn xộn → mentor tách ra, điền ô, hỏi tiếp ô thiếu, ép trả lời chuẩn nếu sai. Đủ 5 ô → đi thẳng tới abstract. **Tuyệt đối không rẽ nhánh, không sáng tạo đề tài cho user.**

Ngoại lệ duy nhất: khi có ambiguity cần disambiguation (ví dụ: "RCT hồi cứu" → đưa 2 lựa chọn cụ thể). Đây không phải brainstorm — chỉ là hỏi rõ intent của user.

---
