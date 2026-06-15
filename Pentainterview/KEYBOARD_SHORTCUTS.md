# ⌨️ Keyboard Shortcuts Guide

## Overview
Added full keyboard shortcut support to PentaInterview iOS app for external keyboard users (iPad + Keyboard, Mac Catalyst, etc.)

---

## Keyboard Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| **⌃⇧Z** | Gợi ý | Trigger AI suggestion based on profile |
| **⌃⇧X** | Tóm tắt | Summarize question (Vietnamese) |
| **⌃⇧C** | Xoá | Clear all transcripts |

**Note:** ⌃ = Control (Ctrl), ⇧ = Shift, Z/X/C = Key letter

---

## What Was Changed

### 1. **ContentView.swift** - Main UI
- ✅ Added `@State private var showKeyboardShortcuts = false` to track sheet state
- ✅ Added **Ctrl+Shift+Z** shortcut to "Gợi ý" button
- ✅ Added **Ctrl+Shift+X** shortcut to "Tóm tắt" button  
- ✅ Added **Ctrl+Shift+C** shortcut to "Xoá" button
- ✅ Added keyboard icon button (⌘) in header to access shortcuts guide
- ✅ Updated "Gợi ý" button UI to show shortcut hint: **⌃⇧Z**

### 2. **KeyboardShortcutsView.swift** - NEW FILE
- ✅ Beautiful shortcuts guide with all three shortcuts listed
- ✅ Each shortcut shows: keys, description, and detail explanation
- ✅ Tips section for best practices
- ✅ Dark theme matching app design

---

## Features

### Visual Indicators
- **Button label** now shows keyboard shortcut (⌃⇧Z) under "Gợi ý" text
- **Header button** (⌘ icon) opens detailed shortcuts guide
- **Shortcuts guide view** displays all shortcuts with key layout visualization

### Smart Integration
- Shortcuts respect button **disabled state**
  - Gợi ý: Only works when connected + transcript exists
  - Tóm tắt: Only works when transcript not empty
  - Xoá: Always available
- Visual feedback with **button animations**
- **Consistent styling** with app design tokens

### User Experience
- Discoverable: Help button in header
- Memorable: Visual shortcuts on button labels
- Professional: Detailed guide with tips
- Non-intrusive: Works alongside touch UI

---

## How to Use

### For iPad Users
1. **Connect external keyboard** to iPad
2. **Open app** - PentaInterview will recognize keyboard
3. **Press shortcuts**:
   - **⌃⇧Z** → Get AI suggestion
   - **⌃⇧X** → Summarize question
   - **⌃⇧C** → Clear transcript

### View Shortcuts Guide
- **Tap ⌘ button** in top-right corner (next to ⚙️)
- Shows all shortcuts with visual key layout
- Includes tips for best practices

---

## Code Implementation

### SwiftUI Keyboard Shortcut API
```swift
Button {
    // Action here
} label: {
    // Label here
}
.keyboardShortcut("z", modifiers: [.control, .shift])
```

### Multiple Modifiers
```swift
// Ctrl + Shift + Z
.keyboardShortcut("z", modifiers: [.control, .shift])

// Alternative: using OptionSet syntax
.keyboardShortcut("z", modifiers: [.shift, .control])
```

---

## Browser Compatibility

✅ **Works on:**
- iPad with external keyboard
- Mac Catalyst
- Mac version (if available)
- Physical keyboard connected

❌ **Not available on:**
- Touch-only devices (no keyboard)
- Virtual keyboard

**Graceful fallback:** App remains fully usable without keyboard - all buttons available via touch UI

---

## Technical Details

### File Locations
- `PentaInterviewIos/ContentView.swift` - Modified (shortcuts + button + state)
- `PentaInterviewIos/KeyboardShortcutsView.swift` - New (guide UI)

### SwiftUI Features Used
- `.keyboardShortcut()` modifier
- `@State` for sheet presentation
- `.sheet(isPresented:)` for modal presentation
- Custom view composition

### Design Consistency
- Color scheme: Using app's design tokens
  - Accent: #52B6FF
  - Background: #0D0F12
  - Text main: #DDE3F0
  - Text dim: #5A6480
- Font sizing: Consistent with existing components
- Spacing/padding: Matches app layout system

---

## Testing Checklist

- [ ] Connect iPad + external keyboard
- [ ] Press **⌃⇧Z** → Should trigger "Gợi ý" (if conditions met)
- [ ] Press **⌃⇧X** → Should trigger "Tóm tắt" (if transcript exists)
- [ ] Press **⌃⇧C** → Should clear transcript
- [ ] Tap **⌘ button** → Should show shortcuts guide
- [ ] Close guide → App should work normally
- [ ] Test touch UI still works (all buttons clickable)
- [ ] Test disabled states (buttons gray out when needed)

---

## Future Enhancements

Possible improvements:
- [ ] Customizable keyboard shortcuts (settings)
- [ ] More shortcuts (scroll, expand panels, etc.)
- [ ] Haptic feedback on shortcut activation
- [ ] Shortcut hints on long-press
- [ ] Save shortcut preferences
- [ ] Voice command integration

---

## Notes

### Why These Shortcuts?
- **Z** = "Z"uggestion (AI Suggestion) - Easy to remember
- **X** = e"X"tract/summarize - Mnemonic for text processing
- **C** = "C"lear - Standard convention

### Modifier Choice
- **Ctrl+Shift** = Less likely to conflict with system shortcuts
- **Triple modifier** = Intentional (prevents accidental activation)

### Profile-Aware Suggestions
The "Gợi ý" shortcut still uses the full profile context from CandidateProfile.swift:
- Name: Lê Đăng Khoa
- Target roles: AI Full Stack Engineer, etc.
- Skills: Python, Swift, FastAPI, etc.
- Projects: PentaSchool, PentaMO, etc.
- Experience: Self-taught developer, JLPT N3
- Background: Manufacturing → Software transition

---

## Support

**Keyboard not working?**
1. Verify keyboard is physically connected
2. Check app has keyboard focus
3. Try in Settings app first to test OS-level keyboard
4. Restart app if needed

**Shortcuts not discoverable?**
- Tap **⌘ button** in header for guide
- Check button labels for shortcut hints
- Long-press buttons for additional help (future feature)

---

**Status:** ✅ Complete & Ready to Use  
**Date:** May 3, 2026  
**Version:** 1.0
