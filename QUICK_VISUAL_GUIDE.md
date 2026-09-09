# AI Context Management - Quick Visual Reference

## 📍 Where to Find It

```
Brainr Dashboard
    ↓
    ⚙️ Settings (gear icon, top right)
    ↓
    AI Context Tab ⚡ (new tab in Settings)
    ↓
    Manage All AI Instructions
```

## 🎨 UI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ ⚙️ Settings                                                 🔄 Refresh │
├──────────────────────────────────────────────────────────────────┤
│ Tabs:                                                              │
│ LLM | Database | SQLite | Vector | Training | Auth | ... | AI ⚡ | │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│ AI Context Management                                             │
│ Configure all system instructions and context that the AI will   │
│ use. No more hidden context — manage everything here.            │
│                                                                    │
│ ┌─ Content Sections ──────────────────────────────────────────┐ │
│ │ System ▼ | Rules ▢ | Business ▢ | Isolation ▢ | Vocab ▢   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│ System Instructions                                               │
│ Main system prompt that guides AI behavior                        │
│ [Copy 📋]                                                         │
│                                                                    │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ You are the Clientshot AI Assistant — a conversational    │  │
│ │ product expert embedded in the Clientshot feedback         │  │
│ │ management platform. You help form admins, branch admins,  │  │
│ │ and support users understand their feedback data,          │  │
│ │ navigate the product, and solve problems.                  │  │
│ │                                                            │  │
│ │ Your job is NOT to be a database query tool. It is to     │  │
│ │ sound like a knowledgeable teammate who understands the   │  │
│ │ data, knows the product deeply, and communicates in       │  │
│ │ plain English.                                            │  │
│ │                                                            │  │
│ │ [... 1000+ more lines of instructions ...]                │  │
│ │                                                            │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ 💡 Tip: This is the main system prompt that will be sent to the   │
│    LLM. It defines the AI's role, behavior, response style, and   │
│    all business rules.                                            │
│                                                                    │
│ ┌─ Action Buttons ────────────────────────────────────────────┐  │
│ │ [💾 Save Context] [🔄 Reset to Default]                   │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ℹ️ How This Works                                                 │
│ • System Instructions: Sent to the LLM as system message         │
│ • Response Rules: Guidelines for formatting and style            │
│ • Business Rules: Constraints and business logic                 │
│ • Data Isolation: Multi-tenant filtering rules                   │
│ • Vocabulary: Terminology definitions                            │
│ • All changes apply immediately to new responses                 │
│ • Previous conversations are not affected                        │
│                                                                    │
│ Last updated: Jan 15, 2024 at 2:30 PM                            │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

## 📋 The 5 Sections

### 1️⃣ System Instructions (Required)
**Icon**: 📝
**Default**: Loaded from existing `CLIENTSHOT_SYSTEM_INSTRUCTIONS`
**Size**: ~1000+ lines
**Use**: Main AI behavior, roles, response style
**Required**: Yes

### 2️⃣ Response Rules (Optional)
**Icon**: 📐
**Default**: Empty
**Size**: As needed
**Use**: Response formatting, output structure
**Required**: No

### 3️⃣ Business Rules (Optional)
**Icon**: ⚖️
**Default**: Empty
**Size**: As needed
**Use**: Business constraints, validation rules
**Required**: No

### 4️⃣ Data Isolation (Optional)
**Icon**: 🔒
**Default**: Empty
**Size**: As needed
**Use**: Multi-tenant security, company filtering
**Required**: No

### 5️⃣ Vocabulary (Optional)
**Icon**: 📚
**Default**: Empty
**Size**: As needed
**Use**: Terminology definitions, glossary
**Required**: No

## 🔄 User Actions Flow

```
Admin Opens Settings
   │
   ├─ Clicks "AI Context" Tab
   │  └─ Page loads current context from database
   │
   ├─ Reads current instructions
   │  └─ Can see all 5 sections
   │
   ├─ Edits Content
   │  ├─ Click any tab (System, Rules, etc.)
   │  ├─ Edit text in textarea
   │  └─ Can use copy button to backup
   │
   ├─ Saves Changes
   │  ├─ Click "Save Context" button
   │  ├─ Success message appears ✅
   │  └─ Database updated immediately
   │
   ├─ Tests in Chat
   │  ├─ Go to Chat tab
   │  ├─ Ask AI a question
   │  └─ AI uses NEW context
   │
   └─ Can Revert Anytime
      ├─ Click "Reset to Default"
      ├─ Confirm in dialog
      └─ Context reverts to original
```

## 🔑 Key Information

```
🔐 Access Control
   └─ Admin users only
   └─ Enforced on backend

📝 What Gets Saved
   ├─ System instructions
   ├─ Response rules
   ├─ Business rules
   ├─ Data isolation rules
   ├─ Vocabulary
   ├─ Timestamp of change
   └─ Who made the change (user ID)

⏱️ When Changes Apply
   └─ Immediately to NEW conversations
   └─ Does NOT affect existing conversations
   └─ Can reset anytime

🔄 Fallback System
   ├─ Checks database first
   ├─ Falls back to hardcoded default if needed
   └─ App never breaks

📊 Audit Trail
   ├─ Shows when context was last updated
   ├─ Shows who updated it
   └─ Timestamp always visible
```

## 🎯 Common Tasks

### Change AI Tone
```
1. Open Settings → AI Context
2. Go to System Instructions tab
3. Find: "Write as if a knowledgeable teammate"
4. Change to: "Write in a friendly, casual tone"
5. Click "Save Context" ✅
6. Ask AI a question in Chat
7. AI responds with new tone
```

### Add New Business Rule
```
1. Open Settings → AI Context
2. Click "Business Rules" tab
3. Type: "All dates must be in MM/DD/YYYY format"
4. Click "Save Context" ✅
5. Ask AI to provide dates
6. AI formats dates per your rule
```

### Revert Bad Changes
```
1. Open Settings → AI Context
2. Click "Reset to Default"
3. Confirm the action
4. Context reverts ✅
5. AI back to original behavior
```

### Backup Instructions
```
1. Open Settings → AI Context
2. Click any [Copy] button
3. Paste into text file/email
4. Save as backup
```

## 🚀 First-Time Setup

No setup needed! On first app startup:

```
App Starts
   ↓
Create ai_context table (if not exists)
   ↓
Load existing CLIENTSHOT_SYSTEM_INSTRUCTIONS
   ↓
Create initial AIContext record
   ↓
Mark as is_active=True
   ↓
Ready for admin to use ✅
```

## 📱 Mobile Responsiveness

Works on all screen sizes:
- ✅ Desktop - Full featured
- ✅ Tablet - Optimized layout
- ✅ Mobile - Scrollable areas

## 🎨 Visual Indicators

```
Tab Colors:
├─ Active Tab:   Blue border, bold text
├─ Inactive Tab: Gray text, no border
└─ Icons:        ⚡ Zap for AI Context

Message Types:
├─ Success: 🟢 Green background, checkmark
├─ Error:   🔴 Red background, X mark
└─ Info:    🔵 Blue background, info icon

Buttons:
├─ Save:    Primary (blue), with save icon 💾
├─ Reset:   Secondary (gray), with refresh icon 🔄
└─ Copy:    Icon only (clipboard) 📋
```

## 📊 Data Flow Diagram

```
Admin Edits Context
        │
        ↓
     Frontend
   React Component
        │
        ↓
   POST /api/settings/ai-context
        │
        ↓
      Backend
   Flask Endpoint
        │
        ├─ Check Admin Auth ✅
        ├─ Save to Database
        ├─ Deactivate Old Context
        └─ Activate New Context
        │
        ↓
   Database
   ai_context table
        │
        ↓
   Response to Frontend
        │
        ↓
   Success Message 🎉
        │
        ↓
   New Chat Message
        │
        ↓
   responder.py
   get_system_instructions()
        │
        ├─ Query: Active Context? ✅
        └─ Use from Database
        │
        ↓
   LLM Request
   With NEW system prompt
        │
        ↓
   AI Response
   Using NEW context
```

## 🔍 What Admin Sees at Each Step

### Before Saving
```
Text Area: [Original instructions]
Button: [💾 Save Context]
Status: Not modified
```

### While Saving
```
Text Area: [Instructions]
Button: [💾 Save Context] (disabled, spinning)
Status: Saving...
```

### After Saving
```
Text Area: [Saved instructions]
Button: [💾 Save Context] (enabled)
Status: ✅ AI context saved successfully
Time:   Last updated: Jan 15, 2024 at 2:30 PM
```

## 🎓 Learning Resources

For more information, see:
- **USER_EXPERIENCE_GUIDE.md** - Detailed usage guide
- **AI_CONTEXT_GUIDE.md** - Complete reference
- **TECHNICAL_CHANGES.md** - How it works technically

## ✨ Feature Highlights

```
✅ Complete Transparency
   └─ All AI instructions visible in one place

✅ Full Control
   └─ Change any aspect without code

✅ Immediate Impact
   └─ Changes apply to next conversation

✅ Easy Revert
   └─ One-click reset to defaults

✅ Audit Trail
   └─ Track who changed what and when

✅ Organized
   └─ 5 logical sections for easy management

✅ Secure
   └─ Admin-only access enforced

✅ Reliable
   └─ Fallback ensures app always works
```

---

**Everything is ready! 🚀 Admin can start managing AI context immediately.**
