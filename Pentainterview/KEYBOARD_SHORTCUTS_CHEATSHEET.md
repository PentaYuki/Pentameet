# ⌨️ Keyboard Shortcuts Quick Reference

## Quick Cheat Sheet

```
┌─────────────────────────────────────────────────────────┐
│        PentaInterview - Keyboard Shortcuts              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🎯  AI Suggestion          Ctrl + Shift + Z           │
│      (⌃⇧Z)                  Gợi ý trả lời dựa profile  │
│                                                         │
│  📋 Summarize Question      Ctrl + Shift + X           │
│      (⌃⇧X)                  Tóm tắt thành Tiếng Việt   │
│                                                         │
│  🗑️  Clear Transcript        Ctrl + Shift + C           │
│      (⌃⇧C)                  Xoá toàn bộ transcript     │
│                                                         │
│  ⌨️  Shortcuts Guide         Tap ⌘ button (top-right)  │
│                              View all shortcuts         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Requirements: iPad + External Keyboard (or Mac)        │
│  Graceful Fallback: Touch buttons still work!           │
└─────────────────────────────────────────────────────────┘
```

---

## Key Layout

```
┌─────────────────────┐
│  Ctrl  ⌃  (hold)   │
│  Shift ⇧  (hold)   │
│  + Press Key       │
├─────────────────────┤
│    Z  X  C         │
│  Suggest Summary   │
│                    │
│  Hold both ⌃⇧     │
│  Then press key   │
└─────────────────────┘
```

---

## Usage Examples

### Example 1: Get AI Suggestion
```
1. Ask a question (wait for transcription)
2. Press: ⌃ + ⇧ + Z
3. AI generates suggestion (1-3s)
4. See answer in "Gợi ý trả lời" panel
```

### Example 2: Summarize
```
1. Interviewer asks long question
2. Press: ⌃ + ⇧ + X
3. Gemini summarizes (2-5s)
4. See summary in "Tóm tắt" panel (Vietnamese)
```

### Example 3: Clear & Start Fresh
```
1. Interview finished or want to restart
2. Press: ⌃ + ⇧ + C
3. All transcripts cleared instantly
4. Ready for next question
```

---

## Button Indicators

### On-Screen Hints
```
┌──────────────────────┐
│ ⌘                    │  ← Tap for shortcuts guide
│ ⚙️                    │  ← Settings
└──────────────────────┘

┌───────────────────────┐
│ 🗑️  ✨Tóm tắt   🎯Gợi ý│
├───────────────────────┤
│  ⌃⇧C  ⌃⇧X      ⌃⇧Z  │  ← Keyboard hints
└───────────────────────┘
```

The "Gợi ý" button shows **⌃⇧Z** below the text

---

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **iPad + Keyboard** | ✅ Fully supported | Recommended |
| **Mac Catalyst** | ✅ Works | If available |
| **Mac App** | ✅ Works | If ported |
| **iPhone (touch only)** | ✅ Buttons work | No keyboard shortcuts |
| **Apple Keyboard** | ✅ Works | Standard keyboard |
| **Third-party Keyboard** | ✅ Should work | Most compatible |

---

## Troubleshooting

### Shortcuts Not Working?

**Check 1:** Keyboard Connected?
```
✓ Physical keyboard connected to iPad
✓ iPad recognizes keyboard (check iPad settings)
✓ Try typing in Notes app first
```

**Check 2:** App Has Focus?
```
✓ App window is active (not background)
✓ No other app taking keyboard input
✓ Text field not focused (unless intended)
```

**Check 3:** Button Conditions?
```
✓ "Gợi ý": Need connected + transcript
✓ "Tóm tắt": Need non-empty transcript  
✓ "Xoá": Always available
```

**Check 4:** Restart?
```bash
1. Close app completely
2. Restart app
3. Reconnect keyboard if needed
4. Try again
```

---

## Advanced: Custom Shortcuts (Future)

Currently shortcuts are fixed:
- **Z** for Suggestion
- **X** for Summarize
- **C** for Clear

Future enhancement: Allow users to customize (coming soon)

---

## Profile-Aware Suggestions

When you press **⌃⇧Z**, the AI suggestion uses:

```
Profile: Lê Đăng Khoa
├─ Target Roles
│  ├─ AI Full Stack Engineer
│  ├─ Bridge Software Engineer
│  └─ AI Integration Engineer
├─ Skills
│  ├─ Languages: Python, Swift, JS, TS, SQL
│  ├─ Frameworks: FastAPI, Flask, SwiftUI, React
│  ├─ AI Tools: Gemini, Ollama, LangChain, FAISS
│  └─ Infra: Docker, PostgreSQL, Vercel
├─ Projects
│  ├─ PentaSchool (LMS)
│  ├─ PentaMO (AI Marketplace)
│  ├─ PentaKurumi (Real-time Pipeline)
│  ├─ PentaAli (Gesture Manager)
│  └─ VN Stock Market AI
└─ Background: Manufacturing → Software, JLPT N3
```

Suggestion is tailored to THIS profile!

---

## File Locations

```
PentaInterviewIos/
├── ContentView.swift              ← Shortcuts logic
├── KeyboardShortcutsView.swift    ← Guide view
├── CandidateProfile.swift         ← Profile data
├── BackendService.swift           ← Backend calls
└── PentaInterviewIosApp.swift     ← App entry
```

---

## Tips & Tricks

### Tip 1: Keyboard Muscle Memory
```
Practice the 3 shortcuts:
⌃⇧Z → AI answer (most used)
⌃⇧X → Summarize (when needed)
⌃⇧C → Clear (between questions)
```

### Tip 2: Workflow Optimization
```
1. Interviewer speaks...
2. Wait for full transcript
3. Press ⌃⇧Z immediately
4. AI generates suggestion (1-3s)
5. You read answer while thinking
6. Answer perfectly!
```

### Tip 3: Multi-question Session
```
Q1: Get suggestion (⌃⇧Z)
Q1: Answer interviewer
Q2: Clear (⌃⇧C)
Q2: Get suggestion (⌃⇧Z)
... repeat
```

### Tip 4: Long Questions
```
Interviewer asks long Q...
→ Press ⌃⇧X first (summarize)
→ Then ⌃⇧Z (get suggestion)
→ 2 panels = full context!
```

---

## Need Help?

**View full guide:**
- Tap **⌘** button in top-right corner
- Detailed guide with explanations
- Tips and best practices included

**Check documentation:**
- KEYBOARD_SHORTCUTS.md (this file's long version)
- README_AI_SUGGESTION.md (AI system)
- QUICK_START.md (setup guide)

---

## Summary

```
Just 3 shortcuts:
⌃⇧Z = Gợi ý (Suggest)
⌃⇧X = Tóm tắt (Summarize)  
⌃⇧C = Xoá (Clear)

All profile-aware, all AI-powered!
```

**Happy interviewing! 🚀**
