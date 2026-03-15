"""
Research Roadmap Generator — template-based, no LLM required.

Maps study design to a step-by-step research roadmap with timeline estimates.
Checklist type is mapped 1:1 from study design (STROBE/CONSORT/STARD/PRISMA/CARE).
"""

from app.models.enums import DesignType
from app.models.schemas import ResearchBlueprint, ResearchRoadmap, RoadmapStep


# ─── Checklist mapping ────────────────────────────────────────────────────────

_CHECKLIST_MAP: dict[str, str] = {
    DesignType.RCT.value:                  "CONSORT",
    DesignType.QUASI_EXPERIMENTAL.value:   "CONSORT",
    DesignType.BEFORE_AFTER.value:         "CONSORT",
    DesignType.DIAGNOSTIC_ACCURACY.value:  "STARD",
    DesignType.SYSTEMATIC_REVIEW.value:    "PRISMA",
    DesignType.META_ANALYSIS.value:        "PRISMA",
    DesignType.SCOPING_REVIEW.value:       "PRISMA",
    DesignType.CASE_REPORT.value:          "CARE",
    DesignType.CASE_SERIES.value:          "CARE",
    # Observational (default STROBE)
    DesignType.COHORT_RETROSPECTIVE.value: "STROBE",
    DesignType.COHORT_PROSPECTIVE.value:   "STROBE",
    DesignType.CASE_CONTROL.value:         "STROBE",
    DesignType.CROSS_SECTIONAL.value:      "STROBE",
    DesignType.PROGNOSTIC.value:           "STROBE",
    DesignType.QUALITATIVE.value:          "COREQ",
    DesignType.MIXED_METHODS.value:        "COREQ",
}


# ─── Timeline mapping ─────────────────────────────────────────────────────────

_TOTAL_TIMELINE: dict[str, str] = {
    DesignType.RCT.value:                  "6–18 tháng từ giờ đến submit",
    DesignType.COHORT_RETROSPECTIVE.value: "8–14 tuần từ giờ đến submit",
    DesignType.COHORT_PROSPECTIVE.value:   "6–24 tháng từ giờ đến submit",
    DesignType.CASE_CONTROL.value:         "3–6 tháng từ giờ đến submit",
    DesignType.CROSS_SECTIONAL.value:      "2–4 tháng từ giờ đến submit",
    DesignType.DIAGNOSTIC_ACCURACY.value:  "3–6 tháng từ giờ đến submit",
    DesignType.CASE_SERIES.value:          "4–8 tuần từ giờ đến submit",
    DesignType.CASE_REPORT.value:          "2–4 tuần từ giờ đến submit",
    DesignType.SYSTEMATIC_REVIEW.value:    "4–8 tháng từ giờ đến submit",
    DesignType.META_ANALYSIS.value:        "4–8 tháng từ giờ đến submit",
    DesignType.SCOPING_REVIEW.value:       "3–6 tháng từ giờ đến submit",
    DesignType.QUALITATIVE.value:          "4–8 tháng từ giờ đến submit",
    DesignType.MIXED_METHODS.value:        "6–12 tháng từ giờ đến submit",
    DesignType.BEFORE_AFTER.value:         "3–6 tháng từ giờ đến submit",
    DesignType.QUASI_EXPERIMENTAL.value:   "3–6 tháng từ giờ đến submit",
    DesignType.PROGNOSTIC.value:           "4–8 tháng từ giờ đến submit",
}

_DEFAULT_TIMELINE = "2–6 tháng từ giờ đến submit"


# ─── Step templates ───────────────────────────────────────────────────────────

def _steps_retrospective(bp: ResearchBlueprint) -> list[RoadmapStep]:
    return [
        RoadmapStep(
            step_number=1,
            title="Xin phê duyệt đạo đức (IRB/Ethics)",
            description=(
                "Hồi cứu thường được miễn informed consent, nhưng VẪN cần số phê duyệt. "
                "Liên hệ Phòng KHCN bệnh viện. Chuẩn bị: đề cương tóm tắt, Research Blueprint."
            ),
            who="Bạn tự làm",
            duration_estimate="~2–4 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Thiết kế bảng thu thập dữ liệu",
            description=(
                f"Thu thập: thông tin nền (tuổi, giới), nhóm can thiệp/so sánh, "
                f"kết cục chính ({bp.primary_outcome}), biến chứng (nếu có). "
                "Ghi rõ missing data — đừng bỏ qua, sẽ cần report trong Results."
            ),
            who="Bạn tự làm",
            duration_estimate="~1 tuần",
            avr_tool="Data Collection Form Generator (coming soon)",
        ),
        RoadmapStep(
            step_number=3,
            title="Thu thập dữ liệu từ hồ sơ bệnh án",
            description=(
                f"Nguồn: {bp.setting or 'hồ sơ bệnh án'}. "
                f"Cỡ mẫu mục tiêu: n = {bp.sample_size}. "
                "Ghi nhận cả missing data và lý do loại trừ."
            ),
            who="Bạn tự làm",
            duration_estimate="~2–6 tuần tùy cỡ mẫu",
        ),
        RoadmapStep(
            step_number=4,
            title="Phân tích thống kê",
            description=(
                f"Primary: so sánh {bp.primary_outcome} giữa 2 nhóm. "
                "Kiểm tra phân phối chuẩn (Shapiro-Wilk) trước → chọn t-test hoặc Mann-Whitney U. "
                "Report: mean ± SD (hoặc median + IQR), p-value, 95% CI."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
            avr_tool="Statistical Plan Builder (coming soon)",
        ),
        RoadmapStep(
            step_number=5,
            title="Hoàn thiện Abstract → Chạy Gate",
            description=(
                "Điền data thật vào phần Results của abstract ước tính. "
                "Quay lại AVR → Phase 2 (Submission Gate) để kiểm duyệt trước khi nộp."
            ),
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=6,
            title="Viết full manuscript",
            description=(
                "Sau khi Gate pass → AVR tạo khung sườn manuscript theo đúng journal format. "
                "Đắp thịt vào khung, submit."
            ),
            who="AVR hỗ trợ",
            duration_estimate="~2–4 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


def _steps_rct(bp: ResearchBlueprint) -> list[RoadmapStep]:
    return [
        RoadmapStep(
            step_number=1,
            title="Đăng ký thử nghiệm lâm sàng",
            description=(
                "RCT bắt buộc đăng ký TRƯỚC khi thu nhận bệnh nhân. "
                "Các registry được chấp nhận: ClinicalTrials.gov, ANZCTR, WHO ICTRP. "
                "Lấy số đăng ký (trial registration number) để đưa vào abstract."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Xin phê duyệt đạo đức (IRB/Ethics)",
            description=(
                "RCT yêu cầu full ethics approval + informed consent form. "
                "Chuẩn bị đầy đủ: protocol, IB (nếu có thuốc/thiết bị mới), consent form mẫu."
            ),
            who="Bạn tự làm",
            duration_estimate="~4–8 tuần",
        ),
        RoadmapStep(
            step_number=3,
            title="Thiết kế quy trình randomization",
            description=(
                "Chọn phương pháp: block randomization, stratified, hoặc simple. "
                "Chuẩn bị allocation concealment (sealed envelopes hoặc REDCap). "
                "Document rõ ràng để viết vào phần Methods."
            ),
            who="Bạn tự làm",
            duration_estimate="~1 tuần",
        ),
        RoadmapStep(
            step_number=4,
            title="Thiết kế bảng thu thập dữ liệu + CRF",
            description=(
                f"Case Report Form (CRF) cần cover: baseline, can thiệp, "
                f"kết cục ({bp.primary_outcome}), adverse events, withdrawals."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
            avr_tool="Data Collection Form Generator (coming soon)",
        ),
        RoadmapStep(
            step_number=5,
            title="Thu nhận bệnh nhân & can thiệp",
            description=(
                f"Target: n = {bp.sample_size} (tính cả dropout rate ~15–20%). "
                "Theo dõi sát adverse events. Document mọi protocol deviation."
            ),
            who="Bạn tự làm",
            duration_estimate=bp.timeframe or "~3–12 tháng tùy protocol",
        ),
        RoadmapStep(
            step_number=6,
            title="Phân tích thống kê",
            description=(
                "Intention-to-treat (ITT) analysis là primary. "
                "Per-protocol analysis là secondary. "
                "Report: effect size, 95% CI, p-value, NNT nếu phù hợp."
            ),
            who="Bạn tự làm",
            duration_estimate="~2–4 tuần",
            avr_tool="Statistical Plan Builder (coming soon)",
        ),
        RoadmapStep(
            step_number=7,
            title="Hoàn thiện Abstract → Chạy Gate",
            description=(
                "Điền data thật vào Results. "
                "Đảm bảo đã báo cáo: randomization ratio, số dropout, ITT population."
            ),
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=8,
            title="Viết full manuscript",
            description="AVR tạo khung sườn CONSORT-compliant. Đắp thịt, submit.",
            who="AVR hỗ trợ",
            duration_estimate="~2–4 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


def _steps_diagnostic(bp: ResearchBlueprint) -> list[RoadmapStep]:
    return [
        RoadmapStep(
            step_number=1,
            title="Xin phê duyệt đạo đức",
            description="Cần ethics approval + informed consent (nếu prospective).",
            who="Bạn tự làm",
            duration_estimate="~2–4 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Xác định gold standard & spectrum bệnh",
            description=(
                f"Mọi bệnh nhân phải được xét nghiệm bằng CẢ index test VÀ reference standard. "
                "Document rõ spectrum of disease (mild → severe). "
                "Tránh verification bias."
            ),
            who="Bạn tự làm",
            duration_estimate="~1 tuần",
        ),
        RoadmapStep(
            step_number=3,
            title="Thu thập dữ liệu — blinded reading",
            description=(
                "Người đọc index test không biết kết quả reference standard (và ngược lại). "
                f"Target: n = {bp.sample_size} (tính cả bệnh (+) và bệnh (-))."
            ),
            who="Bạn tự làm",
            duration_estimate="~2–8 tuần",
        ),
        RoadmapStep(
            step_number=4,
            title="Phân tích độ chính xác chẩn đoán",
            description=(
                "Tính: Sensitivity, Specificity, PPV, NPV, LR+, LR−, AUC (ROC). "
                "Dùng: MedCalc, STATA, hoặc R package `pROC`. "
                "Report 95% CI cho mọi chỉ số."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
            avr_tool="Statistical Plan Builder (coming soon)",
        ),
        RoadmapStep(
            step_number=5,
            title="Hoàn thiện Abstract → Chạy Gate",
            description="Điền data thật. Đảm bảo báo cáo đủ 4 ô contingency table.",
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=6,
            title="Viết full manuscript",
            description="AVR tạo khung STARD-compliant. Đắp thịt, submit.",
            who="AVR hỗ trợ",
            duration_estimate="~2–4 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


def _steps_case_series(bp: ResearchBlueprint) -> list[RoadmapStep]:
    return [
        RoadmapStep(
            step_number=1,
            title="Xin phê duyệt đạo đức",
            description="Case series thường được miễn consent nhưng cần ethics approval.",
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Thu thập & chuẩn hóa dữ liệu từng ca",
            description=(
                f"Ghi nhận đồng nhất mỗi ca: demographics, presentation, intervention, "
                f"outcome ({bp.primary_outcome}), follow-up. "
                "Missing data phải được report rõ."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–3 tuần",
        ),
        RoadmapStep(
            step_number=3,
            title="Phân tích mô tả",
            description=(
                "Thống kê mô tả: mean/median, range, tần suất. "
                "Không có control group → không dùng p-value so sánh nhóm."
            ),
            who="Bạn tự làm",
            duration_estimate="~1 tuần",
        ),
        RoadmapStep(
            step_number=4,
            title="Hoàn thiện Abstract → Chạy Gate",
            description="Điền data thật. Lưu ý: không over-claim causal inference.",
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=5,
            title="Viết full manuscript",
            description="AVR tạo khung CARE-compliant. Đắp thịt, submit.",
            who="AVR hỗ trợ",
            duration_estimate="~1–2 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


def _steps_review(bp: ResearchBlueprint) -> list[RoadmapStep]:
    return [
        RoadmapStep(
            step_number=1,
            title="Đăng ký protocol (PROSPERO)",
            description=(
                "Systematic review & meta-analysis nên đăng ký PROSPERO trước khi bắt đầu. "
                "Miễn phí tại prospero.york.ac.uk."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Thiết kế search strategy",
            description=(
                "Search ≥ 2 databases: PubMed + EMBASE tối thiểu. "
                f"Query từ blueprint: {bp.intervention_or_exposure}, {bp.primary_outcome}. "
                "Thêm: grey literature, reference lists."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
        ),
        RoadmapStep(
            step_number=3,
            title="Screening & full-text review (2 reviewers)",
            description=(
                "Dùng Covidence, Rayyan hoặc Excel. "
                "2 reviewers độc lập, đồng thuận bởi reviewer thứ 3 khi conflict. "
                "Document PRISMA flow diagram."
            ),
            who="Bạn tự làm",
            duration_estimate="~3–6 tuần",
        ),
        RoadmapStep(
            step_number=4,
            title="Đánh giá chất lượng nghiên cứu",
            description=(
                "RCT: Cochrane RoB 2.0. Observational: Newcastle-Ottawa Scale. "
                "Report kết quả dưới dạng traffic light plot."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
        ),
        RoadmapStep(
            step_number=5,
            title="Meta-analysis (nếu áp dụng)",
            description=(
                "Dùng RevMan, R (meta package) hoặc STATA. "
                "Random effects model khi I² > 50%. "
                "Funnel plot để detect publication bias."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
            avr_tool="Statistical Plan Builder (coming soon)",
        ),
        RoadmapStep(
            step_number=6,
            title="Hoàn thiện Abstract → Chạy Gate",
            description="Điền kết quả meta-analysis. Đảm bảo báo cáo heterogeneity (I²).",
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=7,
            title="Viết full manuscript",
            description="AVR tạo khung PRISMA-compliant. Đắp thịt, submit.",
            who="AVR hỗ trợ",
            duration_estimate="~2–4 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


def _steps_observational(bp: ResearchBlueprint) -> list[RoadmapStep]:
    """Cross-sectional, case-control, prospective cohort, prognostic."""
    return [
        RoadmapStep(
            step_number=1,
            title="Xin phê duyệt đạo đức (IRB/Ethics)",
            description=(
                "Cần ethics approval. Prospective study cần cả informed consent. "
                "Chuẩn bị: đề cương, sampling frame, consent form."
            ),
            who="Bạn tự làm",
            duration_estimate="~2–4 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Thiết kế bảng thu thập dữ liệu",
            description=(
                f"Bao gồm: demographics, exposure/outcome ({bp.primary_outcome}), "
                "confounders. Chuẩn hóa định nghĩa biến số trước khi thu thập."
            ),
            who="Bạn tự làm",
            duration_estimate="~1 tuần",
            avr_tool="Data Collection Form Generator (coming soon)",
        ),
        RoadmapStep(
            step_number=3,
            title="Thu thập dữ liệu",
            description=(
                f"Target: n = {bp.sample_size}. "
                "Ghi nhận missing data có hệ thống. "
                "Tránh selection bias trong quá trình sampling."
            ),
            who="Bạn tự làm",
            duration_estimate=bp.timeframe or "~2–8 tuần",
        ),
        RoadmapStep(
            step_number=4,
            title="Phân tích thống kê",
            description=(
                f"Primary analysis: {bp.statistical_approach or 'so sánh nhóm, regression phù hợp'}. "
                "Adjust confounders bằng multivariate regression nếu cần. "
                "Report: OR/RR/HR, 95% CI, p-value."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
            avr_tool="Statistical Plan Builder (coming soon)",
        ),
        RoadmapStep(
            step_number=5,
            title="Hoàn thiện Abstract → Chạy Gate",
            description="Điền data thật. Kiểm tra đủ confounders được addressed.",
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=6,
            title="Viết full manuscript",
            description="AVR tạo khung STROBE-compliant. Đắp thịt, submit.",
            who="AVR hỗ trợ",
            duration_estimate="~2–4 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


def _steps_qualitative(bp: ResearchBlueprint) -> list[RoadmapStep]:
    return [
        RoadmapStep(
            step_number=1,
            title="Xin phê duyệt đạo đức + informed consent",
            description="Qualitative study bắt buộc có consent form chi tiết về ghi âm/ghi chép.",
            who="Bạn tự làm",
            duration_estimate="~2–4 tuần",
        ),
        RoadmapStep(
            step_number=2,
            title="Thiết kế interview guide / focus group guide",
            description=(
                "Câu hỏi mở, theo thứ tự từ general → specific. "
                "Pilot test với 1–2 participant trước. "
                "Không leading questions."
            ),
            who="Bạn tự làm",
            duration_estimate="~1–2 tuần",
        ),
        RoadmapStep(
            step_number=3,
            title="Thu thập dữ liệu đến saturation",
            description=(
                f"Target: {bp.sample_size} participants hoặc đến data saturation. "
                "Ghi âm + transcription verbatim. Member checking để xác nhận accuracy."
            ),
            who="Bạn tự làm",
            duration_estimate="~4–8 tuần",
        ),
        RoadmapStep(
            step_number=4,
            title="Phân tích định tính (thematic analysis)",
            description=(
                "Coding → themes. Dùng NVivo, ATLAS.ti hoặc manual. "
                "2 coders độc lập, tính inter-rater reliability (Cohen's kappa)."
            ),
            who="Bạn tự làm",
            duration_estimate="~2–4 tuần",
        ),
        RoadmapStep(
            step_number=5,
            title="Hoàn thiện Abstract → Chạy Gate",
            description="Điền kết quả (themes, quotes). Đảm bảo reflexivity được addressed.",
            who="AVR hỗ trợ",
            duration_estimate="~1 tuần",
            avr_tool="Submission Gate + Guided Revision",
        ),
        RoadmapStep(
            step_number=6,
            title="Viết full manuscript",
            description="AVR tạo khung COREQ-compliant. Đắp thịt, submit.",
            who="AVR hỗ trợ",
            duration_estimate="~2–4 tuần",
            avr_tool="Manuscript Outline Generator (Phase 3)",
        ),
    ]


# ─── Main function ────────────────────────────────────────────────────────────

def generate_roadmap(blueprint: ResearchBlueprint) -> ResearchRoadmap:
    """Generate a template-based research roadmap from a ResearchBlueprint."""
    design = blueprint.design_type.value if hasattr(blueprint.design_type, "value") else str(blueprint.design_type)

    # Select steps template
    if design == DesignType.RCT.value:
        steps = _steps_rct(blueprint)
    elif design in (DesignType.QUASI_EXPERIMENTAL.value, DesignType.BEFORE_AFTER.value):
        steps = _steps_rct(blueprint)  # similar structure
    elif design == DesignType.COHORT_RETROSPECTIVE.value:
        steps = _steps_retrospective(blueprint)
    elif design in (DesignType.COHORT_PROSPECTIVE.value, DesignType.CASE_CONTROL.value,
                    DesignType.CROSS_SECTIONAL.value, DesignType.PROGNOSTIC.value):
        steps = _steps_observational(blueprint)
    elif design == DesignType.DIAGNOSTIC_ACCURACY.value:
        steps = _steps_diagnostic(blueprint)
    elif design in (DesignType.CASE_SERIES.value, DesignType.CASE_REPORT.value):
        steps = _steps_case_series(blueprint)
    elif design in (DesignType.SYSTEMATIC_REVIEW.value, DesignType.META_ANALYSIS.value,
                    DesignType.SCOPING_REVIEW.value):
        steps = _steps_review(blueprint)
    elif design in (DesignType.QUALITATIVE.value, DesignType.MIXED_METHODS.value):
        steps = _steps_qualitative(blueprint)
    else:
        steps = _steps_retrospective(blueprint)  # safe default

    checklist = _CHECKLIST_MAP.get(design, "STROBE")
    timeline = _TOTAL_TIMELINE.get(design, _DEFAULT_TIMELINE)

    return ResearchRoadmap(
        steps=steps,
        checklist_type=checklist,
        total_timeline_estimate=timeline,
        design_type=design,
    )
