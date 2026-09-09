# AI Context Management Feature

## Overview
The AI Context Management feature allows admins to configure all system instructions and context that the AI uses, eliminating hidden hardcoded context. Everything is now editable through a dedicated Settings panel.

## What's New

### 1. **New Settings Tab: "AI Context"**
Located in Settings (gear icon), the "AI Context" tab provides a dedicated interface for managing AI behavior.

### 2. **Five Editable Sections**
- **System Instructions**: Main system prompt (sent with every LLM request)
- **Response Rules**: Guidelines for formatting and tone
- **Business Rules**: Business logic and constraints
- **Data Isolation**: Multi-tenant filtering rules
- **Vocabulary**: Terminology definitions for consistent language

### 3. **Admin-Only Access**
- Only admins (is_admin or is_central_admin) can access and modify AI context
- Changes are logged with timestamp and admin user ID

### 4. **Pre-Populated with Existing Context**
On first run, the AI Context is automatically populated with the existing `CLIENTSHOT_SYSTEM_INSTRUCTIONS` from `response_guide.py`.

## How It Works

### Database Storage
- New table: `ai_context` in the admin database
- Stores all system instructions and context
- Tracks who updated it and when

### Dynamic Loading
- `responder.py` now calls `get_system_instructions()` 
- This function checks the database for active context
- Falls back to hardcoded default if database unavailable
- No performance impact due to simple query

### Initialization
- On app startup, if no active AI context exists, one is created automatically
- Uses the existing `CLIENTSHOT_SYSTEM_INSTRUCTIONS` as the default

## API Endpoints

### GET `/api/settings/ai-context`
Fetch the currently active AI context.

**Response:**
```json
{
  "success": true,
  "context": {
    "id": 1,
    "name": "default",
    "is_active": true,
    "system_instructions": "You are the Clientshot AI Assistant...",
    "response_rules": "...",
    "business_rules": "...",
    "data_isolation_rules": "...",
    "vocabulary": "...",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T11:45:00",
    "updated_by": 1
  }
}
```

### POST `/api/settings/ai-context`
Create or update AI context.

**Request:**
```json
{
  "id": 1,  // Optional - if updating existing
  "name": "default",
  "system_instructions": "Your prompt here",
  "response_rules": "...",
  "business_rules": "...",
  "data_isolation_rules": "...",
  "vocabulary": "..."
}
```

### POST `/api/settings/ai-context/default`
Reset to the built-in default instructions with confirmation.

## UI Features

### Main Panel
- 5 tabs for different context sections
- Large textarea for editing instructions
- Real-time character count
- Copy-to-clipboard button for each field

### Action Buttons
- **Save Context**: Saves all changes and activates immediately
- **Reset to Default**: Reverts to built-in instructions (with confirmation)

### Information Display
- Shows when context was last updated
- Shows which admin updated it
- Helpful tips about each section

## Usage

### For Admins

1. Go to **Settings** → **AI Context** tab
2. Edit any of the 5 sections:
   - Modify System Instructions for overall AI behavior
   - Update Response Rules for formatting
   - Add Business Rules for constraints
   - Configure Data Isolation rules
   - Define Vocabulary
3. Click **Save Context** to apply changes
4. New conversations will immediately use updated context

### To Reset
1. Click **Reset to Default** button
2. Confirm in the dialog
3. Context reverts to built-in instructions

## Technical Details

### Database Schema
```sql
CREATE TABLE ai_context (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    system_instructions TEXT NOT NULL,
    response_rules TEXT,
    business_rules TEXT,
    data_isolation_rules TEXT,
    vocabulary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER FOREIGN KEY
)
```

### How System Instructions Are Used

**In responder.py:**
```python
system_instructions = get_system_instructions()  # Loads from DB or falls back
text = llm.chat([
    {"role": "system", "content": system_instructions},
    {"role": "user", "content": situation},
])
```

### Fallback Behavior
If database is unavailable:
1. `AIContext.get_active()` returns None
2. Function falls back to `CLIENTSHOT_SYSTEM_INSTRUCTIONS` from response_guide.py
3. App continues without interruption
4. Warning is logged

## Benefits

✅ **Transparency**: All AI instructions are now visible and editable
✅ **Control**: Admins can adjust AI behavior without code changes
✅ **Flexibility**: Support for multiple context sections
✅ **Safety**: Admin-only access, no data leakage between sections
✅ **Reliability**: Fallback ensures app works if DB is temporarily unavailable
✅ **Audit Trail**: Tracks who changed what and when
✅ **Easy Reset**: Can always revert to known-good defaults

## Common Use Cases

### Adjust AI Tone
Edit the System Instructions to change from professional to casual, etc.

### Add New Business Rules
Add rules to Data Isolation Rules for tenant-specific constraints

### Define Industry Vocabulary
Use Vocabulary section to ensure consistent terminology

### Update Response Format
Modify Response Rules for different output formats

### Experiment Safely
Try different context configurations without affecting old conversations

## Migration from Hardcoded Context

1. On first app startup, system automatically creates AI Context with existing instructions
2. Admin can then edit context through UI
3. Old `CLIENTSHOT_SYSTEM_INSTRUCTIONS` in `response_guide.py` becomes fallback
4. No manual data migration needed

## Troubleshooting

### Context not loading
- Check app logs for database errors
- Verify admin database is accessible
- Check if user has admin role

### Changes not applying
- Ensure you clicked "Save Context" button
- Check browser console for API errors
- Verify admin permissions

### Need to see current context
- Go to AI Context tab
- Each section shows the currently active text
- Use Copy button to view in external editor

## Future Enhancements

Potential future additions:
- Version history/rollback
- A/B testing different contexts
- Context templates for different use cases
- Import/export context configurations
- Context validation/preview
