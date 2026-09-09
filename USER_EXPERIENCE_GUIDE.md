# AI Context Management - User Experience Guide

## What Users (Admins) Will See

### Accessing the Feature

1. **Click Settings** (gear icon in top navigation)
2. **Look for "AI Context" tab** (with a lightning bolt ⚡ icon)
3. **Click the tab** to open AI Context Management panel

---

## The AI Context Panel

### Main Interface

```
┌─ Settings ─────────────────────────────────────────────────┐
│ LLM Config | DB Config | ... | AI Context ⚡ | Audit Logs  │
└────────────────────────────────────────────────────────────┘

AI Context Management
Configure all system instructions and context that the AI will use. 
No more hidden context — manage everything here.

┌─ Tabs ──────────────────────────────────────────────────────┐
│ System | Response Rules | Business Rules | Data Isolation | Vocabulary │
└────────────────────────────────────────────────────────────┘

[Large text area with current system instructions...]

[Copy] [Save Context] [Reset to Default]

Last updated: Jan 15, 2024 at 2:30 PM
```

---

## The 5 Sections

### 1. **System Instructions** (Default Tab)

**What is it?**
The main system prompt that's sent to the AI with every request.

**What admin sees:**
- A large text area with 1000+ lines of instructions
- Instructions start with "You are the Clientshot AI Assistant..."
- Includes all response rules, business rules, vocabulary, etc.

**What can admin do?**
- Edit the entire prompt
- Change the tone (e.g., make it more casual)
- Add new rules or constraints
- Remove parts they don't want
- Copy the entire text to clipboard

**Example change:**
```
Before: "You are the Clientshot AI Assistant..."
After: "You are a helpful data analyst for my company..."
```

---

### 2. **Response Rules** (Optional)

**What is it?**
Guidelines for how responses should be formatted and presented.

**What admin sees:**
- Empty by default (optional field)
- Can add custom formatting rules

**What can admin do?**
- Specify JSON format requirements
- Define table output rules
- Customize response structure
- Set tone/style guidelines

**Example content:**
```
- Always respond in JSON format
- Include confidence score for predictions
- Sort results by relevance
- Limit responses to 500 characters
```

---

### 3. **Business Rules** (Optional)

**What is it?**
Business logic and constraints the AI must follow.

**What admin sees:**
- Empty by default (optional field)
- Can add industry-specific rules

**What can admin do?**
- Define business constraints
- Add compliance requirements
- Specify validation rules
- Set data handling policies

**Example content:**
```
- Complaints cannot be reopened once resolved
- NPS must use the formula: (Promoters - Detractors) / Total * 100
- User must only see their company's data
- Financial data must be masked in logs
```

---

### 4. **Data Isolation** (Optional)

**What is it?**
Rules for multi-tenant data filtering and security.

**What admin sees:**
- Empty by default (optional field)
- Can define isolation rules

**What can admin do?**
- Specify company filtering rules
- Define branch-level access
- Set role-based data visibility
- Document security constraints

**Example content:**
```
- Always filter by user's company_id
- Branch admins see only their branch
- Central admins see all branches
- Users cannot see other users' data
```

---

### 5. **Vocabulary** (Optional)

**What is it?**
Terminology definitions for consistent language.

**What admin sees:**
- Empty by default (optional field)
- Can define key terms

**What can admin do?**
- Define industry vocabulary
- Set terminology standards
- Map terms to definitions
- Create glossary

**Example content:**
```
- Tenant = single organization (company/workspace)
- Branch = division within company
- Service Point = customer touchpoint
- NPS = Net Promoter Score
- Promoter = customer with score 9-10
```

---

## Action Buttons

### Save Context Button
- **What it does**: Saves all changes immediately
- **Where it appears**: Bottom of panel
- **What happens after clicking**:
  1. Green banner appears: "AI context saved successfully"
  2. All new AI responses use the new context
  3. Previous conversations are not affected
  4. Timestamp updates to current time

### Reset to Default Button
- **What it does**: Reverts context to built-in instructions
- **Where it appears**: Bottom of panel, next to Save
- **What happens after clicking**:
  1. Confirmation dialog appears
  2. Must confirm the action (with warning)
  3. Context reverts to original instructions
  4. Green banner: "AI context reset to default"

---

## Information Display

### Last Updated Section
```
Last updated: Jan 15, 2024 at 2:30 PM
```
Shows when the context was last modified.

### How It Works Info Box
```
ℹ️ How This Works
• System Instructions: Sent to the LLM as the system message
• Response Rules: Guidelines for formatting and style (optional)
• Business Rules: Constraints and business logic (optional)
• Data Isolation: Multi-tenant filtering rules (optional)
• Vocabulary: Terminology definitions (optional)
• All changes apply to new AI responses immediately
• Previous conversations are not affected
```

---

## Typical User Journey

### Scenario 1: Adjusting AI Tone

1. Admin opens Settings → AI Context
2. Sees System Instructions (default tab)
3. Finds line: "Write as if a knowledgeable teammate is responding"
4. Changes to: "Write in a friendly, casual tone with humor"
5. Clicks "Save Context"
6. Green success message appears
7. Goes to Chat, AI now responds with new tone

### Scenario 2: Adding New Business Rule

1. Admin opens Settings → AI Context
2. Clicks "Business Rules" tab
3. Clicks in empty text area
4. Types new rule: "All monetary values must include currency symbol"
5. Clicks "Save Context"
6. Success message appears
7. AI now includes currency symbols in responses

### Scenario 3: Experimenting and Reverting

1. Admin makes multiple changes
2. Tests in Chat, doesn't like the results
3. Returns to Settings → AI Context
4. Clicks "Reset to Default"
5. Confirms in dialog
6. Context reverts instantly
7. AI back to original behavior

---

## Error Scenarios

### "AI context saved successfully" ✅
**What it means**: Changes were saved. All new AI responses use new context.

### "Only admins can access AI context settings" ❌
**What it means**: User doesn't have admin role. Contact admin for access.

### "System instructions cannot be empty" ❌
**What it means**: Main system instructions field is required. Add content before saving.

### "AI context not found" ❌
**What it means**: Database error. Contact support if persists.

---

## Key Behaviors to Know

1. **Changes apply immediately**
   - No restart needed
   - Affects only new conversations
   - Old conversations keep old context

2. **Only one context is active**
   - Creating new context deactivates old one
   - Resetting creates new default, deactivates current

3. **Copy button available**
   - Click copy icon to copy section to clipboard
   - Useful for backups or sharing

4. **Optional fields**
   - Response Rules, Business Rules, Data Isolation, Vocabulary are optional
   - System Instructions is required
   - Admin can leave optional fields empty

5. **Audit trail maintained**
   - App tracks who changed context and when
   - Timestamp shows last update

---

## Tips for Admins

### ✅ Best Practices

1. **Read before editing**
   - Understand current instructions before changing
   - Use copy button to save backup

2. **Test changes**
   - Make small changes, test in Chat
   - Revert if not working as expected

3. **Document changes**
   - Note why you're changing context
   - This helps future troubleshooting

4. **Use sections logically**
   - System Instructions: Overall behavior
   - Response Rules: Format/style
   - Business Rules: Constraints
   - Data Isolation: Security
   - Vocabulary: Terms

### ⚠️ Be Careful With

1. **Removing important rules**
   - Rules are there for a reason
   - Removing them may cause problems

2. **Changing data isolation**
   - Wrong rules could expose data across organizations
   - Be very careful with tenant/company filtering

3. **Making context too long**
   - Very long prompts cost more in API tokens
   - Keep it concise where possible

4. **Testing in production**
   - Always test in staging/dev first if possible
   - Changes affect all users immediately

---

## FAQ (What Admins Might Ask)

**Q: Will my changes affect existing conversations?**
A: No. Only new conversations use the updated context. Old ones keep their original context.

**Q: Can I see what context was used for a past conversation?**
A: Not currently, but the same context is used for all new messages in that conversation.

**Q: What if I make a mistake?**
A: Click "Reset to Default" to revert to the built-in instructions.

**Q: Can I save multiple versions?**
A: Currently only one active context. Use the copy button to manually backup text.

**Q: How often should I update the context?**
A: As needed. Change it when AI behavior needs adjustment, rules change, etc.

**Q: What happens if I leave optional fields empty?**
A: That's fine. Only System Instructions is required. Optional fields are supplementary.

**Q: Can regular users see the AI context?**
A: No. This panel is admin-only. Users just see AI responses.

**Q: Do I need to restart the app after saving?**
A: No. Changes take effect immediately.

---

## Visual Flow

```
Settings Page
    ↓
Click "AI Context" Tab
    ↓
Panel Opens
    ├─ 5 Sections (System, Rules, Business, Isolation, Vocab)
    ├─ Admin reads/edits content
    └─ Click Actions
       ├─ Save Context
       │  └─ Green success message
       │     └─ New conversations use new context
       │
       └─ Reset to Default
          └─ Confirmation dialog
             └─ Context reverts
                └─ Green success message
```

---

## After Saving

The flow when admin saves:

```
Admin clicks "Save Context"
    ↓
Frontend validates (not empty)
    ↓
POST /api/settings/ai-context
    ↓
Backend checks admin authorization
    ↓
Backend saves to ai_context table
    ↓
Frontend receives success response
    ↓
Green banner shows: "AI context saved successfully"
    ↓
Next chat message uses NEW context
    ↓
Previous conversations unchanged
```

---

## Summary

The AI Context Management feature gives admins complete visibility and control over AI system instructions. 

**Key Points:**
- ✅ All instructions now editable (no hidden context)
- ✅ Organized into 5 logical sections
- ✅ Admin-only access (secure)
- ✅ Changes apply immediately
- ✅ Easy to revert to defaults
- ✅ No code changes needed

**What's the outcome for users?**
- AI behavior can be customized without developer involvement
- All control points are transparent and auditable
- Changes can be tested and reverted quickly
- Company-specific rules can be enforced

---

**Ready to use!** 🚀

No additional setup needed. Just log in as admin, go to Settings, click "AI Context" tab, and start managing your AI instructions.
