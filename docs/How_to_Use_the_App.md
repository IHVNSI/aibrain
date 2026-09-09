# How to Use the App

Welcome to the **Assistant AI** application! This guide will walk you through everything you need to know to effectively use the app, configure it for your needs, and leverage all available features.

## Table of Contents

1. [What is Assistant AI?](#what-is-assistant-ai)
2. [Key Features](#key-features)
3. [Getting Started](#getting-started)
4. [Navigation and Layout](#navigation-and-layout)
5. [The Chat Interface](#the-chat-interface)
6. [Voice Input Guide](#voice-input-guide)
7. [Conversations and History](#conversations-and-history)
8. [Settings and Audio Configuration](#settings-and-audio-configuration)
9. [Tips and Best Practices](#tips-and-best-practices)
10. [Troubleshooting](#troubleshooting)

---

## What is Assistant AI?

Assistant AI is an intelligent conversational platform that combines **text-to-SQL generation**, **knowledge base management**, and **natural language understanding** to help you interact with your data in a natural way. Whether you're querying databases, uploading documents for reference, or having natural conversations, this app provides a seamless experience.

The app is powered by advanced language models (LLMs) and can intelligently route your queries to the most appropriate source: your database, uploaded knowledge base files, or direct conversational responses.

---

## Key Features

### 1. **Natural Language Querying**
Ask questions about your data in plain English, and the app will generate and execute the appropriate SQL queries against your database.

**Example:** "What were the total sales for Q1 2025?" → Automatically generates SQL and retrieves results.

### 2. **Multi-Source Query Routing**
The app intelligently determines whether to:
- Query your **database** (for structured data queries)
- Search your **knowledge base** (for document-based information)
- Provide a **direct response** (for general questions)

Database queries are always prioritized when applicable.

### 3. **Voice Input Support**
- **Speak your queries** instead of typing
- **Manual text editing** during voice listening
- **Clear Text command** to remove errors
- **Voice settings** for customization (gender, pitch, rate, volume)

### 4. **Knowledge Base Management**
Upload and organize documents for reference:
- **Word documents** (.docx)
- **Excel spreadsheets** (.xlsx)
- **PowerPoint presentations** (.pptx)
- **PDFs** (.pdf)
- **Images** (.png, .jpg)

### 5. **Conversation Persistence**
- **Unlimited conversations** stored in your database
- **Full chat history** with all responses, queries, and visualizations
- **Editable conversation titles** for easy organization
- **Searchable history**

### 6. **Data Visualization**
Charts and visualizations automatically render for query results when applicable:
- Bar charts
- Line charts
- Pie charts
- Trend analysis

### 7. **Audio Playback**
The app can **read responses aloud** with customizable voice settings (gender, pitch, rate, volume).

### 8. **Database-Backed Settings**
All your preferences are saved to the database:
- Audio settings persist across sessions
- Conversation titles stored server-side
- No browser memory dependency

---

## Getting Started

### Step 1: Login

1. Open the app in your browser
2. Enter your credentials:
   - **Email:** Your registered email address
   - **Password:** Your password
3. Click **"Login"** or press **Enter**

**Demo/Guest Access:**
- **Email:** `guest@guest.com`
- **Password:** `Guest123`

### Step 2: Understand the Layout

The app has three main sections:

| Section | Purpose |
|---------|---------|
| **Left Sidebar** | Conversation history and management |
| **Main Chat Area** | Message display and interaction |
| **Top Navigation** | Access to Settings and app controls |

### Step 3: Start Your First Chat

1. Click **"New Chat"** or begin typing in the message input box
2. Type or speak your query
3. Press **Enter** or click **Send** to submit
4. The app will process and respond with:
   - Generated SQL (if applicable)
   - Query results
   - Visualizations (if applicable)

---

## Navigation and Layout

### Left Sidebar - Conversation History

**Features:**
- Lists all your past conversations
- Click any conversation to load its history
- **Hover over conversation** to reveal options:
  - ✏️ **Edit** - Rename the conversation title
  - 🗑️ **Delete** - Remove the conversation
- **New Chat** button at the top to start fresh conversation

**Editing Conversation Titles:**
1. Hover over any conversation in the sidebar
2. Click the **pencil icon** (✏️)
3. Enter the new title
4. Click **Save** to persist changes or **Cancel** to discard
5. Title changes are saved to your database immediately

### Top Navigation Bar

- **Settings icon (⚙️)** - Access application settings
- **User profile** - View your account info
- **Logout** - Sign out of the app

### Main Chat Area

**Components:**
- **Message bubbles** - Your queries and AI responses
- **Message input box** - Type or speak your query
- **Voice input controls** - Microphone and audio settings
- **Visualization panels** - Charts and data displays

---

## The Chat Interface

### Sending a Message

**Text Input:**
1. Click in the message input field at the bottom
2. Type your query
3. Press **Enter** or click the **Send button** (arrow icon)

**Voice Input:**
1. Click the **microphone icon** 🎤
2. Speak clearly into your device's microphone
3. The app will transcribe your speech in real-time
4. Speak your full query, then stop
5. The app will automatically send after listening ends

### Understanding the Response

Each response includes:

| Element | Description |
|---------|-------------|
| **Message text** | The AI's response or explanation |
| **SQL Query** | If a database query was made, you'll see the generated SQL |
| **Results table** | Data returned from your database |
| **Visualization** | Charts (bar, line, pie) if the data is suitable |
| **Insights** | Key observations about the data |
| **Trend analysis** | If applicable, trend information |

### Response Actions

- **🔊 Speaker icon** - Listen to the response (uses your audio settings)
- **⏹️ Stop button** - Stop current audio playback (appears above speaker during playback)
- **📋 Copy** - Copy the response text
- **⬇️ Download** - Download data/visualization (if available)

---

## Voice Input Guide

### Starting Voice Input

1. **Click the microphone icon** 🎤 in the message input area
2. You'll see a visual indicator showing the app is **listening**
3. **Speak clearly** - The transcription appears in real-time

### Voice Input Features

#### Manual Text Editing During Listening

While the app is listening and transcribing:
1. **Manually edit** the transcribed text in the input box
2. The app detects that you've made manual changes
3. When you send, your **manually edited text is used** (not the speech-to-text result)
4. This is useful for correcting transcription errors

#### Clear Text Command

During voice listening, you can say:
- **"Clear text"** - Removes all accumulated voice input
- This is useful if the transcription becomes too error-prone
- Starts fresh for a new query

#### Voice Settings

Configure your microphone and audio playback:
1. Go to **Settings** (⚙️)
2. Click the **Audio** tab
3. Adjust:
   - **Microphone sensitivity** - Threshold for silence detection
   - **Voice gender** - For text-to-speech playback (Male/Female)
   - **Pitch** - Higher or lower voice (0.5 to 2.0)
   - **Speaking rate** - Faster or slower speech (0.5 to 2.0)
   - **Volume** - Loudness of audio playback (0.0 to 1.0)
   - **Auto-speak** toggle - Automatically read responses aloud

### Best Practices for Voice Input

✅ **Do:**
- Speak at a natural pace
- Use clear pronunciation
- Minimize background noise
- Complete your full query before stopping

❌ **Don't:**
- Whisper or speak too loudly
- Mumble or have unclear pronunciation
- Interrupt mid-sentence
- Speak too quickly without clear pauses

---

## Conversations and History

### Managing Your Conversations

**View History:**
- All your conversations appear in the left sidebar
- Click any conversation to load its full history
- Each message shows the timestamp and full response

**Search History:**
- Use browser search (Ctrl+F) to find content in current conversation
- Or check **Settings → Conversations** tab for advanced search

**Edit Conversation Titles:**
1. Hover over a conversation name in the sidebar
2. Click the **pencil icon** (✏️)
3. Enter new title
4. Click **Save** or press **Enter**
5. Changes are immediately saved to the database

**Delete Conversations:**
1. Hover over a conversation name
2. Click the **trash icon** (🗑️)
3. Confirm deletion
4. Conversation is permanently removed

**Bulk Actions:**
- Visit **Settings → Conversations** tab for advanced management
- Archive, search, or manage multiple conversations
- View conversation metadata

---

## Settings and Audio Configuration

### Accessing Settings

1. Click the **Settings icon** (⚙️) in the top navigation
2. Multiple tabs available for different settings

### Audio Tab

**Configure voice input and playback:**

| Setting | Purpose | Default |
|---------|---------|---------|
| **Microphone Sensitivity** | How sensitive the microphone is to sound | 0.5 |
| **Voice Gender** | Gender of text-to-speech voice | Female |
| **Pitch** | Voice pitch for audio playback | 1.0 |
| **Speaking Rate** | Speed of audio playback | 1.0 |
| **Volume** | Loudness of audio output | 1.0 |
| **Auto-speak** | Automatically read AI responses aloud | Off |

**How to change audio settings:**
1. Go to **Settings → Audio**
2. Adjust sliders or toggle switches
3. Changes auto-save to the database
4. Settings persist across all sessions

### Database Configuration Tab

View your source database connection details and validate connectivity.

### LLM Configuration Tab

See which language model provider is being used (OpenAI, Google Gemini, Anthropic Claude, or Hugging Face).

### Vector Store Tab

View which vector database is storing your knowledge base (ChromaDB, FAISS, or Pinecone).

### Security Tab

Review authentication methods and security policies.

---

## Tips and Best Practices

### For Better Database Queries

1. **Be specific** - "Show me Q1 2025 sales by region" instead of "Show me sales"
2. **Use natural language** - The SQL is generated automatically, don't worry about syntax
3. **Reference column names** if you know them - "What is the total of the 'revenue' column?"
4. **Ask follow-ups** - "What about last year?" builds on previous context

### For Voice Input

1. **Enable auto-speak** in Audio settings if you prefer hands-free interaction
2. **Test voice settings** first - Click the speaker icon to hear a sample
3. **Use Clear Text** when transcription becomes unclear
4. **Manually edit** if you notice transcription errors while speaking
5. **Speak in short queries** for better accuracy

### For Organizing Conversations

1. **Name conversations descriptively** - Use the edit feature to create meaningful titles
2. **Delete old conversations** when they're no longer needed to keep sidebar clean
3. **Keep related queries together** in one conversation thread

### For Productivity

1. **Enable auto-speak** for listening while multitasking
2. **Use voice input** while your hands are busy
3. **Save conversation titles** that represent projects or tasks
4. **Reference previous messages** - Scroll up in the conversation to see past context

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "No results found" or "Query failed"

**Possible causes:**
- The table or column name doesn't exist
- Syntax in the generated SQL is incorrect
- Database connection is down

**Solutions:**
1. Rephrase your query more simply
2. Check the generated SQL in the response - does it look correct?
3. Go to **Settings → DB Config** to verify database connection
4. Try a simpler query like "How many records are in the main table?"

#### Issue: Voice input not working

**Possible causes:**
- Microphone not connected or enabled
- Browser permission denied for microphone
- Audio input device not properly configured

**Solutions:**
1. Check your system microphone settings
2. Grant microphone permission to the browser when prompted
3. Go to **Settings → Audio** and check microphone sensitivity
4. Test with a simpler voice command
5. Try a different browser if issue persists

#### Issue: Charts/Visualizations not displaying

**Possible causes:**
- Data format not suitable for visualization
- Browser rendering issue
- Page refresh lost the data

**Solutions:**
1. Refresh the page (Ctrl+R) - data persists in database
2. Re-run the query
3. Check if data has multiple columns (needed for charts)
4. Try a different chart type by modifying your query

#### Issue: Audio playback not working

**Possible causes:**
- Volume muted or set to 0
- System audio disabled
- Browser audio permissions denied
- Audio output device not connected

**Solutions:**
1. Check volume in **Settings → Audio** (set to 1.0)
2. Check system volume settings
3. Verify speakers/headphones are connected
4. Grant audio permission in browser settings
5. Test by clicking the speaker icon to hear audio

#### Issue: "Access Denied" or permission errors

**Possible causes:**
- You're a guest user with limited access
- Training data requires higher permissions
- Knowledge base content restricted to authenticated users

**Solutions:**
1. Login with your full account (not guest)
2. Check with admin for appropriate permissions
3. Restricted training data shows `[ACCESS:AUTHENTICATED]` marker
4. Guest account has demo access only

#### Issue: Settings not persisting

**Possible causes:**
- LocalStorage issues
- Database connection problem
- Session timeout

**Solutions:**
1. Try reloading the page (Ctrl+R)
2. Check **Settings** to verify changes were saved
3. Login again to refresh session
4. Check browser console (F12) for error messages
5. Contact admin if database is unreachable

#### Issue: Conversation history not showing

**Possible causes:**
- No conversations yet (first time user)
- Conversations were deleted
- Database issue

**Solutions:**
1. Start a new chat to create first conversation
2. Refresh page (Ctrl+R)
3. Logout and login again
4. Check **Settings → Conversations** for all conversations
5. Verify database connection in **Settings → DB Config**

#### Issue: Slow response times

**Possible causes:**
- Complex query requires time to execute
- Large dataset being processed
- Network latency
- LLM API slow response

**Solutions:**
1. Be more specific in your query to reduce data
2. Add time filters (e.g., "for the last month")
3. Check your internet connection
4. Try simplifying the query
5. Check **Settings → LLM Config** to verify LLM provider

---

## Next Steps

### Ready to explore more?

- **Configure your audio** in Settings → Audio tab
- **Upload knowledge base documents** in Settings → Training / RAG tab
- **Review security settings** in Settings → Security tab
- **Set up database connection** in Settings → DB Config tab
- **Explore advanced features** in other Settings tabs

### Need more help?

- Check other documentation guides (coming in next sections)
- Review **Settings → API DOC** for technical details
- Contact your administrator for account-specific questions

---

**Happy querying! 🚀**
