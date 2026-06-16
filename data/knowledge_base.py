"""Knowledge base dùng chung cho SDG và Agent mock retrieval."""

DOC_CATALOG = {
    "doc_policy_001": {
        "title": "Chính sách tài khoản",
        "keywords": ["mật khẩu", "password", "đăng nhập", "tài khoản", "account"],
        "content": "Để đổi mật khẩu: vào Cài đặt > Bảo mật > Đổi mật khẩu. Mật khẩu tối thiểu 8 ký tự.",
    },
    "doc_faq_002": {
        "title": "FAQ hướng dẫn",
        "keywords": ["đổi", "thay đổi", "cài đặt", "hướng dẫn", "faq"],
        "content": "Hướng dẫn đổi thông tin tài khoản và cài đặt cá nhân trong ứng dụng.",
    },
    "doc_guide_003": {
        "title": "Hướng dẫn AI Evaluation",
        "keywords": ["evaluation", "đánh giá", "benchmark", "ragas", "ai"],
        "content": "RAGAS đo lường faithfulness, answer relevancy và chất lượng retrieval cho hệ RAG.",
    },
    "doc_security_004": {
        "title": "Bảo mật & 2FA",
        "keywords": ["bảo mật", "security", "xác thực", "2fa", "otp"],
        "content": "Bật xác thực 2 yếu tố tại Cài đặt bảo mật. Hỗ trợ SMS và Authenticator app.",
    },
    "doc_support_005": {
        "title": "Hỗ trợ khách hàng",
        "keywords": ["hỗ trợ", "support", "liên hệ", "ticket", "helpdesk"],
        "content": "Liên hệ helpdesk qua ticket hoặc hotline. Chỉ trả lời trong phạm vi tài liệu hệ thống.",
    },
    "doc_billing_006": {
        "title": "Thanh toán & hóa đơn",
        "keywords": ["thanh toán", "billing", "hóa đơn", "invoice", "gói"],
        "content": "Xem hóa đơn tại Billing > Lịch sử. Hỗ trợ thẻ tín dụng và chuyển khoản.",
    },
    "doc_api_007": {
        "title": "Tài liệu API",
        "keywords": ["api", "endpoint", "token", "rest", "webhook"],
        "content": "API key tạo tại Developer Portal. Rate limit 100 req/phút cho gói free.",
    },
    "doc_privacy_008": {
        "title": "Quyền riêng tư",
        "keywords": ["privacy", "gdpr", "dữ liệu", "xóa", "consent"],
        "content": "Người dùng có quyền yêu cầu xóa dữ liệu cá nhân trong vòng 30 ngày.",
    },
    "doc_onboard_009": {
        "title": "Onboarding",
        "keywords": ["onboarding", "bắt đầu", "tutorial", "setup", "khởi tạo"],
        "content": "Quy trình onboarding gồm 4 bước: đăng ký, xác minh email, cấu hình workspace, mời thành viên.",
    },
    "doc_incident_010": {
        "title": "Xử lý sự cố",
        "keywords": ["incident", "sự cố", "downtime", "sla", "outage"],
        "content": "SLA uptime 99.9%. Báo sự cố qua status page hoặc PagerDuty integration.",
    },
}
