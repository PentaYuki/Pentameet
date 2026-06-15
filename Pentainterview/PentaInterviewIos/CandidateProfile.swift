// CandidateProfile.swift
// Interview Assistant iOS
// Profile JSON của ứng viên — Gemini sẽ dùng để tạo câu trả lời phù hợp

import Foundation

// MARK: - Models

struct CandidateProfile: Codable {
    let name: String
    let targetRoles: [String]
    let skills: SkillSet
    let projects: [ProjectEntry]
    let experience: String
    let japaneseLevel: String
    let background: String

    enum CodingKeys: String, CodingKey {
        case name
        case targetRoles   = "target_roles"
        case skills, projects, experience
        case japaneseLevel = "japanese_level"
        case background
    }

    // Chuyển thành dict để gửi lên backend
    var asDict: [String: Any] {
        return [
            "name": name,
            "target_roles": targetRoles,
            "skills": [
                "languages":   skills.languages,
                "frameworks":  skills.frameworks,
                "ai_tools":    skills.aiTools,
                "infra":       skills.infra,
            ],
            "projects": projects.map { ["name": $0.name, "desc": $0.desc] },
            "experience":      experience,
            "japanese_level":  japaneseLevel,
            "background":      background,
        ]
    }
}

struct SkillSet: Codable {
    let languages: [String]
    let frameworks: [String]
    let aiTools: [String]
    let infra: [String]

    enum CodingKeys: String, CodingKey {
        case languages, frameworks
        case aiTools = "ai_tools"
        case infra
    }
}

struct ProjectEntry: Codable {
    let name: String
    let desc: String
}

// MARK: - Khoa's Profile

extension CandidateProfile {
    /// Profile mặc định — chỉnh trực tiếp tại đây trước mỗi phỏng vấn
    static let current = CandidateProfile(
        name: "Lê Đăng Khoa (alias: Yato / PentaYuki)",

        targetRoles: [
            "AI Full Stack Engineer",
            "Bridge Software Engineer (JP↔VN)",
            "AI Integration Engineer",
        ],

        skills: SkillSet(
            languages:  ["Python", "Swift", "JavaScript", "TypeScript", "SQL"],
            frameworks: ["FastAPI", "Flask", "Flask-SocketIO", "SwiftUI", "React", "Next.js"],
            aiTools:    [
                "Gemini API", "Ollama (local LLM)", "Faster-Whisper",
                "Silero VAD", "FAISS vector search", "LangChain",
                "PhoBERT / FinBERT", "Gemma 3 4B",
            ],
            infra: [
                "Tailscale", "Docker", "PostgreSQL", "Supabase",
                "WebSocket / Socket.IO", "SSE", "Vercel", "GitHub Actions",
            ]
        ),

        projects: [
            ProjectEntry(
                name: "PentaSchool (LMS)",
                desc: "Full learning management system with AI auto-grading, Fabric.js canvas editor, KaTeX math rendering, Vietnamese K12 exam parser (MCQ/TF/SAQ), live on Vercel with Supabase backend"
            ),
            ProjectEntry(
                name: "PentaMO (AI Marketplace)",
                desc: "AI-powered Vietnamese motorcycle marketplace: 7-step orchestration pipeline, FAISS semantic cache, bilingual support, Ollama local inference, lead scoring"
            ),
            ProjectEntry(
                name: "PentaKurumi (Real-time AI Pipeline)",
                desc: "Cross-platform STT→LLM→TTS pipeline: Mac mini FastAPI server, iOS SwiftUI PentaCommand app, Windows PySide6 launcher, connected via Tailscale"
            ),
            ProjectEntry(
                name: "PentaAli (Gesture Window Manager)",
                desc: "Gesture-controlled Windows window management system with 5-layer architecture, remotely configured via iOS companion app"
            ),
            ProjectEntry(
                name: "VN Stock Market AI",
                desc: "Multi-agent forecasting system: technical, sentiment (PhoBERT/FinBERT), macro, and risk agents; Kronos time-series model; MLOps drift detection; FastAPI dashboard"
            ),
        ],

        experience: "Self-taught developer. Prior work: manufacturing worker at Nagano Interior Kabushiki Kaisha, Japan. Tester at Viet Map. JLPT N3, actively studying N2.",

        japaneseLevel: "JLPT N3 (studying N2, business communication level)",

        background: "Non-IT graduate (Automotive Engineering, HUTECH). Transitioned entirely to software through self-learning. Specializes in local-first AI systems, real-time pipelines, and multi-platform integrations. Comfortable working in Japanese corporate environments."
    )
}
