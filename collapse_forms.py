#!/usr/bin/env python3
"""
Script to modify WhatsAppWebTab.jsx to add collapsible form sections
"""
import re

file_path = "frontend/src/components/WhatsAppWebTab.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: Find and replace the Direct AI Message Handler header and opening
# Look for the exact pattern with the emoji
pattern1 = re.compile(
    r'<h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-purple-900">\s*'
    r'<MessageSquare size=\{18\} />\s*'
    r'Direct AI Message Handler\s*'
    r'</h3>\s*'
    r'<p className="text-sm text-purple-700 mb-4">.*?Manually process WhatsApp messages with AI and generate smart responses\s*</p>\s*'
    r'<div className="space-y-4">',
    re.DOTALL
)

replacement1 = '''<button
                  onClick={() => setAiFormOpen(!aiFormOpen)}
                  className="w-full flex items-center justify-between mb-4 hover:opacity-80 transition"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2 text-purple-900">
                    <MessageSquare size={18} />
                    Direct AI Message Handler
                  </h3>
                  <ChevronDown
                    size={20}
                    className={`text-purple-900 transition-transform ${aiFormOpen ? 'rotate-180' : ''}`}
                  />
                </button>
                <p className="text-sm text-purple-700 mb-4">
                  Manually process WhatsApp messages with AI and generate smart responses
                </p>
                
                {aiFormOpen && (
                <div className="space-y-4">'''

content = re.sub(pattern1, replacement1, content)

print(f"Replaced Direct AI header: {'✓' if 'aiFormOpen' in content else '✗'}")

# Pattern 2: Find the closing of the form inputs (before {/* Pending AI Responses */})
# and add the conditional close
pattern2 = re.compile(
    r'(                  </button>\s*</div>)\s*'
    r'(\n\s*{/\* Pending AI Responses \*/})',
    re.DOTALL
)

replacement2 = r'\1\n                )}\n                \2'

content = re.sub(pattern2, replacement2, content)

print(f"Wrapped form inputs: {'✓' if content.count('{aiFormOpen &&') >= 1 else '✗'}")

# Pattern 3: Find and replace the Send Message form
pattern3 = re.compile(
    r'{/\* Send Message Section \*/}\s*'
    r'<div className="bg-gray-50 p-6 rounded-lg">\s*'
    r'<h3 className="text-lg font-semibold mb-4 flex items-center gap-2">\s*'
    r'<Send size=\{18\} />\s*'
    r'Send Message\s*'
    r'</h3>\s*'
    r'<form onSubmit=\{handleSendMessage\} className="space-y-4">',
    re.DOTALL
)

replacement3 = '''{/* Send Message Section */}
              <div className="bg-gray-50 p-6 rounded-lg">
                <button
                  onClick={() => setSendFormOpen(!sendFormOpen)}
                  className="w-full flex items-center justify-between mb-4 hover:opacity-80 transition"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Send size={18} />
                    Send Message
                  </h3>
                  <ChevronDown
                    size={20}
                    className={`text-gray-700 transition-transform ${sendFormOpen ? 'rotate-180' : ''}`}
                  />
                </button>
                
                {sendFormOpen && (
                <form onSubmit={handleSendMessage} className="space-y-4">'''

content = re.sub(pattern3, replacement3, content)

print(f"Replaced Send Message header: {'✓' if 'setSendFormOpen' in content else '✗'}")

# Pattern 4: Close the Send Message form conditional
pattern4 = re.compile(
    r'(                  </button>\s*</form>)\s*'
    r'</div>\s*'
    r'(\n\s*{/\* Recent Chats Messages \*/})',
    re.DOTALL
)

replacement4 = r'\1\n                )}\n              </div>\n\2'

content = re.sub(pattern4, replacement4, content)

print(f"Wrapped send form: {'✓' if content.count('{sendFormOpen &&') >= 1 else '✗'}")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ Successfully modified WhatsAppWebTab.jsx")
print("- Added collapsible Direct AI Message Handler form")
print("- Added collapsible Send Message form")
print("- Forms now hidden by default")
