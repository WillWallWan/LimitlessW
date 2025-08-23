#!/usr/bin/env python3
"""
Claude Gentle Summary - Rate-limit friendly version

Processes conversations in smaller batches to respect Claude's rate limits.
Perfect for getting started with Claude analysis.
"""

import os
import time
from anthropic import Anthropic
from dotenv import load_dotenv
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def summarize_small_batch(lifelogs):
    """Summarize a small batch of conversations with Claude"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY in your .env file")
        return
    
    client = Anthropic(api_key=api_key)
    
    # Prepare a concise version of conversations
    conversation_summary = ""
    for i, lifelog in enumerate(lifelogs[:3], 1):  # Just first 3 conversations
        title = lifelog.get('title', f'Conversation {i}')
        time_str = lifelog.get('startTime', 'Unknown time')
        
        # Get just the first 200 characters of markdown for summary
        content = lifelog.get('markdown', '')[:200]
        if len(lifelog.get('markdown', '')) > 200:
            content += "..."
        
        conversation_summary += f"{i}. **{title}** ({time_str})\n   {content}\n\n"
    
    prompt = f"""Please provide a brief summary of these recent conversations:

{conversation_summary}

Focus on:
- Key topics discussed
- Any action items mentioned
- Overall themes

Keep it concise (2-3 paragraphs max)."""

    try:
        print("🤖 Claude is analyzing your conversations (gentle mode)...\n")
        
        # Use a smaller model and shorter response
        message = client.messages.create(
            model="claude-3-haiku-20240307",  # Faster, cheaper model
            max_tokens=300,  # Shorter response
            messages=[{"role": "user", "content": prompt}]
        )
        
        print("📋 **Summary:**")
        print("=" * 40)
        print(message.content[0].text)
        print("=" * 40)
        
        return message.content[0].text
        
    except Exception as e:
        print(f"❌ Error with Claude API: {e}")
        return None

def test_claude_connection():
    """Simple test to verify Claude API is working"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ No Claude API key found")
        return False
    
    try:
        client = Anthropic(api_key=api_key)
        
        # Simple test message
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            messages=[{"role": "user", "content": "Hello! Just testing the connection. Please respond briefly."}]
        )
        
        print("✅ Claude API connection successful!")
        print(f"📝 Claude says: {message.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        return False

def main():
    """Main function for gentle Claude testing"""
    
    print("🤖 Claude Gentle Summary & Connection Test")
    print("=" * 50)
    
    # First, test the connection
    print("🔧 Testing Claude API connection...")
    if not test_claude_connection():
        return
    
    print("\n📚 Fetching a small sample of conversations...")
    
    # Check Limitless API key
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    try:
        # Get just a few recent conversations
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            limit=5,  # Small batch
            direction="desc",
            includeMarkdown=True
        )
        
        if not lifelogs:
            print("📭 No conversations found!")
            return
        
        print(f"✅ Found {len(lifelogs)} recent conversations")
        
        # Add a small delay to be gentle with rate limits
        print("⏳ Waiting a moment to respect rate limits...")
        time.sleep(2)
        
        # Generate summary
        summarize_small_batch(lifelogs)
        
        print("\n💡 **Tips for scaling up:**")
        print("- This gentle version processes 3-5 conversations")
        print("- Once rate limits stabilize, you can process more")
        print("- Consider Claude Pro for higher rate limits")
        print("- Use the full version (claude_summarize_day.py) later")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()


